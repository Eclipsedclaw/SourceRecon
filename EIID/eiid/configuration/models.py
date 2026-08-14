"""不依赖具体文件格式的只读配置对象。"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple


@dataclass(frozen=True)
class CoordinateConfig:
    """探测器坐标约定；两个向量的物理含义不能混用。"""

    detector_stack_direction: Tuple[float, float, float]
    camera_boresight_source_direction: Tuple[float, float, float]


@dataclass(frozen=True)
class ProjectPathsConfig:
    """项目隔离目录；所有算法输入和输出都必须位于 project_root 下。"""

    project_root: Path
    input_root: Path
    response_root: Path
    output_root: Path
    log_root: Path


@dataclass(frozen=True)
class EnergyGridConfig:
    """第一版联合重建能量网格配置。"""

    minimum_mev: float
    maximum_mev: float
    bin_width_mev: Optional[float] = None
    edges_mev: Optional[Tuple[float, ...]] = None


@dataclass(frozen=True)
class SkyGridConfig:
    """HEALPix 天空网格配置。"""

    grid_type: str
    nside: int
    nested: bool


@dataclass(frozen=True)
class TriggerConfig:
    """数字化后事件触发配置。"""

    required_channels: Tuple[str, ...]
    minimum_hit_energy_mev: Mapping[str, float]
    coincidence_window_ns: Optional[float]


@dataclass(frozen=True)
class RuntimeConfig:
    """单个 worker 内的数值库线程策略。"""

    numerical_threads_per_worker: int


@dataclass(frozen=True)
class MemoryGuardConfig:
    """数据集并行时的内存保护参数。"""

    enabled: bool
    minimum_available_gib: float
    estimated_worker_peak_gib: float
    poll_interval_seconds: float = 2.0
    maximum_retries: int = 2


@dataclass(frozen=True)
class BatchConfig:
    """批处理并行上限；maximum_workers 不是强制实际并发数。"""

    maximum_workers: int
    memory_guard: MemoryGuardConfig


@dataclass(frozen=True)
class ResponseConfig:
    """响应库适配器配置；adapter 不是正式格式承诺。"""

    adapter: str
    library_path: Path
    library_status: str
    overwrite_existing: bool = False
    parameters: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ReconstructionConfig:
    """LM-MLEM 迭代、早停、灵敏度选择和快照策略。"""

    sensitivity_kind: str
    maximum_iterations: int
    minimum_iterations: int
    denominator_floor: float
    sensitivity_floor: float
    likelihood_relative_tolerance: Optional[float]
    image_relative_tolerance: Optional[float]
    convergence_patience: int
    snapshot_first_iterations: int
    snapshot_interval: int


@dataclass(frozen=True)
class EventResponseConfig:
    """事件响应模型及其显式参数。"""

    model_id: str
    parameters: Mapping[str, Any]


@dataclass(frozen=True)
class BackgroundConfig:
    """固定背景/离群分量；第一版不在 MLEM 中共同估计背景。"""

    mode: str
    event_density: float
    expected_count: float


@dataclass(frozen=True)
class VisualizationConfig:
    """像素填充图、平滑和相机居中投影配置。"""

    enabled: bool
    display_up_direction: Tuple[float, float, float]
    smoothing_sigma_deg: float
    smoothing_chunk_size: int
    maximum_numpy_smoothing_pixels: int
    raster_width: int
    raster_height: int
    dpi: int
    energy_bands_mev: Tuple[Tuple[float, float], ...]
    file_names: Mapping[str, str]


@dataclass(frozen=True)
class OutputConfig:
    """数值与摘要输出文件名。"""

    file_names: Mapping[str, str]


@dataclass(frozen=True)
class EiidConfig:
    """EIID 的完整类型化配置。

    `source_path` 用于把未来输入/输出相对路径稳定地解析为相对于配置文件的
    路径，而不是相对于进程启动目录。
    """

    schema_version: str
    profile_purpose: str
    paths: ProjectPathsConfig
    coordinates: CoordinateConfig
    chamber_to_channel: Mapping[int, str]
    channel_to_layer: Mapping[str, int]
    energy_grid: EnergyGridConfig
    sky_grid: SkyGridConfig
    trigger: TriggerConfig
    runtime: RuntimeConfig
    batch: BatchConfig
    source_path: Path
    raw_payload: Dict[str, Any] = field(repr=False)
    response: Optional[ResponseConfig] = None
    reconstruction: Optional[ReconstructionConfig] = None
    event_response: Optional[EventResponseConfig] = None
    background: Optional[BackgroundConfig] = None
    visualization: Optional[VisualizationConfig] = None
    output: Optional[OutputConfig] = None

    @property
    def base_directory(self) -> Path:
        """配置文件所在目录。"""

        return self.source_path.parent

    def resolve_path(self, value: str) -> Path:
        """解析并检查项目内路径；不允许输入/输出逃出 EIID 根目录。"""

        path = Path(str(value)).expanduser()
        if path.is_absolute():
            resolved = path.resolve()
        else:
            resolved = (self.base_directory / path).resolve()
        try:
            resolved.relative_to(self.paths.project_root)
        except ValueError as error:
            raise ValueError(
                "配置路径超出 EIID 项目根目录：" + str(resolved)
            ) from error
        return resolved

    def as_dict(self) -> Dict[str, Any]:
        """返回深复制，防止调用者修改内部配置快照。"""

        return deepcopy(self.raw_payload)
