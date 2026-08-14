"""限制每个 worker 内数值库线程，避免数据集并行时过度超卖 CPU。"""

import os
from typing import Dict


NUMERICAL_THREAD_VARIABLES = (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
    "BLIS_NUM_THREADS",
)


def apply_numerical_thread_limits(thread_count: int = 1, overwrite: bool = False) -> Dict[str, str]:
    """设置常见数值库线程环境变量。

    最好在导入 NumPy/SciPy 前调用。默认不覆盖管理员或作业系统已经设置的值；
    服务器启动脚本会显式导出这些变量。
    """

    count = int(thread_count)
    if count <= 0:
        raise ValueError("thread_count 必须大于 0。")
    for name in NUMERICAL_THREAD_VARIABLES:
        if overwrite or name not in os.environ:
            os.environ[name] = str(count)
    return {name: os.environ[name] for name in NUMERICAL_THREAD_VARIABLES}

