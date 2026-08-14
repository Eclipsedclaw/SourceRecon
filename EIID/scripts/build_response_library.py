#!/usr/bin/env python3
"""从离线 Geant4 节点统计构建可移植响应库。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from eiid.domain import EnergyGrid
from eiid.response import (
    ResponseCampaignBuilder,
    ResponseLibraryMetadata,
    ResponseNodeTable,
    ResponseStoreFactory,
)
from eiid.response.campaign import utc_now


def _inside(root: Path, value, label: str) -> Path:
    path = Path(value).expanduser()
    resolved = path.resolve() if path.is_absolute() else (root / path).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise ValueError(label + " 必须位于 EIID project_root 内。") from error
    return resolved


def build(config_path: str):
    path = Path(config_path).expanduser().resolve()
    with path.open("r", encoding="utf-8") as stream:
        config = json.load(stream)
    if config.get("schema_version") != "eiid.response_build.v1":
        raise ValueError("响应构建 schema_version 必须是 eiid.response_build.v1。")
    if config.get("adapter") != "portable_npz_json_v1":
        raise ValueError("第一版生产响应构建只允许 portable_npz_json_v1。")
    root_value = Path(str(config["project_root"])).expanduser()
    project_root = (
        root_value.resolve()
        if root_value.is_absolute()
        else (path.parent / root_value).resolve()
    )
    statistics = _inside(project_root, config["node_statistics_npz"], "node_statistics_npz")
    output = _inside(project_root, config["output_library"], "output_library")
    grid = config["grid"]
    if "energy_edges_mev" in grid:
        energy = EnergyGrid(grid["energy_edges_mev"])
    else:
        energy = EnergyGrid.uniform(
            float(grid["minimum_mev"]),
            float(grid["maximum_mev"]),
            float(grid["bin_width_mev"]),
        )
    sky = {
        "type": "healpix",
        "nside": int(grid["nside"]),
        "nested": bool(grid["nested"]),
        "pixel_count": 12 * int(grid["nside"]) ** 2,
    }
    raw = config["metadata"]
    metadata = ResponseLibraryMetadata(
        library_id=str(raw["library_id"]),
        schema_version="1.0.0",
        library_status=str(raw["library_status"]),
        response_model_kind="hybrid_monte_carlo_arm_v1",
        geometry_version=str(raw["geometry_version"]),
        physics_list=str(raw["physics_list"]),
        digitizer_version=str(raw["digitizer_version"]),
        trigger_definition="valid_hit(ch1) AND valid_hit(ch2)",
        producer_run_id=raw.get("producer_run_id"),
        created_utc=utc_now(),
        attributes=dict(raw.get("attributes", {})),
    )
    library = ResponseCampaignBuilder().build(
        ResponseNodeTable.from_npz(statistics),
        energy,
        sky,
        metadata,
        config["normalization"],
    )
    store = ResponseStoreFactory.create(str(config["adapter"]))
    manifest = store.save(library, output, overwrite=bool(config.get("overwrite", False)))
    return {
        "status": "ok",
        "library_id": metadata.library_id,
        "library_status": metadata.library_status,
        "manifest": str(manifest),
        "physical_use_allowed": metadata.library_status == "validated_physical",
    }


def main():
    parser = argparse.ArgumentParser(description="构建 EIID 离线响应库。")
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.config), ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
