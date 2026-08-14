"""稀疏 list-mode MLEM 核心更新器。"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import time
from typing import Callable, Optional, Sequence, Tuple

import numpy as np

from eiid.convergence.telemetry import IterationMetrics, memory_snapshot
from eiid.response import SensitivityMap, SparseEventResponse


class StopReason(str, Enum):
    """当前阶段支持的确定性停止原因。"""

    MAX_ITERATIONS = "maximum_iterations"
    LIKELIHOOD_CONVERGED = "likelihood_relative_change_converged"
    IMAGE_CONVERGED = "image_relative_change_converged"


@dataclass(frozen=True)
class LmMlemConfig:
    """LM-MLEM 数值保护和早停参数，全部由外部配置传入。"""

    maximum_iterations: int
    minimum_iterations: int
    denominator_floor: float
    sensitivity_floor: float
    likelihood_relative_tolerance: Optional[float]
    image_relative_tolerance: Optional[float]
    convergence_patience: int

    def __post_init__(self) -> None:
        if self.maximum_iterations <= 0:
            raise ValueError("maximum_iterations 必须大于 0。")
        if self.minimum_iterations < 0 or self.minimum_iterations > self.maximum_iterations:
            raise ValueError("minimum_iterations 必须位于 [0, maximum_iterations]。")
        if self.denominator_floor <= 0.0 or self.sensitivity_floor < 0.0:
            raise ValueError("分母下限必须为正，灵敏度下限不能为负。")
        for name, value in (
            ("likelihood_relative_tolerance", self.likelihood_relative_tolerance),
            ("image_relative_tolerance", self.image_relative_tolerance),
        ):
            if value is not None and value <= 0.0:
                raise ValueError(name + " 必须为正数或 None。")
        if self.convergence_patience <= 0:
            raise ValueError("convergence_patience 必须大于 0。")


@dataclass(frozen=True)
class LmMlemResult:
    """重建最终联合图像和完整停止状态。"""

    image: np.ndarray
    telemetry: Tuple[IterationMetrics, ...]
    stop_reason: StopReason
    completed_iterations: int

    def __post_init__(self) -> None:
        image = np.asarray(self.image, dtype=float).copy()
        image.setflags(write=False)
        object.__setattr__(self, "image", image)
        object.__setattr__(self, "telemetry", tuple(self.telemetry))


class ListModeMlemSolver:
    """按设计基线公式执行联合天空—能量 list-mode MLEM。"""

    def __init__(self, config: LmMlemConfig):
        self.config = config

    @staticmethod
    def _validate_responses(
        responses: Sequence[SparseEventResponse], cell_count: int
    ) -> Tuple[SparseEventResponse, ...]:
        items = tuple(responses)
        if not items:
            raise ValueError("LM-MLEM 至少需要一个观测事件。")
        if any(item.cell_count != cell_count for item in items):
            raise ValueError("全部事件响应必须使用相同联合网格。")
        identifiers = [item.event_id for item in items]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("事件响应 event_id 必须唯一。")
        return items

    def _initial_image(
        self,
        sensitivity: np.ndarray,
        event_count: int,
        background_expected_count: float,
        initial_image,
    ) -> np.ndarray:
        active = sensitivity > self.config.sensitivity_floor
        if not np.any(active):
            raise ValueError("灵敏度没有任何有效联合单元。")
        if initial_image is None:
            image = np.zeros_like(sensitivity)
            image[active] = 1.0
        else:
            image = np.asarray(initial_image, dtype=float).reshape(-1).copy()
            if image.size != sensitivity.size:
                raise ValueError("初始图像大小与灵敏度不一致。")
            if not np.all(np.isfinite(image)) or np.any(image < 0.0):
                raise ValueError("初始图像必须是非负有限数。")
            image[~active] = 0.0
        expected_source_count = max(float(event_count) - background_expected_count, 1.0)
        predicted = float(np.dot(sensitivity, image))
        if predicted <= 0.0:
            raise ValueError("初始图像在有效灵敏度支撑上没有正强度。")
        image *= expected_source_count / predicted
        return image

    def _log_likelihood(
        self,
        image: np.ndarray,
        responses: Tuple[SparseEventResponse, ...],
        backgrounds: np.ndarray,
        background_expected_count: float,
        sensitivity: np.ndarray,
    ):
        total = -float(np.dot(sensitivity, image)) - background_expected_count
        invalid = 0
        valid = 0
        for index, response in enumerate(responses):
            denominator = response.dot(image) + backgrounds[index]
            if denominator <= self.config.denominator_floor:
                invalid += 1
                denominator = self.config.denominator_floor
            else:
                valid += 1
            total += float(np.log(denominator))
        return total, valid, invalid

    @staticmethod
    def _relative_change(current, previous, floor: float):
        delta = current - previous
        l1 = float(np.sum(np.abs(delta)) / max(np.sum(np.abs(previous)), floor))
        l2 = float(np.linalg.norm(delta) / max(np.linalg.norm(previous), floor))
        maximum = float(
            np.max(np.abs(delta) / np.maximum(np.abs(previous), floor))
        )
        return l1, l2, maximum

    @staticmethod
    def _physical_diagnostics(
        image, sky_count, energy_count, sky_directions, energy_centers_mev
    ):
        """返回方向质心/R68和能谱峰；缺少网格坐标时显式返回 None。"""

        result = {
            "sky_centroid_direction": None,
            "sky_r68_deg": None,
            "energy_peak_mev": None,
            "energy_weighted_mean_mev": None,
        }
        joint = np.asarray(image, dtype=float).reshape(sky_count, energy_count)
        if energy_centers_mev is not None:
            centers = np.asarray(energy_centers_mev, dtype=float).reshape(-1)
            if centers.size != energy_count:
                raise ValueError("energy_centers_mev 数量与能量网格不一致。")
            spectrum = np.sum(joint, axis=0)
            if float(np.sum(spectrum)) > 0.0:
                result["energy_peak_mev"] = float(centers[int(np.argmax(spectrum))])
                result["energy_weighted_mean_mev"] = float(
                    np.dot(spectrum, centers) / np.sum(spectrum)
                )
        if sky_directions is not None:
            directions = np.asarray(sky_directions, dtype=float)
            if directions.shape != (sky_count, 3):
                raise ValueError("sky_directions 形状与天空网格不一致。")
            weights = np.sum(joint, axis=1)
            total = float(np.sum(weights))
            vector = np.sum(directions * weights[:, np.newaxis], axis=0)
            norm = float(np.linalg.norm(vector))
            if total > 0.0 and norm > 1e-15:
                centroid = vector / norm
                angles = np.arccos(np.clip(directions @ centroid, -1.0, 1.0))
                order = np.argsort(angles)
                cumulative = np.cumsum(weights[order])
                index = min(int(np.searchsorted(cumulative, 0.68 * total)), sky_count - 1)
                result["sky_centroid_direction"] = tuple(float(value) for value in centroid)
                result["sky_r68_deg"] = float(np.rad2deg(angles[order[index]]))
        return result

    def run(
        self,
        responses: Sequence[SparseEventResponse],
        sensitivity_map: SensitivityMap,
        background_event_density=None,
        background_expected_count: float = 0.0,
        initial_image=None,
        sky_directions=None,
        energy_centers_mev=None,
        observer: Optional[Callable[[IterationMetrics, np.ndarray, bool], None]] = None,
    ) -> LmMlemResult:
        sensitivity = np.asarray(sensitivity_map.values, dtype=float).reshape(-1)
        items = self._validate_responses(responses, sensitivity.size)
        backgrounds = (
            np.zeros(len(items), dtype=float)
            if background_event_density is None
            else np.asarray(background_event_density, dtype=float).reshape(-1)
        )
        if backgrounds.size != len(items):
            raise ValueError("background_event_density 必须与事件数一致。")
        if not np.all(np.isfinite(backgrounds)) or np.any(backgrounds < 0.0):
            raise ValueError("背景事件密度必须为非负有限数。")
        background_total = float(background_expected_count)
        if not np.isfinite(background_total) or background_total < 0.0:
            raise ValueError("background_expected_count 必须为非负有限数。")

        image = self._initial_image(
            sensitivity, len(items), background_total, initial_image
        )
        sky_count, energy_count = sensitivity_map.shape
        start = time.perf_counter()
        previous_likelihood = None
        likelihood_streak = 0
        image_streak = 0
        history = []
        zero_response_count = sum(item.nonzero_count == 0 for item in items)
        event_groups = {}
        for item in items:
            group = str(item.diagnostics.get("event_group", "unclassified"))
            event_groups[group] = event_groups.get(group, 0) + 1

        initial_likelihood, valid, invalid = self._log_likelihood(
            image, items, backgrounds, background_total, sensitivity
        )
        rss, available = memory_snapshot()
        peak = int(np.argmax(image))
        physical = self._physical_diagnostics(
            image, sky_count, energy_count, sky_directions, energy_centers_mev
        )
        initial_metrics = IterationMetrics(
            iteration=0,
            log_likelihood=initial_likelihood,
            relative_log_likelihood_change=None,
            total_intensity=float(np.sum(image)),
            l1_relative_change=0.0,
            l2_relative_change=0.0,
            maximum_relative_change=0.0,
            sky_marginal_l1_change=0.0,
            energy_marginal_l1_change=0.0,
            peak_joint_cell_index=peak,
            peak_sky_pixel_index=peak // energy_count,
            peak_energy_bin_index=peak % energy_count,
            valid_event_count=valid,
            zero_response_event_count=zero_response_count,
            invalid_denominator_count=invalid,
            iteration_seconds=0.0,
            elapsed_seconds=0.0,
            events_per_second=0.0,
            process_rss_bytes=rss,
            system_available_memory_bytes=available,
            event_group_contributions=event_groups,
            **physical,
        )
        history.append(initial_metrics)
        if observer is not None:
            observer(initial_metrics, image.copy(), False)
        previous_likelihood = initial_likelihood

        stop_reason = StopReason.MAX_ITERATIONS
        completed_iterations = 0
        for iteration in range(1, self.config.maximum_iterations + 1):
            iteration_start = time.perf_counter()
            correction = np.zeros_like(image)
            for event_index, response in enumerate(items):
                denominator = response.dot(image) + backgrounds[event_index]
                if denominator <= self.config.denominator_floor:
                    continue
                np.add.at(
                    correction,
                    response.cell_indices,
                    response.values / denominator,
                )
            active = sensitivity > self.config.sensitivity_floor
            updated = np.zeros_like(image)
            updated[active] = (
                image[active] * correction[active] / sensitivity[active]
            )
            if not np.all(np.isfinite(updated)) or np.any(updated < 0.0):
                raise FloatingPointError("LM-MLEM 更新产生非有限或负强度。")
            if float(np.sum(updated)) <= 0.0:
                raise FloatingPointError("LM-MLEM 更新后全部联合强度为零。")

            likelihood, valid, invalid = self._log_likelihood(
                updated, items, backgrounds, background_total, sensitivity
            )
            relative_likelihood = abs(likelihood - previous_likelihood) / max(
                abs(previous_likelihood), self.config.denominator_floor
            )
            l1, l2, maximum = self._relative_change(
                updated, image, self.config.denominator_floor
            )
            old_joint = image.reshape(sky_count, energy_count)
            new_joint = updated.reshape(sky_count, energy_count)
            sky_change = self._relative_change(
                np.sum(new_joint, axis=1),
                np.sum(old_joint, axis=1),
                self.config.denominator_floor,
            )[0]
            energy_change = self._relative_change(
                np.sum(new_joint, axis=0),
                np.sum(old_joint, axis=0),
                self.config.denominator_floor,
            )[0]
            duration = time.perf_counter() - iteration_start
            elapsed = time.perf_counter() - start
            rss, available = memory_snapshot()
            peak = int(np.argmax(updated))
            physical = self._physical_diagnostics(
                updated, sky_count, energy_count, sky_directions, energy_centers_mev
            )

            if iteration >= self.config.minimum_iterations:
                if (
                    self.config.likelihood_relative_tolerance is not None
                    and relative_likelihood
                    < self.config.likelihood_relative_tolerance
                ):
                    likelihood_streak += 1
                else:
                    likelihood_streak = 0
                if (
                    self.config.image_relative_tolerance is not None
                    and l1 < self.config.image_relative_tolerance
                ):
                    image_streak += 1
                else:
                    image_streak = 0
            final = iteration == self.config.maximum_iterations
            if likelihood_streak >= self.config.convergence_patience:
                stop_reason = StopReason.LIKELIHOOD_CONVERGED
                final = True
            elif image_streak >= self.config.convergence_patience:
                stop_reason = StopReason.IMAGE_CONVERGED
                final = True

            metrics = IterationMetrics(
                iteration=iteration,
                log_likelihood=likelihood,
                relative_log_likelihood_change=relative_likelihood,
                total_intensity=float(np.sum(updated)),
                l1_relative_change=l1,
                l2_relative_change=l2,
                maximum_relative_change=maximum,
                sky_marginal_l1_change=sky_change,
                energy_marginal_l1_change=energy_change,
                peak_joint_cell_index=peak,
                peak_sky_pixel_index=peak // energy_count,
                peak_energy_bin_index=peak % energy_count,
                valid_event_count=valid,
                zero_response_event_count=zero_response_count,
                invalid_denominator_count=invalid,
                iteration_seconds=duration,
                elapsed_seconds=elapsed,
                events_per_second=(len(items) / duration if duration > 0.0 else 0.0),
                process_rss_bytes=rss,
                system_available_memory_bytes=available,
                event_group_contributions=event_groups,
                **physical,
            )
            history.append(metrics)
            image = updated
            previous_likelihood = likelihood
            completed_iterations = iteration
            if observer is not None:
                observer(metrics, image.copy(), final)
            if final:
                break

        return LmMlemResult(
            image=image,
            telemetry=tuple(history),
            stop_reason=stop_reason,
            completed_iterations=completed_iterations,
        )
