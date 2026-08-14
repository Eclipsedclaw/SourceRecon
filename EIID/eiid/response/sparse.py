"""单事件稀疏响应领域对象。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

import numpy as np


@dataclass(frozen=True)
class SparseEventResponse:
    """按 C 顺序展平的天空像素 × 能量 bin 稀疏响应。

    展平规则为 cell = sky_pixel * energy_bin_count + energy_bin。构造时会
    排序并合并重复索引，防止不同响应分量对同一单元重复计数。
    """

    event_id: str
    cell_count: int
    cell_indices: np.ndarray
    values: np.ndarray
    model_id: str
    diagnostics: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.event_id or not self.model_id:
            raise ValueError("event_id 和 model_id 不能为空。")
        count = int(self.cell_count)
        indices = np.asarray(self.cell_indices, dtype=np.int64).reshape(-1)
        values = np.asarray(self.values, dtype=float).reshape(-1)
        if count <= 0:
            raise ValueError("cell_count 必须大于 0。")
        if indices.size != values.size:
            raise ValueError("cell_indices 与 values 长度必须一致。")
        if np.any(indices < 0) or np.any(indices >= count):
            raise IndexError("稀疏响应索引超出联合网格范围。")
        if not np.all(np.isfinite(values)) or np.any(values < 0.0):
            raise ValueError("响应值必须是非负有限数。")

        if indices.size:
            order = np.argsort(indices, kind="mergesort")
            sorted_indices = indices[order]
            sorted_values = values[order]
            unique_indices, first = np.unique(sorted_indices, return_index=True)
            merged_values = np.add.reduceat(sorted_values, first)
            nonzero = merged_values > 0.0
            indices = unique_indices[nonzero]
            values = merged_values[nonzero]

        indices = np.asarray(indices, dtype=np.int64)
        values = np.asarray(values, dtype=float)
        indices.setflags(write=False)
        values.setflags(write=False)
        object.__setattr__(self, "cell_count", count)
        object.__setattr__(self, "cell_indices", indices)
        object.__setattr__(self, "values", values)
        object.__setattr__(self, "diagnostics", dict(self.diagnostics))

    @classmethod
    def empty(
        cls,
        event_id: str,
        cell_count: int,
        model_id: str,
        reason: str,
    ) -> "SparseEventResponse":
        """构造不丢事件身份和失败原因的空响应。"""

        return cls(
            event_id=event_id,
            cell_count=cell_count,
            cell_indices=np.empty(0, dtype=np.int64),
            values=np.empty(0, dtype=float),
            model_id=model_id,
            diagnostics={"empty_reason": str(reason)},
        )

    @property
    def nonzero_count(self) -> int:
        return int(self.values.size)

    def to_dense(self) -> np.ndarray:
        """仅供小规模验证使用；正式重建不应批量稠密化事件响应。"""

        dense = np.zeros(self.cell_count, dtype=float)
        dense[self.cell_indices] = self.values
        return dense

    def dot(self, joint_image: np.ndarray) -> float:
        """计算本事件的 R_i · f，保持稀疏访问。"""

        image = np.asarray(joint_image, dtype=float).reshape(-1)
        if image.size != self.cell_count:
            raise ValueError("联合图像大小与响应 cell_count 不一致。")
        return float(np.dot(self.values, image[self.cell_indices]))

