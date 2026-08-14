from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable


class Configuration:
    """
    JSON 配置文件的只读包装器。

    所有路径均由本类统一解析。相对路径相对于配置文件所在目录，而不是
    相对于运行命令时的当前目录，因此整个 SOE1 文件夹搬到服务器后不会
    因为从不同目录启动而改变路径含义。
    """

    def __init__(self, payload: Dict[str, Any], source_path: Path):
        self._payload = payload
        self.source_path = source_path.resolve()
        self.base_directory = self.source_path.parent

    @classmethod
    def from_json(cls, path: str) -> "Configuration":
        source_path = Path(path).expanduser().resolve()
        if not source_path.exists():
            raise FileNotFoundError("找不到配置文件：" + str(source_path))

        with source_path.open("r", encoding="utf-8") as file:
            payload = json.load(file)

        if not isinstance(payload, dict):
            raise ValueError("配置文件顶层必须是 JSON object。")
        return cls(payload=payload, source_path=source_path)

    def section(self, name: str) -> Dict[str, Any]:
        value = self._payload.get(name)
        if not isinstance(value, dict):
            raise KeyError("配置中缺少 object 类型的 section：" + name)
        return value

    def optional_section(self, name: str) -> Dict[str, Any]:
        value = self._payload.get(name, {})
        if not isinstance(value, dict):
            raise TypeError("配置 section 必须是 object：" + name)
        return value

    def require_keys(
        self,
        section_name: str,
        keys: Iterable[str],
    ) -> None:
        section = self.section(section_name)
        missing = [key for key in keys if key not in section]
        if missing:
            raise KeyError(
                section_name + " 缺少配置项：" + ", ".join(missing)
            )

    def resolve_path(self, value: Any, allow_none: bool = False) -> Path:
        """
        将配置中的路径转换为绝对 Path。

        Windows 盘符路径和 Linux 绝对路径都会保持绝对语义；相对路径统一
        相对于当前 JSON 文件所在目录。None 只在 allow_none=True 时允许。
        """

        if value is None:
            if allow_none:
                return None
            raise ValueError("必需路径不能为 null。")

        path = Path(str(value)).expanduser()
        if path.is_absolute():
            return path.resolve()
        return (self.base_directory / path).resolve()

    def as_dict(self) -> Dict[str, Any]:
        """返回浅复制，供运行摘要保存，避免外部修改内部状态。"""

        return dict(self._payload)

