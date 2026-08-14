"""端到端重建的原子数值、事件和摘要输出。"""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from typing import Mapping, Sequence

import numpy as np


def _atomic_json(path: Path, payload) -> None:
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write("\n")
    os.replace(str(temporary), str(path))


class ReconstructionResultWriter:
    """把算法结果写入 RunContext 标准目录，文件名全部来自配置。"""

    def __init__(self, run_context, output_config):
        self.context = run_context
        self.config = output_config

    def write_joint_image(
        self, image, energy_grid, sky_grid, joint_standard_error=None,
        uncertainty_metadata=None,
    ) -> Path:
        path = (
            self.context.paths.numerical_directory
            / self.config.file_names["final_joint_image"]
        )
        temporary = path.with_name(path.name + ".tmp")
        joint = np.asarray(image, dtype=float).reshape(
            sky_grid.pixel_count, energy_grid.bin_count
        )
        payload = {
                "joint_image": joint,
                "sky_marginal": np.sum(joint, axis=1),
                "energy_marginal": np.sum(joint, axis=0),
                "energy_edges_mev": energy_grid.edges_mev,
                "sky_pixel_directions": sky_grid.all_pixel_directions(),
                "healpix_nside": np.asarray([sky_grid.nside], dtype=np.int64),
                "healpix_nested": np.asarray([sky_grid.nested], dtype=np.bool_),
        }
        if joint_standard_error is not None:
            error = np.asarray(joint_standard_error, dtype=float).reshape(joint.shape)
            payload["joint_standard_error"] = error
            payload["energy_marginal_standard_error"] = np.sqrt(
                np.nansum(error ** 2, axis=0)
            )
            payload["uncertainty_method"] = np.asarray(
                [str(dict(uncertainty_metadata or {}).get("method", "unspecified"))]
            )
        with temporary.open("wb") as stream:
            np.savez_compressed(
                stream,
                **payload
            )
        os.replace(str(temporary), str(path))
        return path

    def write_event_summary(self, events, responses) -> Path:
        path = (
            self.context.paths.numerical_directory
            / self.config.file_names["event_summary"]
        )
        temporary = path.with_name(path.name + ".tmp")
        response_by_id = {item.event_id: item for item in responses}
        with temporary.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(
                stream,
                fieldnames=(
                    "event_id",
                    "hit_count",
                    "total_deposited_energy_mev",
                    "sequence_class",
                    "topology",
                    "response_nonzero_cell_count",
                    "response_empty_reason",
                ),
            )
            writer.writeheader()
            for event in events:
                response = response_by_id[event.event_id]
                writer.writerow(
                    {
                        "event_id": event.event_id,
                        "hit_count": len(event.hits),
                        "total_deposited_energy_mev": (
                            event.total_deposited_energy_mev
                        ),
                        "sequence_class": event.sequence_class.value,
                        "topology": event.topology.value,
                        "response_nonzero_cell_count": response.nonzero_count,
                        "response_empty_reason": response.diagnostics.get(
                            "empty_reason", ""
                        ),
                    }
                )
        os.replace(str(temporary), str(path))
        return path

    def write_dataset_metadata(self, dataset, ingestion_summary) -> Path:
        path = (
            self.context.paths.run_directory
            / self.config.file_names["dataset_metadata"]
        )
        payload = {
            "dataset_id": dataset.metadata.dataset_id,
            "source_type": dataset.metadata.source_type,
            "schema_version": dataset.metadata.schema_version,
            "attributes": dict(dataset.metadata.attributes),
            "input_summary": dict(dataset.summary),
            "ingestion_summary": dict(ingestion_summary),
        }
        _atomic_json(path, payload)
        return path

    def write_reconstruction_summary(self, summary: Mapping) -> Path:
        path = (
            self.context.paths.run_directory
            / self.config.file_names["reconstruction_summary"]
        )
        _atomic_json(path, dict(summary))
        return path
