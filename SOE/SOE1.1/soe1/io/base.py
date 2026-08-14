from __future__ import annotations

from abc import ABC, abstractmethod

from ..domain import InputDataset


class EventSource(ABC):
    """
    所有数据源的抽象基类。

    重建流水线只依赖这个接口，因此更换 ROOT branch、实验文件格式或
    数据库时，不需要修改康普顿物理和 SOE 采样代码。
    """

    @abstractmethod
    def read(self) -> InputDataset:
        """读取数据、完成 hit 聚合并按用途分类。"""

        raise NotImplementedError

