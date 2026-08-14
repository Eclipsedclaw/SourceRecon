#!/usr/bin/env python3
"""独立验证响应库完整性、网格、物理单位和正式使用状态。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from eiid.response import ResponseStoreFactory


def main():
    parser = argparse.ArgumentParser(description="验证 EIID 响应库。")
    parser.add_argument("--adapter", required=True)
    parser.add_argument("--library", required=True)
    parser.add_argument("--require-validated-physical", action="store_true")
    args = parser.parse_args()
    store = ResponseStoreFactory.create(args.adapter)
    library = store.load(args.library)
    if "arm_sigma_deg" not in library.calibration_arrays:
        raise ValueError("混合响应库缺少 arm_sigma_deg。")
    expected_shape = library.sensitivities.conditional.shape
    arm = np.asarray(library.calibration_arrays["arm_sigma_deg"], dtype=float)
    if arm.shape != expected_shape or np.any(~np.isfinite(arm)) or np.any(arm <= 0.0):
        raise ValueError("arm_sigma_deg 形状或数值无效。")
    for name, values in library.calibration_arrays.items():
        if name.startswith("topology_probability__"):
            array = np.asarray(values, dtype=float)
            if array.shape != expected_shape or np.any(array < 0.0) or np.any(array > 1.0):
                raise ValueError("拓扑概率形状或范围无效：" + name)
    if args.require_validated_physical and library.metadata.library_status != "validated_physical":
        raise ValueError("响应库尚未标记 validated_physical。")
    if args.require_validated_physical and library.sensitivities.conditional.metadata.get(
        "generated_count_included_zero_deposit_events"
    ) is not True:
        raise ValueError("正式响应分母没有证明包含零沉积 primary。")
    result = {
        "status": "ok",
        "library_id": library.metadata.library_id,
        "library_status": library.metadata.library_status,
        "sky_grid": dict(library.sky_grid),
        "energy_bin_count": library.energy_grid.bin_count,
        "available_sensitivity": [
            item.kind.value
            for item in (
                library.sensitivities.conditional,
                library.sensitivities.effective_area,
                library.sensitivities.finite_distance_emitted,
            )
            if item is not None
        ],
        "physical_use_allowed": library.metadata.library_status == "validated_physical",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
