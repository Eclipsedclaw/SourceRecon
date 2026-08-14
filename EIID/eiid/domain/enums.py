"""领域枚举和可组合拒绝原因。"""

from enum import Enum, IntFlag


class Channel(str, Enum):
    """算法通道；名称与 Geant4 chamberID 通过配置映射。"""

    CH0 = "ch0"
    CH1 = "ch1"
    CH2 = "ch2"


class SequenceClass(str, Enum):
    """事件层序分类；UNKNOWN/BACKSCATTER 不能在 I/O 层被删除。"""

    NORMAL_FORWARD = "normal_forward"
    BACKSCATTER = "backscatter"
    AMBIGUOUS = "ambiguous"
    UNKNOWN = "unknown"


class EventTopology(str, Enum):
    """响应模型可扩展的粗粒度事件拓扑。"""

    TWO_HIT = "two_hit"
    THREE_OR_MORE_HIT = "three_or_more_hit"
    PAIR_PRODUCTION = "pair_production"
    OUTLIER = "outlier"
    UNKNOWN = "unknown"


class RejectionReason(IntFlag):
    """触发/选择失败原因位掩码，可同时保留多个原因。"""

    NONE = 0
    NO_VALID_HIT = 1 << 0
    MISSING_CH1 = 1 << 1
    MISSING_CH2 = 1 << 2
    COINCIDENCE_FAILED = 1 << 3
    QUALITY_REJECTED = 1 << 4

