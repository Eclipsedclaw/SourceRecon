"""与输入格式和重建算法解耦的统一领域对象。"""

from .dataset import DatasetMetadata, EventDataset
from .deposit import DetectorDeposit
from .enums import Channel, EventTopology, RejectionReason, SequenceClass
from .event import MeasuredEvent
from .grid import EnergyGrid, SkyEnergyGrid
from .hit import DigitizedHit
from .truth import SimulationTruth

__all__ = [
    "Channel",
    "DatasetMetadata",
    "DetectorDeposit",
    "DigitizedHit",
    "EnergyGrid",
    "EventDataset",
    "EventTopology",
    "MeasuredEvent",
    "RejectionReason",
    "SequenceClass",
    "SimulationTruth",
    "SkyEnergyGrid",
]
