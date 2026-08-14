"""数据集级多进程调度、内存保护、恢复和完成跳过。"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import threading
import time
from typing import Dict, List, Optional

from eiid.configuration import load_config

from .memory import MemoryGuardPolicy, SystemMemoryMonitor
from .threading import NUMERICAL_THREAD_VARIABLES


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_json(path: Path, payload) -> None:
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write("\n")
    os.replace(str(temporary), str(path))


def _safe_name(value: str) -> str:
    result = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value).strip())
    if not result or len(result) > 80:
        raise ValueError("dataset_id 为空或过长。")
    return result


def _generate_run_id(kind: str, snapshot) -> str:
    """在批处理底层生成与 RunContext 同结构的唯一编号，避免循环导入。"""

    canonical = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:8]
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return "{}_{}_{}_{}".format(timestamp, _safe_name(kind).lower(), digest, secrets.token_hex(3))


@dataclass
class DatasetJob:
    """单个数据集在批处理中的可持久化状态。"""

    dataset_id: str
    config_path: Path
    attempts: int = 0
    status: str = "pending"
    current_run_id: Optional[str] = None
    resume_from_run_id: Optional[str] = None
    exit_code: Optional[int] = None
    failure_reason: Optional[str] = None
    run_ids: List[str] = field(default_factory=list)

    def as_dict(self):
        return {
            "dataset_id": self.dataset_id,
            "config_path": str(self.config_path),
            "attempts": self.attempts,
            "status": self.status,
            "current_run_id": self.current_run_id,
            "resume_from_run_id": self.resume_from_run_id,
            "exit_code": self.exit_code,
            "failure_reason": self.failure_reason,
            "run_ids": list(self.run_ids),
        }


@dataclass
class _RunningJob:
    job: DatasetJob
    process: subprocess.Popen
    pump: threading.Thread
    log_stream: object
    started_monotonic: float


class BatchManifestLoader:
    """读取独立批清单，并验证数据集配置与项目隔离。"""

    @staticmethod
    def load(path_value):
        path = Path(path_value).expanduser().resolve()
        with path.open("r", encoding="utf-8") as stream:
            raw = json.load(stream)
        if raw.get("schema_version") != "eiid.batch.v1":
            raise ValueError("批清单 schema_version 必须是 eiid.batch.v1。")
        candidate = Path(str(raw["project_root"])).expanduser()
        project_root = candidate.resolve() if candidate.is_absolute() else (path.parent / candidate).resolve()

        def inside(value, label):
            item = Path(str(value)).expanduser()
            resolved = item.resolve() if item.is_absolute() else (project_root / item).resolve()
            try:
                resolved.relative_to(project_root)
            except ValueError as error:
                raise ValueError(label + " 必须位于 EIID project_root 内。") from error
            return resolved

        jobs = []
        identifiers = set()
        for item in raw["datasets"]:
            raw_id = str(item["dataset_id"])
            dataset_id = _safe_name(raw_id)
            if dataset_id in identifiers:
                raise ValueError("批清单 dataset_id 重复：" + dataset_id)
            identifiers.add(dataset_id)
            config_path = inside(item["config"], "dataset config")
            config = load_config(str(config_path))
            configured_id = str(config.raw_payload.get("input", {}).get("dataset_id", ""))
            if configured_id != raw_id:
                raise ValueError("批清单 dataset_id 与数据集配置不一致：" + dataset_id)
            if config.paths.project_root != project_root:
                raise ValueError("所有数据集配置必须使用同一个 EIID project_root。")
            jobs.append(DatasetJob(dataset_id, config_path))
        if not jobs:
            raise ValueError("批清单至少需要一个数据集。")
        return path, project_root, raw, jobs


class MemoryAwareBatchScheduler:
    """逐进程运行数据集，按实时可用内存决定并发和保护性终止。"""

    def __init__(self, manifest_path, python_executable=None):
        self.manifest_path, self.project_root, self.raw, self.jobs = BatchManifestLoader.load(manifest_path)
        self.python = str(python_executable or self.raw.get("python_executable") or sys.executable)
        self.maximum_workers = int(self.raw["maximum_workers"])
        guard = self.raw["memory_guard"]
        self.policy = MemoryGuardPolicy(
            enabled=bool(guard["enabled"]),
            minimum_available_gib=float(guard["minimum_available_gib"]),
            estimated_worker_peak_gib=float(guard["estimated_worker_peak_gib"]),
        )
        self.poll_interval = float(guard.get("poll_interval_seconds", 2.0))
        self.maximum_retries = int(guard.get("maximum_retries", 2))
        self.termination_grace = float(guard.get("termination_grace_seconds", 10.0))
        if self.maximum_workers <= 0 or self.poll_interval <= 0.0 or self.maximum_retries < 0 or self.termination_grace <= 0.0:
            raise ValueError("批处理并行、轮询、重试或终止等待参数无效。")
        self.skip_completed = bool(self.raw.get("skip_completed", True))
        self.monitor = SystemMemoryMonitor()
        snapshot = dict(self.raw)
        snapshot["manifest_path"] = str(self.manifest_path)
        self.batch_id = _generate_run_id("batch", snapshot)
        root = (self.project_root / str(self.raw.get("batch_output_root", "batch_runs"))).resolve()
        try:
            root.relative_to(self.project_root)
        except ValueError as error:
            raise ValueError("batch_output_root 必须位于 EIID 根目录内。") from error
        self.directory = root / self.batch_id
        self.directory.mkdir(parents=True, exist_ok=False)
        self.logs = self.directory / "dataset_logs"
        self.logs.mkdir()
        self.manifest_output = self.directory / "batch_manifest.json"
        self.memory_csv = self.directory / "memory_telemetry.csv"
        self.failed_json = self.directory / "failed_datasets.json"
        self.running: Dict[str, _RunningJob] = {}
        self.started_utc = _utc_now()

    def _write_manifest(self, status="running"):
        _atomic_json(self.manifest_output, {
            "batch_id": self.batch_id,
            "status": status,
            "started_utc": self.started_utc,
            "updated_utc": _utc_now(),
            "project_root": str(self.project_root),
            "source_manifest": str(self.manifest_path),
            "maximum_workers": self.maximum_workers,
            "memory_guard": dict(self.raw["memory_guard"]),
            "datasets": [job.as_dict() for job in self.jobs],
        })

    def _append_memory(self, snapshot, capacity):
        exists = self.memory_csv.exists()
        with self.memory_csv.open("a", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream)
            if not exists:
                writer.writerow(("timestamp_utc", "total_bytes", "available_bytes", "safe_capacity", "running_workers"))
            writer.writerow((snapshot.timestamp_utc, snapshot.total_bytes, snapshot.available_bytes, capacity, len(self.running)))

    def _completed_dataset_ids(self):
        completed = set()
        for marker in (self.project_root / "runs").glob("*/SUCCESS.json"):
            try:
                with marker.open("r", encoding="utf-8") as stream:
                    dataset_id = json.load(stream).get("summary", {}).get("dataset_id")
                if dataset_id:
                    completed.add(str(dataset_id))
            except (OSError, ValueError, json.JSONDecodeError):
                continue
        return completed

    def _latest_resumable(self, dataset_id: str) -> Optional[str]:
        candidates = []
        runs = self.project_root / "runs"
        if not runs.is_dir():
            return None
        for directory in runs.iterdir():
            if not directory.is_dir() or (directory / "SUCCESS.json").exists():
                continue
            if not any((directory / "checkpoints").glob("iteration_*.npz")):
                continue
            try:
                with (directory / "config_snapshot.json").open("r", encoding="utf-8") as stream:
                    payload = json.load(stream)
                if str(payload.get("input", {}).get("dataset_id")) == dataset_id:
                    candidates.append(directory.name)
            except (OSError, ValueError, json.JSONDecodeError):
                continue
        return sorted(candidates)[-1] if candidates else None

    @staticmethod
    def _pump_output(process, log_stream, prefix):
        assert process.stdout is not None
        for line in iter(process.stdout.readline, ""):
            sys.stdout.write("[{}] {}".format(prefix, line))
            sys.stdout.flush()
            log_stream.write(line)
            log_stream.flush()
        process.stdout.close()

    def _launch(self, job: DatasetJob):
        config = load_config(str(job.config_path))
        job.attempts += 1
        job.current_run_id = _generate_run_id("dataset_" + job.dataset_id.lower(), config.as_dict())
        job.run_ids.append(job.current_run_id)
        job.status = "running"
        job.failure_reason = None
        log_stream = (self.logs / (job.current_run_id + ".log")).open("w", encoding="utf-8", newline="\n")
        env = os.environ.copy()
        for name in NUMERICAL_THREAD_VARIABLES:
            env[name] = str(config.runtime.numerical_threads_per_worker)
        env["MPLBACKEND"] = "Agg"
        env["EIID_RUN_ID"] = job.current_run_id
        env["EIID_LOG_PATH"] = str(config.paths.log_root / (job.current_run_id + ".log"))
        command = [self.python, "-u", str(self.project_root / "main_experiment.py"), "--config", str(job.config_path)]
        resume = job.resume_from_run_id or self._latest_resumable(job.dataset_id)
        if resume:
            command.extend(("--resume-from-run-id", resume))
            job.resume_from_run_id = resume
        process = subprocess.Popen(
            command, cwd=str(self.project_root), env=env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace", bufsize=1,
        )
        pump = threading.Thread(target=self._pump_output, args=(process, log_stream, job.dataset_id), daemon=True)
        pump.start()
        self.running[job.dataset_id] = _RunningJob(job, process, pump, log_stream, time.monotonic())
        print("[EIID batch] launched dataset={} run_id={} attempt={}".format(job.dataset_id, job.current_run_id, job.attempts), flush=True)

    def _finish(self, running: _RunningJob, memory_terminated=False):
        code = running.process.poll()
        if code is None:
            return
        running.pump.join(timeout=5.0)
        running.log_stream.close()
        job = running.job
        job.exit_code = int(code)
        config = load_config(str(job.config_path))
        run_directory = config.paths.output_root / str(job.current_run_id)
        success = code == 0 and (run_directory / "SUCCESS.json").is_file()
        if success:
            job.status = "success"
            job.failure_reason = None
        else:
            job.failure_reason = "memory_guard_terminated" if memory_terminated else "worker_exit_{}".format(code)
            if job.attempts <= self.maximum_retries:
                job.status = "pending"
                if any((run_directory / "checkpoints").glob("iteration_*.npz")):
                    job.resume_from_run_id = job.current_run_id
            else:
                job.status = "failed"
        self.running.pop(job.dataset_id, None)
        print("[EIID batch] dataset={} status={} exit={}".format(job.dataset_id, job.status, code), flush=True)

    def _protect_memory(self, snapshot):
        if not self.policy.enabled or snapshot.available_bytes >= self.policy.minimum_available_bytes or not self.running:
            return
        victim = max(self.running.values(), key=lambda item: item.started_monotonic)
        print("[EIID batch] memory guard terminating dataset={}".format(victim.job.dataset_id), flush=True)
        victim.process.terminate()
        try:
            victim.process.wait(timeout=self.termination_grace)
        except subprocess.TimeoutExpired:
            victim.process.kill()
            victim.process.wait()
        self._finish(victim, memory_terminated=True)

    def run(self):
        if self.skip_completed:
            complete = self._completed_dataset_ids()
            for job in self.jobs:
                if job.dataset_id in complete:
                    job.status = "skipped_completed"
        self._write_manifest()
        interrupted = False
        try:
            while any(job.status in ("pending", "running") for job in self.jobs):
                for running in tuple(self.running.values()):
                    if running.process.poll() is not None:
                        self._finish(running)
                snapshot = self.monitor.snapshot()
                capacity = self.policy.safe_worker_capacity(snapshot.available_bytes, self.maximum_workers)
                self._append_memory(snapshot, capacity)
                self._protect_memory(snapshot)
                slots = max(0, capacity - len(self.running))
                pending = [job for job in self.jobs if job.status == "pending"]
                for job in pending[:slots]:
                    self._launch(job)
                self._write_manifest()
                if not self.running and pending and capacity == 0:
                    print("[EIID batch] waiting for free memory", flush=True)
                time.sleep(self.poll_interval)
        except KeyboardInterrupt:
            interrupted = True
            for running in tuple(self.running.values()):
                running.process.terminate()
            for running in tuple(self.running.values()):
                try:
                    running.process.wait(timeout=self.termination_grace)
                except subprocess.TimeoutExpired:
                    running.process.kill()
                self._finish(running)
            raise
        finally:
            failed = [job.as_dict() for job in self.jobs if job.status == "failed"]
            _atomic_json(self.failed_json, {"failed_datasets": failed})
            final_status = "interrupted" if interrupted else ("failure" if failed else "success")
            self._write_manifest(final_status)
            marker = self.directory / ("SUCCESS.json" if final_status == "success" else "FAILURE.json")
            _atomic_json(marker, {"batch_id": self.batch_id, "status": final_status, "finished_utc": _utc_now(), "failed_dataset_count": len(failed)})
        return {
            "batch_id": self.batch_id,
            "status": "failure" if any(job.status == "failed" for job in self.jobs) else "success",
            "batch_directory": str(self.directory),
            "datasets": [job.as_dict() for job in self.jobs],
        }
