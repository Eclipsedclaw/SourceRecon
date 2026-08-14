"""相机正前方和传播方向的统一定义。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


def _unit(value, label):
    vector = np.asarray(value, dtype=float).copy()
    if vector.shape != (3,) or not np.all(np.isfinite(vector)):
        raise ValueError(label + " 必须是三个有限数字。")
    norm = float(np.linalg.norm(vector))
    if norm <= 0.0:
        raise ValueError(label + " 不能是零向量。")
    vector /= norm
    vector.setflags(write=False)
    return vector


@dataclass(frozen=True)
class CoordinateConvention:
    """Geant4 探测器坐标中的两个相反物理方向。"""

    detector_stack_direction: np.ndarray
    camera_boresight_source_direction: np.ndarray

    def __post_init__(self) -> None:
        stack = _unit(self.detector_stack_direction, "detector_stack_direction")
        boresight = _unit(
            self.camera_boresight_source_direction,
            "camera_boresight_source_direction",
        )
        if not np.allclose(stack, -boresight, atol=1e-12, rtol=0.0):
            raise ValueError("堆叠方向与相机正前方来源方向必须相反。")
        object.__setattr__(self, "detector_stack_direction", stack)
        object.__setattr__(self, "camera_boresight_source_direction", boresight)

    def propagation_to_source(self, propagation_direction) -> np.ndarray:
        """传播方向转换为天空来源方向。"""

        return -_unit(propagation_direction, "propagation_direction")

    def source_to_propagation(self, source_direction) -> np.ndarray:
        """天空来源方向转换为 gamma 传播方向。"""

        return -_unit(source_direction, "source_direction")

    def is_camera_front(self, source_direction) -> bool:
        """判断来源是否位于以 boresight 为中心的开前半球。"""

        direction = _unit(source_direction, "source_direction")
        return bool(
            np.dot(direction, self.camera_boresight_source_direction) > 0.0
        )

