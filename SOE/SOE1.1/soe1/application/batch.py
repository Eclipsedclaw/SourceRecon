from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
import json
import traceback
from pathlib import Path
from typing import Dict, List

from ..analysis import (
    BatchQualityReporter,
    DatasetQualityReporter,
    SimulationMetadata,
    SimulationMetadataParser,
)
from ..configuration import Configuration
from .pipeline import SoeApplication


def _run_dataset_task(task):
    """
    进程池使用的顶层 worker。

    每个 worker 只写自己的 dataset 文件夹，不共享重建状态，因此不同 ROOT
    之间没有锁，也不会改变单组 SOE 的随机链和物理逻辑。
    """

    metadata = SimulationMetadata(**task["metadata"])
    dataset_directory = Path(task["dataset_directory"])
    quality_path = dataset_directory / "quality_metrics.json"
    try:
        if task["mode"] == "reconstruct":
            configuration = Configuration(
                payload=task["configuration_payload"],
                source_path=Path(task["configuration_source_path"]),
            )
            SoeApplication(configuration).run(
                dataset_metadata=metadata,
                analysis_directory=dataset_directory,
            )
        elif task["mode"] == "reanalyze":
            DatasetQualityReporter(
                numerical_directory=dataset_directory / "numerical",
                report_directory=dataset_directory,
                metadata=metadata,
                analysis_config=task["analysis_config"],
            ).write_all()
        else:
            raise ValueError("未知批处理任务模式：" + str(task["mode"]))

        with quality_path.open("r", encoding="utf-8") as file:
            metrics = json.load(file)
        return {
            "ok": True,
            "mode": task["mode"],
            "dataset_slug": metadata.dataset_slug,
            "metrics": metrics,
        }
    except Exception as error:
        return {
            "ok": False,
            "mode": task["mode"],
            "dataset_slug": metadata.dataset_slug,
            "source_path": metadata.source_path,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "traceback": traceback.format_exc(),
        }


