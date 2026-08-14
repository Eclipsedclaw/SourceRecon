"""统一 run_id、配置快照和成功/失败生命周期。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import secrets
import socket
import sys
import traceback
from typing import Any, Mapping, Optional


_SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,159}$")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_json(payload: Mapping[str, Any]) -> str:
    try:
        return json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except (TypeError, ValueError) as error:
        raise ValueError("配置快照必须可以序列化为 JSON。") from error


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    serialized = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(serialized)
        stream.write("\n")
    os.replace(str(temporary), str(path))


class RunIdFactory:
    """生成可读、可排序且带配置指纹的唯一运行编号。"""

    @staticmethod
    def configuration_hash(config_snapshot: Mapping[str, Any]) -> str:
        canonical = _canonical_json(config_snapshot).encode("utf-8")
        return hashlib.sha256(canonical).hexdigest()

    @classmethod
    def generate(
        cls,
        run_kind: str,
        config_snapshot: Mapping[str, Any],
        timestamp_utc: Optional[datetime] = None,
        entropy: Optional[str] = None,
    ) -> str:
        kind = str(run_kind).strip().lower().replace(" ", "_")
        if not _SAFE_IDENTIFIER.fullmatch(kind):
            raise ValueError("run_kind 只能包含字母、数字、点、短横线和下划线。")
        moment = timestamp_utc or datetime.now(timezone.utc)
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=timezone.utc)
        moment = moment.astimezone(timezone.utc)
        timestamp = moment.strftime("%Y%m%dT%H%M%S%fZ")
        config_hash = cls.configuration_hash(config_snapshot)
        suffix = str(entropy) if entropy is not None else secrets.token_hex(3)
        if not re.fullmatch(r"[A-Za-z0-9]+", suffix):
            raise ValueError("run_id 随机后缀只能包含字母和数字。")
        return "{}_{}_{}_{}".format(timestamp, kind, config_hash[:8], suffix)


@dataclass(frozen=True)
class RunPaths:
    """一次运行的全部标准输出位置。"""

    run_directory: Path
    numerical_directory: Path
    checkpoint_directory: Path
    figure_directory: Path
    manifest_path: Path
    configuration_snapshot_path: Path
    success_marker_path: Path
    failure_marker_path: Path
    log_path: Path


class RunContext:
    """管理一次运行从 running 到 success/failure 的原子状态转换。"""

    def __init__(
        self,
        run_id: str,
        run_kind: str,
        config_snapshot: Mapping[str, Any],
        project_root,
        output_root,
        log_root,
        log_path=None,
        code_revision: Optional[str] = None,
    ):
        if not _SAFE_IDENTIFIER.fullmatch(str(run_id)):
            raise ValueError("run_id 含非法字符或长度超限。")
        if not _SAFE_IDENTIFIER.fullmatch(str(run_kind)):
            raise ValueError("run_kind 含非法字符或长度超限。")
        self.run_id = str(run_id)
        self.run_kind = str(run_kind)
        self.config_snapshot = dict(config_snapshot)
        self.config_hash = RunIdFactory.configuration_hash(self.config_snapshot)
        self.project_root = Path(project_root).expanduser().resolve()
        self.output_root = Path(output_root).expanduser().resolve()
        self.log_root = Path(log_root).expanduser().resolve()
        for label, path in (
            ("output_root", self.output_root),
            ("log_root", self.log_root),
        ):
            try:
                path.relative_to(self.project_root)
            except ValueError as error:
                raise ValueError(label + " 必须位于 EIID project_root 内。") from error

        selected_log = (
            Path(log_path).expanduser().resolve()
            if log_path is not None
            else (self.log_root / (self.run_id + ".log")).resolve()
        )
        try:
            selected_log.relative_to(self.log_root)
        except ValueError as error:
            raise ValueError("运行日志必须位于配置的 log_root 内。") from error

        run_directory = (self.output_root / self.run_id).resolve()
        try:
            run_directory.relative_to(self.output_root)
        except ValueError as error:
            raise ValueError("run_id 导致运行目录逃出 output_root。") from error
        self.paths = RunPaths(
            run_directory=run_directory,
            numerical_directory=run_directory / "numerical",
            checkpoint_directory=run_directory / "checkpoints",
            figure_directory=run_directory / "figures",
            manifest_path=run_directory / "run_manifest.json",
            configuration_snapshot_path=run_directory / "config_snapshot.json",
            success_marker_path=run_directory / "SUCCESS.json",
            failure_marker_path=run_directory / "FAILURE.json",
            log_path=selected_log,
        )
        self.code_revision = (
            str(code_revision)
            if code_revision is not None
            else os.environ.get("EIID_CODE_REVISION", "unknown_not_recorded")
        )
        self.started_utc = _utc_now()
        self._status = "created"
        self._manifest = {}

    @classmethod
    def start(
        cls,
        config,
        run_kind: str,
        run_id: Optional[str] = None,
        log_path=None,
    ) -> "RunContext":
        """从 EiidConfig 创建运行目录；同名 run 永不静默覆盖。"""

        snapshot = config.as_dict()
        selected_id = run_id or RunIdFactory.generate(run_kind, snapshot)
        context = cls(
            run_id=selected_id,
            run_kind=run_kind,
            config_snapshot=snapshot,
            project_root=config.paths.project_root,
            output_root=config.paths.output_root,
            log_root=config.paths.log_root,
            log_path=log_path,
        )
        context._open()
        return context

    def _open(self) -> None:
        if self.paths.run_directory.exists():
            raise FileExistsError("run_id 已存在，禁止覆盖：" + self.run_id)
        self.paths.numerical_directory.mkdir(parents=True, exist_ok=False)
        self.paths.checkpoint_directory.mkdir()
        self.paths.figure_directory.mkdir()
        self.paths.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.paths.log_path.touch(exist_ok=True)
        _atomic_json(self.paths.configuration_snapshot_path, self.config_snapshot)
        self._manifest = {
            "run_id": self.run_id,
            "run_kind": self.run_kind,
            "status": "running",
            "started_utc": self.started_utc,
            "finished_utc": None,
            "project_root": str(self.project_root),
            "run_directory": str(self.paths.run_directory),
            "log_path": str(self.paths.log_path),
            "configuration_sha256": self.config_hash,
            "code_revision": self.code_revision,
            "host": socket.gethostname(),
            "pid": os.getpid(),
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "executable": sys.executable,
            "stop_reason": None,
        }
        _atomic_json(self.paths.manifest_path, self._manifest)
        self._status = "running"

    @property
    def status(self) -> str:
        return self._status

    def add_provenance(self, values: Mapping[str, Any]) -> None:
        """在运行期间追加可追溯来源，例如恢复所用的父 run 和 checkpoint。"""

        if self._status != "running":
            raise RuntimeError("只有 running 状态可以更新 provenance。")
        provenance = dict(self._manifest.get("provenance", {}))
        provenance.update(dict(values))
        self._manifest["provenance"] = provenance
        _atomic_json(self.paths.manifest_path, self._manifest)

    def mark_success(
        self,
        summary: Optional[Mapping[str, Any]] = None,
        stop_reason: str = "completed",
    ) -> None:
        if self._status != "running":
            raise RuntimeError("只有 running 状态可以标记 success。")
        finished = _utc_now()
        marker = {
            "run_id": self.run_id,
            "status": "success",
            "started_utc": self.started_utc,
            "finished_utc": finished,
            "stop_reason": str(stop_reason),
            "summary": dict(summary or {}),
        }
        self._manifest.update(
            status="success",
            finished_utc=finished,
            stop_reason=str(stop_reason),
        )
        _atomic_json(self.paths.manifest_path, self._manifest)
        # SUCCESS 最后原子落位；调度器只把存在此标记的目录视为完整运行。
        _atomic_json(self.paths.success_marker_path, marker)
        self._status = "success"

    def mark_failure(
        self,
        error: BaseException,
        stop_reason: str = "exception",
    ) -> None:
        if self._status != "running":
            raise RuntimeError("只有 running 状态可以标记 failure。")
        finished = _utc_now()
        marker = {
            "run_id": self.run_id,
            "status": "failure",
            "started_utc": self.started_utc,
            "finished_utc": finished,
            "stop_reason": str(stop_reason),
            "error_type": type(error).__name__,
            "error_message": str(error),
            "traceback": "".join(
                traceback.format_exception(type(error), error, error.__traceback__)
            ),
        }
        self._manifest.update(
            status="failure",
            finished_utc=finished,
            stop_reason=str(stop_reason),
        )
        _atomic_json(self.paths.manifest_path, self._manifest)
        _atomic_json(self.paths.failure_marker_path, marker)
        self._status = "failure"

    def __enter__(self) -> "RunContext":
        if self._status != "running":
            raise RuntimeError("RunContext 尚未启动或已经结束。")
        return self

    def __exit__(self, error_type, error, error_traceback):
        if error is None:
            if self._status == "running":
                self.mark_success(stop_reason="completed")
            return False
        if self._status == "running":
            reason = "user_interrupt" if isinstance(error, KeyboardInterrupt) else "exception"
            self.mark_failure(error, stop_reason=reason)
        return False
