"""响应函数、灵敏度和响应库适配器。

重建器只依赖本包的领域接口，不依赖 NPZ、HDF5、ROOT 等具体存储格式。
"""

from .analytic import AnalyticComptonResponse
from .hybrid import HybridMonteCarloResponse
from .base import EventResponseModel
from .builder import EventKernelBatch, EventKernelBuilder
from .campaign import ResponseCampaignBuilder, ResponseNodeTable
from .library import ResponseLibrary, ResponseLibraryMetadata
from .sensitivity import (
    SensitivityBundle,
    SensitivityEstimator,
    SensitivityKind,
    SensitivityMap,
)
from .sparse import SparseEventResponse
from .storage import PrototypeNpzJsonResponseStore
from .portable_store import PortableNpzJsonResponseStore, ResponseStoreFactory

__all__ = [
    "AnalyticComptonResponse",
    "HybridMonteCarloResponse",
    "EventResponseModel",
    "EventKernelBatch",
    "EventKernelBuilder",
    "ResponseCampaignBuilder",
    "ResponseNodeTable",
    "PrototypeNpzJsonResponseStore",
    "PortableNpzJsonResponseStore",
    "ResponseStoreFactory",
    "ResponseLibrary",
    "ResponseLibraryMetadata",
    "SensitivityBundle",
    "SensitivityEstimator",
    "SensitivityKind",
    "SensitivityMap",
    "SparseEventResponse",
]