class SimulationBatchApplication:
    """
    自动遍历一组命名规范的 Geant4 ROOT，并为每组建立独立输出目录。

    单组失败默认不会中断整个长任务；错误、堆栈和已完成组都会写入 manifest，
    便于服务器长时间运行后定位问题和断点续跑。
    """

    POSITION_ORDER = {
        "center": 0,
        "xm": 1,
        "xp": 2,
        "ym": 3,
        "yp": 4,
    }

    def __init__(self, configuration: Configuration):
        self.configuration = configuration

    def run(self) -> Dict[str, str]:
        input_config = self.configuration.section("input")
        if str(input_config.get("type")) != "geant4_batch":
            raise ValueError(
                "SimulationBatchApplication 要求 input.type=geant4_batch。"
            )

        root_directory = self.configuration.resolve_path(
            input_config["root_directory"]
        )
        if not root_directory.is_dir():
            raise NotADirectoryError(
                "批量 ROOT 目录不存在：" + str(root_directory)
            )
        pattern = str(
            input_config.get(
                "file_pattern",
                "b1output_gamma_*MeV_z*m_*.root",
            )
        )
        parser = SimulationMetadataParser(
            source_offset_angle_deg=float(
                input_config.get("source_offset_angle_deg", 15.0)
            ),
            file_name_pattern=input_config.get("file_name_pattern"),
            center_direction=input_config.get(
                "center_direction_detector",
                [0.0, 0.0, -1.0],
            ),
            horizontal_axis=input_config.get(
                "horizontal_axis_detector",
                [-1.0, 0.0, 0.0],
            ),
            vertical_axis=input_config.get(
                "vertical_axis_detector",
                [0.0, -1.0, 0.0],
            ),
            generated_event_count=input_config.get(
                "generated_event_count_per_file"
            ),
        )
        metadata_items = []
        unrecognized = []
        for path in root_directory.glob(pattern):
            try:
                metadata_items.append(parser.parse(path))
            except ValueError as error:
                unrecognized.append(
                    {"path": str(path), "reason": str(error)}
                )
        metadata_items.sort(
            key=lambda item: (
                item.energy_mev,
                item.distance_m,
                self.POSITION_ORDER.get(item.position_label, 99),
            )
        )

        batch_config = self.configuration.optional_section("batch")
        maximum_files = batch_config.get("maximum_files")
        if maximum_files is not None:
            metadata_items = metadata_items[: int(maximum_files)]
        if not metadata_items:
            raise RuntimeError(
                "目录中没有匹配且可解析的 ROOT 文件："
                + str(root_directory / pattern)
            )

        output_root = self.configuration.resolve_path(
            self.configuration.section("output")["directory"]
        )
        dataset_root = output_root / "datasets"
        output_root.mkdir(parents=True, exist_ok=True)
        dataset_root.mkdir(parents=True, exist_ok=True)

        continue_on_error = bool(
            batch_config.get("continue_on_error", True)
        )
        skip_completed = bool(
            batch_config.get("skip_completed_datasets", True)
        )
        parallel_workers = int(
            batch_config.get("parallel_workers", 1)
        )
        if parallel_workers <= 0:
            raise ValueError("batch.parallel_workers 必须大于 0。")
        metrics: List[Dict[str, object]] = []
        failures: List[Dict[str, object]] = list(unrecognized)
        completed = []
        reanalyzed = []
        skipped = []
        pending_tasks = []

        total = len(metadata_items)
        print(
            "SOE1 batch discovered "
            + str(total)
            + " datasets in "
            + str(root_directory),
            flush=True,
        )
        for index, metadata in enumerate(metadata_items, start=1):
            dataset_directory = (
                dataset_root / metadata.dataset_slug
            )
            quality_path = dataset_directory / "quality_metrics.json"
            if skip_completed and quality_path.exists():
                if self._analysis_is_current(
                    dataset_directory,
                    metadata,
                ):
                    with quality_path.open(
                        "r", encoding="utf-8"
                    ) as file:
                        metrics.append(json.load(file))
                    skipped.append(metadata.dataset_slug)
                    print(
                        "["
                        + str(index)
                        + "/"
                        + str(total)
                        + "] skip completed "
                        + metadata.dataset_slug,
                        flush=True,
                    )
                    continue
                if self._has_complete_numerical_output(
                    dataset_directory
                ):
                    print(
                        "["
                        + str(index)
                        + "/"
                        + str(total)
                        + "] queue analysis refresh "
                        + metadata.dataset_slug,
                        flush=True,
                    )
                    pending_tasks.append(
                        self._build_task(
                            mode="reanalyze",
                            metadata=metadata,
                            dataset_directory=dataset_directory,
                        )
                    )
                    continue
                print(
                    "Existing report is incomplete; rebuild "
                    + metadata.dataset_slug,
                    flush=True,
                )

            print(
                "["
                + str(index)
                + "/"
                + str(total)
                + "] queue reconstruction "
                + metadata.dataset_slug,
                flush=True,
            )
            pending_tasks.append(
                self._build_task(
                    mode="reconstruct",
                    metadata=metadata,
                    dataset_directory=dataset_directory,
                )
            )

        effective_workers = min(
            parallel_workers,
            max(len(pending_tasks), 1),
        )
        print(
            "SOE1 batch will run "
            + str(len(pending_tasks))
            + " pending tasks with "
            + str(effective_workers)
            + " worker process(es).",
            flush=True,
        )

        if effective_workers == 1:
            task_results = (
                _run_dataset_task(task) for task in pending_tasks
            )
            for result in task_results:
                self._record_task_result(
                    result=result,
                    total=total,
                    metrics=metrics,
                    completed=completed,
                    reanalyzed=reanalyzed,
                    skipped=skipped,
                    failures=failures,
                )
        else:
            with ProcessPoolExecutor(
                max_workers=effective_workers
            ) as executor:
                futures = {
                    executor.submit(_run_dataset_task, task): task
                    for task in pending_tasks
                }
                for future in as_completed(futures):
                    task = futures[future]
                    try:
                        result = future.result()
                    except Exception as error:
                        result = {
                            "ok": False,
                            "mode": task["mode"],
                            "dataset_slug": task["metadata"][
                                "dataset_slug"
                            ],
                            "source_path": task["metadata"]["source_path"],
                            "error_type": type(error).__name__,
                            "error_message": str(error),
                            "traceback": traceback.format_exc(),
                        }
                    self._record_task_result(
                        result=result,
                        total=total,
                        metrics=metrics,
                        completed=completed,
                        reanalyzed=reanalyzed,
                        skipped=skipped,
                        failures=failures,
                    )

        manifest_path = self._write_manifest(
            output_root,
            root_directory,
            pattern,
            metadata_items,
            completed,
            reanalyzed,
            skipped,
            failures,
            parallel_workers,
        )
        if failures and not continue_on_error:
            raise RuntimeError(
                "批处理存在失败数据集；详见 " + str(manifest_path)
            )

        reporter = BatchQualityReporter(
            output_root=output_root,
            analysis_config=self.configuration.optional_section(
                "analysis"
            ),
        )
        output_paths = reporter.write_all(metrics, failures)
        output_paths["batch_manifest_json"] = str(manifest_path)
        output_paths["output_root"] = str(output_root)
        return output_paths

    def _build_task(
        self,
        mode,
        metadata,
        dataset_directory,
    ):
        task = {
            "mode": mode,
            "metadata": metadata.to_dict(),
            "dataset_directory": str(dataset_directory.resolve()),
            "analysis_config": self.configuration.optional_section(
                "analysis"
            ),
        }
        if mode == "reconstruct":
            child = self._child_configuration(
                metadata,
                dataset_directory / "numerical",
            )
            task.update(
                {
                    "configuration_payload": child.as_dict(),
                    "configuration_source_path": str(child.source_path),
                }
            )
        return task

    @staticmethod
    def _record_task_result(
        result,
        total,
        metrics,
        completed,
        reanalyzed,
        skipped,
        failures,
    ):
        task_failure_count = sum(
            "dataset_slug" in failure for failure in failures
        )
        finished_count = (
            len(completed)
            + len(reanalyzed)
            + len(skipped)
            + task_failure_count
            + 1
        )
        prefix = "[" + str(finished_count) + "/" + str(total) + "] "
        if result["ok"]:
            metrics.append(result["metrics"])
            if result["mode"] == "reanalyze":
                reanalyzed.append(result["dataset_slug"])
                action = "analysis refreshed "
            else:
                completed.append(result["dataset_slug"])
                action = "finished "
            print(
                prefix + action + result["dataset_slug"],
                flush=True,
            )
            return

        failures.append(
            {
                key: value
                for key, value in result.items()
                if key != "ok"
            }
        )
        print(
            prefix
            + "FAILED "
            + result["dataset_slug"]
            + ": "
            + result["error_message"],
            flush=True,
        )

    @staticmethod
    def _has_complete_numerical_output(dataset_directory) -> bool:
        numerical = dataset_directory / "numerical"
        required = [
            "sky_map.csv",
            "spectrum_prior.csv",
            "event_hypothesis_posterior.csv",
            "run_summary.json",
            "configuration_snapshot.json",
        ]
        return all((numerical / name).is_file() for name in required)

    @staticmethod
    def _analysis_is_current(dataset_directory, metadata) -> bool:
        required = [
            dataset_directory / "quality_metrics.json",
            dataset_directory
            / "figures"
            / "02a_front_hemisphere_raw_pixel_map.png",
            dataset_directory
            / "figures"
            / "02b_front_hemisphere_smoothed_map.png",
        ]
        if not all(path.is_file() for path in required):
            return False
        metadata_path = dataset_directory / "dataset_metadata.json"
        try:
            with required[0].open("r", encoding="utf-8") as file:
                json.load(file)
            with metadata_path.open("r", encoding="utf-8") as file:
                stored = json.load(file)
        except (OSError, ValueError, json.JSONDecodeError):
            return False
        expected = metadata.expected_direction
        stored_vector = [
            stored.get("expected_direction_x"),
            stored.get("expected_direction_y"),
            stored.get("expected_direction_z"),
        ]
        try:
            return all(
                abs(float(first) - float(second)) < 1e-10
                for first, second in zip(stored_vector, expected)
            )
        except (TypeError, ValueError):
            return False

    def _child_configuration(
        self,
        metadata,
        numerical_directory,
    ) -> Configuration:
        payload = self.configuration.as_dict()
        input_config = payload["input"]
        input_config["type"] = "geant4_root"
        input_config["root_path"] = metadata.source_path
        input_config["dataset_id"] = metadata.dataset_slug
        input_config["streaming"] = True
        payload["output"]["directory"] = str(
            Path(numerical_directory).resolve()
        )
        return self.configuration.derived(payload)

    @staticmethod
    def _write_manifest(
        output_root,
        root_directory,
        pattern,
        metadata_items,
        completed,
        reanalyzed,
        skipped,
        failures,
        parallel_workers,
    ) -> Path:
        path = output_root / "batch_manifest.json"
        payload = {
            "root_directory": str(root_directory),
            "file_pattern": pattern,
            "parallel_workers": int(parallel_workers),
            "discovered_dataset_count": len(metadata_items),
            "completed_this_run_count": len(completed),
            "reanalyzed_without_reconstruction_count": len(reanalyzed),
            "skipped_completed_count": len(skipped),
            "failed_count": len(failures),
            "completed_this_run": completed,
            "reanalyzed_without_reconstruction": reanalyzed,
            "skipped_completed": skipped,
            "failures": failures,
            "datasets": [
                metadata.to_dict() for metadata in metadata_items
            ],
        }
        with path.open("w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False, indent=2)
        return path
