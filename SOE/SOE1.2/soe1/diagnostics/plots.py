from __future__ import annotations

from pathlib import Path

import matplotlib

# 服务器通常没有图形桌面，必须在导入 pyplot 前选择无窗口 backend。
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from ..geometry import HealpixPixelizer
from ..reconstruction import ReconstructionResult
from ..response import DiscreteSpectrumPrior


class DiagnosticPlotWriter:
    """只负责把数值结果画成组内可快速查看的 PNG，不参与重建计算。"""

    def __init__(
        self,
        output_directory: Path,
        pixelizer: HealpixPixelizer,
    ):
        self.output_directory = output_directory
        self.pixelizer = pixelizer

    def write_sky_map(self, result: ReconstructionResult) -> str:
        path = self.output_directory / "posterior_mean_sky_map.png"
        self.pixelizer.hp.mollview(
            result.posterior_mean_map,
            nest=self.pixelizer.nested,
            title="SOE1 posterior mean origin count",
            unit="mean event count / HEALPix pixel",
            cmap="viridis",
        )
        self.pixelizer.hp.graticule()
        plt.savefig(path, dpi=180, bbox_inches="tight")
        plt.close("all")
        return str(path)

    def write_spectrum(self, spectrum: DiscreteSpectrumPrior) -> str:
        path = self.output_directory / "spectrum_prior.png"
        figure, axis = plt.subplots(figsize=(8.0, 4.5))
        axis.plot(
            spectrum.energies_mev,
            spectrum.probabilities,
            color="tab:blue",
            linewidth=1.5,
        )
        axis.set_xlabel("Incident-energy hypothesis (MeV)")
        axis.set_ylabel("Prior probability per energy bin")
        axis.set_title("SOE1 global spectrum prior")
        axis.grid(alpha=0.25)
        figure.tight_layout()
        figure.savefig(path, dpi=180)
        plt.close(figure)
        return str(path)

