from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd

from ..domain import EventKernel
from ..geometry import HealpixPixelizer
from ..reconstruction import ReconstructionResult
from ..response import DiscreteSpectrumPrior
from .plots import DiagnosticPlotWriter


class OutputWriter:
    """
    保存可复核、可继续分析的数值结果，不在重建核心中混入绘图代码。

    CSV 方便组内同学直接查看；NPY 保留完整精度，适合服务器后处理。
    """

    def __init__(
        self,
        output_directory: Path,
        pixelizer: HealpixPixelizer,
    ):
        self.output_directory = output_directory
        self.pixelizer = pixelizer

    def write_all(
        self,
        result: ReconstructionResult,
        kernels: List[EventKernel],
        spectrum: DiscreteSpectrumPrior,
        run_summary: Dict[str, object],
        configuration: Dict[str, object],
    ) -> Dict[str, str]:
        self.output_directory.mkdir(parents=True, exist_ok=True)
        paths = {}

        paths["posterior_mean_npy"] = self._save_array(
            "posterior_mean_map.npy",
            result.posterior_mean_map,
        )
        paths["posterior_variance_npy"] = self._save_array(
            "posterior_variance_map.npy",
            result.posterior_variance_map,
        )
        paths["sky_map_csv"] = self._write_sky_map(result)
        paths["spectrum_prior_csv"] = self._write_spectrum(spectrum)
        plot_writer = DiagnosticPlotWriter(
            output_directory=self.output_directory,
            pixelizer=self.pixelizer,
        )
        paths["posterior_mean_sky_map_png"] = (
            plot_writer.write_sky_map(result)
        )
        paths["spectrum_prior_png"] = plot_writer.write_spectrum(spectrum)
        paths["event_hypothesis_posterior_csv"] = (
            self._write_hypothesis_posterior(result, kernels)
        )
        paths["final_event_states_csv"] = self._write_final_states(
            result,
            kernels,
        )
        paths["run_summary_json"] = self._write_json(
            "run_summary.json",
            run_summary,
        )
        paths["configuration_snapshot_json"] = self._write_json(
            "configuration_snapshot.json",
            configuration,
        )
        return paths

    def _write_sky_map(self, result: ReconstructionResult) -> str:
        rows = []
        for pixel in range(self.pixelizer.pixel_count):
            direction = self.pixelizer.pixel_to_direction(pixel)
            longitude = float(np.arctan2(direction[1], direction[0]))
            latitude = float(np.arcsin(np.clip(direction[2], -1.0, 1.0)))
            rows.append(
                {
                    "pixel_index": pixel,
                    "x": direction[0],
                    "y": direction[1],
                    "z": direction[2],
                    "longitude_deg": np.rad2deg(longitude),
                    "latitude_deg": np.rad2deg(latitude),
                    "posterior_mean_count": result.posterior_mean_map[pixel],
                    "posterior_variance": result.posterior_variance_map[pixel],
                    "final_count": result.final_counts[pixel],
                }
            )
        path = self.output_directory / "sky_map.csv"
        pd.DataFrame(rows).to_csv(path, index=False)
        return str(path)

    def _write_spectrum(self, spectrum: DiscreteSpectrumPrior) -> str:
        path = self.output_directory / "spectrum_prior.csv"
        pd.DataFrame(
            {
                "incident_energy_mev": spectrum.energies_mev,
                "prior_probability": spectrum.probabilities,
            }
        ).to_csv(path, index=False)
        return str(path)

    def _write_hypothesis_posterior(
        self,
        result: ReconstructionResult,
        kernels: List[EventKernel],
    ) -> str:
        rows = []
        for event_index, kernel in enumerate(kernels):
            prior_weights = np.asarray(
                [hypothesis.weight for hypothesis in kernel.hypotheses],
                dtype=float,
            )
            prior_weights /= prior_weights.sum()
            visits = result.hypothesis_visit_counts[event_index]
            posterior = visits / max(result.saved_sample_count, 1)

            for hypothesis_index, hypothesis in enumerate(
                kernel.hypotheses
            ):
                row = {
                    "event_index": event_index,
                    "event_id": kernel.event.event_id,
                    "n_hits": kernel.event.n_hits,
                    "terminal_channel": kernel.event.terminal_channel,
                    "hypothesis_index": hypothesis_index,
                    "incident_energy_mev": hypothesis.incident_energy_mev,
                    "deposition_class": hypothesis.deposition_class.value,
                    "scatter_angle_deg": np.rad2deg(
                        hypothesis.scatter_angle_rad
                    ),
                    "arm_sigma_deg": np.rad2deg(
                        hypothesis.arm_sigma_rad
                    ),
                    "independent_prior_probability": prior_weights[
                        hypothesis_index
                    ],
                    "soe_posterior_visit_fraction": posterior[
                        hypothesis_index
                    ],
                }
                row.update(
                    {
                        "diagnostic_" + key: value
                        for key, value in hypothesis.diagnostics.items()
                    }
                )
                rows.append(row)

        path = self.output_directory / "event_hypothesis_posterior.csv"
        pd.DataFrame(rows).to_csv(path, index=False)
        return str(path)

    def _write_final_states(
        self,
        result: ReconstructionResult,
        kernels: List[EventKernel],
    ) -> str:
        rows = []
        for state in result.final_states:
            kernel = kernels[state.event_index]
            hypothesis = kernel.hypotheses[state.hypothesis_index]
            rows.append(
                {
                    "event_index": state.event_index,
                    "event_id": kernel.event.event_id,
                    "n_hits": kernel.event.n_hits,
                    "hypothesis_index": state.hypothesis_index,
                    "incident_energy_mev": hypothesis.incident_energy_mev,
                    "deposition_class": hypothesis.deposition_class.value,
                    "pixel_index": state.pixel_index,
                    "sky_x": state.direction_sky[0],
                    "sky_y": state.direction_sky[1],
                    "sky_z": state.direction_sky[2],
                }
            )
        path = self.output_directory / "final_event_states.csv"
        pd.DataFrame(rows).to_csv(path, index=False)
        return str(path)

    def _save_array(self, file_name: str, value: np.ndarray) -> str:
        path = self.output_directory / file_name
        np.save(path, value)
        return str(path)

    def _write_json(self, file_name: str, value) -> str:
        path = self.output_directory / file_name
        with path.open("w", encoding="utf-8") as file:
            json.dump(value, file, ensure_ascii=False, indent=2)
        return str(path)
