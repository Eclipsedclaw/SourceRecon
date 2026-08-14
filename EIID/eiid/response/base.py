"""与响应存储格式无关的事件响应抽象接口。"""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np

from eiid.domain import EnergyGrid, MeasuredEvent

from .sparse import SparseEventResponse


class EventResponseModel(ABC):
    """把一个观测事件映射到稀疏的天空—能量响应。

    sky_directions 的第一个维度对应天空像素，向量含义是“从相机指向来源”。
    应用层可由 HEALPix 提供这些像素中心；响应模型本身不依赖 healpy 或文件格式。
    """

    model_id = "abstract"
    response_semantics = "unspecified"

    @abstractmethod
    def evaluate(
        self,
        event: MeasuredEvent,
        sky_directions: np.ndarray,
        energy_grid: EnergyGrid,
    ) -> SparseEventResponse:
        """计算单事件的稀疏响应；不支持的事件返回带诊断信息的空响应。"""

