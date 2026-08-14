"""数字化后 ch1+ch2 触发策略。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional, Tuple

import numpy as np

from ..domain import Channel, MeasuredEvent, RejectionReason


@dataclass(frozen=True)
class TriggerDecision:
    """触发结果和完整失败原因。"""

    accepted: bool
    reasons: RejectionReason
    valid_hit_ids: Tuple[str, ...]


class TriggerPolicy:
    """实现已确定的数字化后 `ch1 AND ch2` 触发。

    ch0 是否存在不会改变 `accepted`。阈值和符合窗口来自配置，不在代码中
    固定为实验参数。
    """

    REQUIRED_CHANNELS = (Channel.CH1, Channel.CH2)

    def __init__(
        self,
        minimum_hit_energy_mev: Mapping[Channel, float],
        coincidence_window_ns: Optional[float] = None,
    ):
        thresholds = {
            key if isinstance(key, Channel) else Channel(key): float(value)
            for key, value in minimum_hit_energy_mev.items()
        }
        missing = [channel.value for channel in Channel if channel not in thresholds]
        if missing:
            raise ValueError("触发阈值缺少通道：" + ", ".join(missing))
        if any(not np.isfinite(value) or value < 0.0 for value in thresholds.values()):
            raise ValueError("触发阈值必须为非负有限值。")
        if coincidence_window_ns is not None and float(coincidence_window_ns) <= 0.0:
            raise ValueError("coincidence_window_ns 必须为正数或 None。")
        self.thresholds = thresholds
        self.coincidence_window_ns = (
            None if coincidence_window_ns is None else float(coincidence_window_ns)
        )

    def _valid_hits(self, event: MeasuredEvent, channel: Channel):
        threshold = self.thresholds[channel]
        return tuple(
            hit
            for hit in event.hits_in_channel(channel)
            if hit.is_valid_readout and hit.energy_mev > threshold
        )

    def evaluate(self, event: MeasuredEvent) -> TriggerDecision:
        """返回触发决定；不修改也不删除输入事件。"""

        valid_by_channel = {
            channel: self._valid_hits(event, channel) for channel in Channel
        }
        all_valid = tuple(
            hit for channel in Channel for hit in valid_by_channel[channel]
        )
        reasons = RejectionReason.NONE
        if not all_valid:
            reasons |= RejectionReason.NO_VALID_HIT
        if not valid_by_channel[Channel.CH1]:
            reasons |= RejectionReason.MISSING_CH1
        if not valid_by_channel[Channel.CH2]:
            reasons |= RejectionReason.MISSING_CH2

        if (
            self.coincidence_window_ns is not None
            and valid_by_channel[Channel.CH1]
            and valid_by_channel[Channel.CH2]
        ):
            coincident = any(
                first.time_ns is not None
                and second.time_ns is not None
                and abs(float(first.time_ns) - float(second.time_ns))
                <= self.coincidence_window_ns
                for first in valid_by_channel[Channel.CH1]
                for second in valid_by_channel[Channel.CH2]
            )
            if not coincident:
                reasons |= RejectionReason.COINCIDENCE_FAILED

        accepted = reasons == RejectionReason.NONE
        return TriggerDecision(
            accepted=accepted,
            reasons=reasons,
            valid_hit_ids=tuple(hit.hit_id for hit in all_valid),
        )

