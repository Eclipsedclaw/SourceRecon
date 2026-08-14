"""灵敏度定义、估计与严格分型。"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Optional

import numpy as np


class SensitivityKind(str, Enum):
    """三个不得混用的灵敏度物理定义。"""

    CONDITIONAL_ACCEPTANCE_PROBABILITY = "conditional_acceptance_probability"
    EFFECTIVE_AREA_CM2 = "effective_area_cm2"
    FINITE_DISTANCE_EMITTED_PROBABILITY = "finite_distance_emitted_probability"


_EXPECTED_UNIT = {
    SensitivityKind.CONDITIONAL_ACCEPTANCE_PROBABILITY: "1",
    SensitivityKind.EFFECTIVE_AREA_CM2: "cm2",
    SensitivityKind.FINITE_DISTANCE_EMITTED_PROBABILITY: "1",
}


@dataclass(frozen=True)
class SensitivityMap:
    """天空像素 × 能量 bin 的灵敏度及蒙特卡洛统计误差。"""

    kind: SensitivityKind
    values: np.ndarray
    standard_error: np.ndarray
    unit: str
    definition: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        kind = self.kind if isinstance(self.kind, SensitivityKind) else SensitivityKind(self.kind)
        values = np.asarray(self.values, dtype=float).copy()
        errors = np.asarray(self.standard_error, dtype=float).copy()
        if values.ndim != 2 or values.shape != errors.shape:
            raise ValueError("灵敏度及误差必须是形状相同的二维天空×能量数组。")
        if values.size == 0:
            raise ValueError("灵敏度数组不能为空。")
        if not np.all(np.isfinite(values)) or np.any(values < 0.0):
            raise ValueError("灵敏度必须是非负有限数。")
        if not np.all(np.isfinite(errors)) or np.any(errors < 0.0):
            raise ValueError("灵敏度标准误必须是非负有限数。")
        if str(self.unit) != _EXPECTED_UNIT[kind]:
            raise ValueError(
                "灵敏度单位与物理定义不符："
                + kind.value
                + " 必须使用 "
                + _EXPECTED_UNIT[kind]
            )
        if not str(self.definition).strip():
            raise ValueError("灵敏度必须携带明确的接受域/归一化定义。")
        if kind != SensitivityKind.EFFECTIVE_AREA_CM2 and np.any(values > 1.0 + 1e-12):
            raise ValueError("概率型灵敏度不能大于 1。")
        values.setflags(write=False)
        errors.setflags(write=False)
        object.__setattr__(self, "kind", kind)
        object.__setattr__(self, "values", values)
        object.__setattr__(self, "standard_error", errors)
        object.__setattr__(self, "unit", str(self.unit))
        object.__setattr__(self, "definition", str(self.definition))
        object.__setattr__(self, "metadata", dict(self.metadata))

    @property
    def shape(self):
        return self.values.shape


@dataclass(frozen=True)
class SensitivityBundle:
    """同一接受域下的条件概率、有效面积和有限距离绝对概率。

    条件接受概率始终必需。远场或有限距离量仅在对应生成模式具备完整分母时
    保存；缺失用 None 明示，不能用零数组冒充。
    """

    conditional: SensitivityMap
    effective_area: Optional[SensitivityMap] = None
    finite_distance_emitted: Optional[SensitivityMap] = None

    def __post_init__(self) -> None:
        expected = SensitivityKind.CONDITIONAL_ACCEPTANCE_PROBABILITY
        if self.conditional.kind != expected:
            raise ValueError("SensitivityBundle.conditional 的类型不正确。")
        for item, kind in (
            (self.effective_area, SensitivityKind.EFFECTIVE_AREA_CM2),
            (
                self.finite_distance_emitted,
                SensitivityKind.FINITE_DISTANCE_EMITTED_PROBABILITY,
            ),
        ):
            if item is not None:
                if item.kind != kind:
                    raise ValueError("灵敏度对象放入了错误的物理槽位。")
                if item.shape != self.conditional.shape:
                    raise ValueError("同一响应库的灵敏度网格形状必须一致。")

    def by_kind(self, kind: SensitivityKind) -> Optional[SensitivityMap]:
        """按物理定义获取灵敏度，调用者不能使用含糊的变量名 s。"""

        selected = kind if isinstance(kind, SensitivityKind) else SensitivityKind(kind)
        mapping = {
            SensitivityKind.CONDITIONAL_ACCEPTANCE_PROBABILITY: self.conditional,
            SensitivityKind.EFFECTIVE_AREA_CM2: self.effective_area,
            SensitivityKind.FINITE_DISTANCE_EMITTED_PROBABILITY: self.finite_distance_emitted,
        }
        return mapping[selected]


class SensitivityEstimator:
    """无权蒙特卡洛节点的第一组可解析估计器。

    加权生成需要有效样本量和专门方差估计，尚未确认前不会在这里假装等价于
    简单二项分布。
    """

    @staticmethod
    def conditional_acceptance(
        accepted_count,
        generated_count,
        definition: str,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> SensitivityMap:
        accepted = np.asarray(accepted_count, dtype=float)
        generated = np.asarray(generated_count, dtype=float)
        if accepted.ndim != 2 or accepted.shape != generated.shape:
            raise ValueError("accepted_count/generated_count 必须是同形状二维数组。")
        if not np.all(np.isfinite(accepted)) or not np.all(np.isfinite(generated)):
            raise ValueError("蒙特卡洛计数必须有限。")
        if np.any(generated <= 0.0) or np.any(accepted < 0.0) or np.any(accepted > generated):
            raise ValueError("计数要求 0 <= accepted_count <= generated_count 且分母大于 0。")
        probability = accepted / generated
        standard_error = np.sqrt(probability * (1.0 - probability) / generated)
        details = dict(metadata or {})
        details["estimator"] = "unweighted_binomial"
        return SensitivityMap(
            kind=SensitivityKind.CONDITIONAL_ACCEPTANCE_PROBABILITY,
            values=probability,
            standard_error=standard_error,
            unit="1",
            definition=definition,
            metadata=details,
        )

    @staticmethod
    def effective_area(
        conditional: SensitivityMap,
        generation_area_cm2: float,
    ) -> SensitivityMap:
        """按 A_gen * N_accepted/N_generated 计算远场有效面积。"""

        if conditional.kind != SensitivityKind.CONDITIONAL_ACCEPTANCE_PROBABILITY:
            raise TypeError("有效面积必须从条件接受概率派生。")
        area = float(generation_area_cm2)
        if not np.isfinite(area) or area <= 0.0:
            raise ValueError("远场参考生成平面面积必须为正有限数。")
        return SensitivityMap(
            kind=SensitivityKind.EFFECTIVE_AREA_CM2,
            values=conditional.values * area,
            standard_error=conditional.standard_error * area,
            unit="cm2",
            definition=(
                "相机处入射通量归一化：A_eff=A_gen*N_accepted/N_generated；"
                "不乘受限立体角因子。"
            ),
            metadata={
                "generation_area_cm2": area,
                "derived_from": conditional.kind.value,
            },
        )

    @staticmethod
    def finite_distance_emitted_probability(
        conditional: SensitivityMap,
        restricted_solid_angle_sr: float,
        source_distance_mm: float,
    ) -> SensitivityMap:
        """按 条件接受概率 * Omega/(4*pi) 计算相对总发射量的概率。"""

        if conditional.kind != SensitivityKind.CONDITIONAL_ACCEPTANCE_PROBABILITY:
            raise TypeError("s_emitted 必须从条件接受概率派生。")
        solid_angle = float(restricted_solid_angle_sr)
        distance = float(source_distance_mm)
        if not np.isfinite(solid_angle) or solid_angle <= 0.0 or solid_angle > 4.0 * np.pi:
            raise ValueError("受限立体角必须位于 (0, 4*pi] sr。")
        if not np.isfinite(distance) or distance <= 0.0:
            raise ValueError("有限距离点源距离必须为正有限数。")
        factor = solid_angle / (4.0 * np.pi)
        return SensitivityMap(
            kind=SensitivityKind.FINITE_DISTANCE_EMITTED_PROBABILITY,
            values=conditional.values * factor,
            standard_error=conditional.standard_error * factor,
            unit="1",
            definition=(
                "有限距离点源相对 4pi 总发射量："
                "s_emitted=(N_accepted/N_generated_in_cone)*Omega_cone/(4*pi)。"
            ),
            metadata={
                "restricted_solid_angle_sr": solid_angle,
                "solid_angle_fraction_of_4pi": factor,
                "source_distance_mm": distance,
                "derived_from": conditional.kind.value,
            },
        )
