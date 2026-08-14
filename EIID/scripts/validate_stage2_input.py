#!/usr/bin/env python3
"""阶段 2 实验输入、统一领域对象和 ch1+ch2 触发冒烟验证。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from eiid.configuration import load_config
from eiid.detector import TriggerPolicy
from eiid.io import EventIngestionPipeline, EventSourceFactory


def validate(config_path: str):
    config = load_config(config_path)
    source = EventSourceFactory(config).create()
    trigger = TriggerPolicy(
        config.trigger.minimum_hit_energy_mev,
        config.trigger.coincidence_window_ns,
    )
    result = EventIngestionPipeline(source, trigger).run()
    accepted_ids = [event.event_id for event in result.accepted_events]
    rejected_ids = [event.event_id for event in result.rejected_events]
    if not accepted_ids or not rejected_ids:
        raise RuntimeError("stage2 smoke 必须同时覆盖接受和拒绝事件。")
    if any(event.truth is not None for event in result.dataset.events):
        raise RuntimeError("实验输入不得包含 SimulationTruth。")
    return {
        "status": "ok",
        "dataset_id": result.dataset.metadata.dataset_id,
        "source_type": result.dataset.metadata.source_type,
        "event_count": len(result.dataset.events),
        "accepted_event_count": len(result.accepted_events),
        "rejected_event_count": len(result.rejected_events),
        "accepted_event_ids": accepted_ids,
        "rejected_event_ids": rejected_ids,
        "input_summary": dict(result.dataset.summary),
        "same_layer_multi_pixel_preserved": any(
            len(event.hits) > len(set(hit.layer for hit in event.hits))
            for event in result.dataset.events
        ),
    }


def main():
    parser = argparse.ArgumentParser(description="验证 EIID 阶段 2 输入链。")
    parser.add_argument("--config", required=True)
    arguments = parser.parse_args()
    print(
        json.dumps(validate(arguments.config), ensure_ascii=False, indent=2),
        flush=True,
    )


if __name__ == "__main__":
    main()

