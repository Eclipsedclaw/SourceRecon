"""模拟和实验的独立输入适配器。"""

from .base import EventSource, IngestedDataset
from .experiment import ExperimentalDelimitedEventSource, LinearCalibrationTable
from .factory import EventSourceFactory
from .geant4_formal import FormalGeant4RootEventSource
from .geant4_legacy import (
    LegacyGeant4RootEventSource,
    LegacyStep,
    LegacyStepAggregator,
)
from .pipeline import EventIngestionPipeline

__all__ = [
    "EventIngestionPipeline",
    "EventSource",
    "EventSourceFactory",
    "ExperimentalDelimitedEventSource",
    "IngestedDataset",
    "FormalGeant4RootEventSource",
    "LegacyGeant4RootEventSource",
    "LegacyStep",
    "LegacyStepAggregator",
    "LinearCalibrationTable",
]
