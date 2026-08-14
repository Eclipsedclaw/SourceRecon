"""EIID 配置的设计基线和数值合法性校验。"""

from __future__ import annotations

from typing import Any, Dict, Iterable, Mapping, Sequence, Tuple

import numpy as np


FIRST_VERSION_MINIMUM_MEV = 0.1
FIRST_VERSION_MAXIMUM_MEV = 3.0
REQUIRED_TRIGGER_CHANNELS = ("ch1", "ch2")
KNOWN_CHANNELS = ("ch0", "ch1", "ch2")


def require_mapping(value: Any, label: str) -> Mapping[str, Any]:
    """要求配置值是 object/mapping。"""

    if not isinstance(value, Mapping):
        raise ValueError(label + " 必须是 object。")
    return value


def require_keys(mapping: Mapping[str, Any], keys: Iterable[str], label: str) -> None:
    """检查必需配置项，并一次报告全部缺失键。"""

    missing = [key for key in keys if key not in mapping]
    if missing:
        raise ValueError(label + " 缺少配置项：" + ", ".join(missing))


def vector3(value: Sequence[float], label: str) -> Tuple[float, float, float]:
    """把三维有限非零向量归一化为 tuple。"""

    array = np.asarray(value, dtype=float)
    if array.shape != (3,) or not np.all(np.isfinite(array)):
        raise ValueError(label + " 必须是三个有限数字。")
    norm = float(np.linalg.norm(array))
    if norm <= 0.0:
        raise ValueError(label + " 不能是零向量。")
    normalized = array / norm
    return tuple(float(item) for item in normalized)


def validate_coordinate_pair(stack: Sequence[float], boresight: Sequence[float]) -> None:
    """确认传播/堆叠方向与来源方向严格相反。"""

    first = np.asarray(stack, dtype=float)
    second = np.asarray(boresight, dtype=float)
    if not np.allclose(first, -second, atol=1e-12, rtol=0.0):
        raise ValueError(
            "coordinates 中探测器堆叠方向必须与相机正前方来源方向相反。"
        )


def validate_first_version_energy_range(minimum: float, maximum: float) -> None:
    """第一版只允许设计基线确定的 0.1–3.0 MeV。"""

    if not np.isclose(minimum, FIRST_VERSION_MINIMUM_MEV) or not np.isclose(
        maximum, FIRST_VERSION_MAXIMUM_MEV
    ):
        raise ValueError("EIID 第一版能量范围必须是 0.1–3.0 MeV。")


def validate_mapping(
    chamber_to_channel: Mapping[int, str], channel_to_layer: Mapping[str, int]
) -> None:
    """确认当前三层硬件映射与已确定设计一致。"""

    expected_chambers = {0: "ch2", 1: "ch1", 2: "ch0"}
    if dict(chamber_to_channel) != expected_chambers:
        raise ValueError(
            "第一版 chamber 映射必须为 0->ch2、1->ch1、2->ch0；"
            "映射仍需显式写入配置。"
        )
    expected_layers = {"ch2": 0, "ch1": 1, "ch0": 2}
    if dict(channel_to_layer) != expected_layers:
        raise ValueError(
            "第一版 layer 映射必须为 ch2->0、ch1->1、ch0->2。"
        )


def validate_trigger(required_channels: Sequence[str], thresholds: Mapping[str, float]) -> None:
    """确认触发没有错误加入 ch0，也没有遗漏逐通道阈值。"""

    if tuple(required_channels) != REQUIRED_TRIGGER_CHANNELS:
        raise ValueError("第一版触发 required_channels 必须严格为 [ch1, ch2]。")
    missing = [channel for channel in KNOWN_CHANNELS if channel not in thresholds]
    if missing:
        raise ValueError("触发阈值缺少通道：" + ", ".join(missing))
    for channel, value in thresholds.items():
        if channel not in KNOWN_CHANNELS:
            raise ValueError("未知阈值通道：" + str(channel))
        if not np.isfinite(float(value)) or float(value) < 0.0:
            raise ValueError(channel + " 阈值必须是非负有限值。")

