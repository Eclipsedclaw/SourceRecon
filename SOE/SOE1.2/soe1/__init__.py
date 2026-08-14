"""
SOE1.2：面向未知入射能量 2-hit 事件的球面 SOE 重建程序。

包内只暴露稳定的高层接口。具体的 ROOT/TSV 读取、康普顿运动学、
探测器响应与马尔可夫链采样分别放在独立子包中，避免入口脚本堆积逻辑。
"""

from .configuration import Configuration

__all__ = ["Configuration"]
