"""输入接口：实验 TSV 与 Geant4 ROOT 最终都输出 InputDataset。"""

from .base import EventSource
from .experiment import ExperimentalTsvEventSource
from .geant4 import Geant4RootEventSource, StreamingGeant4RootEventSource

__all__ = [
    "EventSource",
    "ExperimentalTsvEventSource",
    "Geant4RootEventSource",
    "StreamingGeant4RootEventSource",
]
