"""版本化响应库的内存领域模型。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional

import numpy as np

from eiid.domain import EnergyGrid

from .sensitivity import SensitivityBundle


@dataclass(frozen=True)
class ResponseLibraryMetadata:
    """响应库来源和兼容性元数据。

    尚未确认的 Geant4/物理参数必须由构建配置明确写成 prototype/synthetic，
    不能由本类提供看似正式的默认值。
    """

    library_id: str
    schema_version: str
    library_status: str
    response_model_kind: str
    geometry_version: str
    physics_list: str
    digitizer_version: str
    trigger_definition: str
    producer_run_id: Optional[str] = None
    created_utc: Optional[str] = None
    attributes: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        required = (
            self.library_id,
            self.schema_version,
            self.library_status,
            self.response_model_kind,
            self.geometry_version,
            self.physics_list,
            self.digitizer_version,
            self.trigger_definition,
        )
        if any(not str(value).strip() for value in required):
            raise ValueError("响应库标识、状态和物理来源元数据均不能为空。")
        if self.producer_run_id is not None and not str(self.producer_run_id).strip():
            raise ValueError("producer_run_id 必须为非空字符串或 None。")
        if self.created_utc is not None and not str(self.created_utc).strip():
            raise ValueError("created_utc 必须为非空字符串或 None。")
        attributes = dict(self.attributes)
        if self.library_status == "validated_physical":
            evidence = (
                "validation_report_sha256",
                "validation_dataset_id",
                "validation_completed_utc",
            )
            if any(not str(attributes.get(name, "")).strip() for name in evidence):
                raise ValueError(
                    "validated_physical 响应库必须记录验证报告哈希、独立数据集和完成时间。"
                )
        object.__setattr__(self, "attributes", attributes)


@dataclass(frozen=True)
class ResponseLibrary:
    """不依赖磁盘格式的响应库。

    calibration_arrays 用于保存 ARM、拓扑概率等混合响应标定量；具体字段由
    manifest 声明，正式字段集合将在小规模 Geant4 campaign 后确认。
    """

    metadata: ResponseLibraryMetadata
    energy_grid: EnergyGrid
    sky_grid: Mapping[str, Any]
    sensitivities: SensitivityBundle
    calibration_arrays: Mapping[str, np.ndarray] = field(default_factory=dict)

    def __post_init__(self) -> None:
        sky = dict(self.sky_grid)
        for key in ("type", "pixel_count"):
            if key not in sky:
                raise ValueError("sky_grid 缺少 " + key + "。")
        pixel_count = int(sky["pixel_count"])
        if pixel_count <= 0:
            raise ValueError("sky_grid.pixel_count 必须大于 0。")
        expected_shape = (pixel_count, self.energy_grid.bin_count)
        if self.sensitivities.conditional.shape != expected_shape:
            raise ValueError(
                "灵敏度形状必须等于 (sky_pixel_count, energy_bin_count)。"
            )

        arrays = {}
        for name, value in self.calibration_arrays.items():
            label = str(name)
            if not label or not all(
                character.isalnum() or character in "_.-" for character in label
            ):
                raise ValueError("calibration_arrays 名称只能包含字母、数字、_、-、.。")
            array = np.asarray(value, dtype=float).copy()
            if array.size == 0 or not np.all(np.isfinite(array)):
                raise ValueError("标定数组必须非空且全部有限：" + label)
            array.setflags(write=False)
            arrays[label] = array
        object.__setattr__(self, "sky_grid", sky)
        object.__setattr__(self, "calibration_arrays", arrays)
