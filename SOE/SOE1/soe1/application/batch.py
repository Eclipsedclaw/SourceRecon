from __future__ import annotations

import json
import traceback
from pathlib import Path
from typing import Dict, List

from ..analysis import BatchQualityReporter, SimulationMetadataParser
from ..configuration import Configuration
from .pipeline import SoeApplication


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
                [1.0, 0.0, 0.0],
            ),
            vertical_axis=input_config.get(
                "vertical_axis_detector",
                [0.0, 1.0, 0.0],
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
        metrics: List[Dict[str, object]] = []
        failures: List[Dict[str, object]] = list(unrecognized)
        completed = []
        skipped = []

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
                try:
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
                except (OSError, ValueError, json.JSONDecodeError):
                    print(
                        "Existing quality report is incomplete; rebuild "
                        + metadata.dataset_slug,
                        flush=True,
                    )

            print(
                "["
                + str(index)
                + "/"
                + str(total)
                + "] reconstruct "
                + metadata.dataset_slug,
                flush=True,
            )
            try:
                child = self._child_configuration(
                    metadata,
                    dataset_directory / "numerical",
                )
                SoeApplication(child).run(
                    dataset_metadata=metadata,
                    analysis_directory=dataset_directory,
                )
                with quality_path.open("r", encoding="utf-8") as file:
                    metrics.append(json.load(file))
                completed.append(metadata.dataset_slug)
                print(
                    "["
                    + str(index)
                    + "/"
                    + str(total)
                    + "] finished "
                    + metadata.dataset_slug,
                    flush=True,
                )
            except Exception as error:
                failure = {
                    "dataset_slug": metadata.dataset_slug,
                    "source_path": metadata.source_path,
                    "error_type": type(error).__name__,
                    "error_message": str(error),
                    "traceback": traceback.format_exc(),
                }
                failures.append(failure)
                print(
                    "FAILED "
                    + metadata.dataset_slug
                    + ": "
                    + str(error),
                    flush=True,
                )
                if not continue_on_error:
                    self._write_manifest(
                        output_root,
                        root_directory,
                        pattern,
                        metadata_items,
                        completed,
                        skipped,
                        failures,
                    )
                    raise

        manifest_path = self._write_manifest(
            output_root,
            root_directory,
            pattern,
            metadata_items,
            completed,
            skipped,
            failures,
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
        skipped,
        failures,
    ) -> Path:
        path = output_root / "batch_manifest.json"
        payload = {
            "root_directory": str(root_directory),
            "file_pattern": pattern,
            "discovered_dataset_count": len(metadata_items),
            "completed_this_run_count": len(completed),
            "skipped_completed_count": len(skipped),
            "failed_count": len(failures),
            "completed_this_run": completed,
            "skipped_completed": skipped,
            "failures": failures,
            "datasets": [
                metadata.to_dict() for metadata in metadata_items
            ],
        }
        with path.open("w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False, indent=2)
        return path
