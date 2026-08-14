"""Geant4 chamber、算法通道和物理层映射。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from ..domain import Channel


@dataclass(frozen=True)
class ChannelMapping:
    """把可配置的外部编号集中转换为领域通道。"""

    chamber_to_channel: Mapping[int, Channel]
    channel_to_layer: Mapping[Channel, int]

    def __post_init__(self) -> None:
        chambers = {
            int(key): value if isinstance(value, Channel) else Channel(value)
            for key, value in self.chamber_to_channel.items()
        }
        layers = {
            key if isinstance(key, Channel) else Channel(key): int(value)
            for key, value in self.channel_to_layer.items()
        }
        if set(chambers.values()) != set(Channel):
            raise ValueError("chamber_to_channel 必须覆盖 ch0/ch1/ch2。")
        if set(layers) != set(Channel):
            raise ValueError("channel_to_layer 必须覆盖 ch0/ch1/ch2。")
        if any(layer < 0 for layer in layers.values()):
            raise ValueError("物理层编号不能为负。")
        object.__setattr__(self, "chamber_to_channel", chambers)
        object.__setattr__(self, "channel_to_layer", layers)

    def channel_for_chamber(self, chamber_id: int) -> Channel:
        try:
            return self.chamber_to_channel[int(chamber_id)]
        except KeyError as error:
            raise KeyError("未知 chamberID：" + str(chamber_id)) from error

    def layer_for_channel(self, channel: Channel) -> int:
        selected = channel if isinstance(channel, Channel) else Channel(channel)
        return self.channel_to_layer[selected]

