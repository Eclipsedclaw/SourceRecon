from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


class BatchQualityReporter:
    """汇总所有模拟条件，并生成跨能量、距离和方位的比较图。"""

    POSITION_ORDER = ["center", "xm", "xp", "ym", "yp"]

    def __init__(
        self,
        output_root: Path,
        analysis_config: Dict[str, object] = None,
    ):
        self.output_root = Path(output_root)
        self.overall_directory = self.output_root / "overall"
        self.figure_directory = self.overall_directory / "figures"
        self.montage_directory = self.overall_directory / "montages"
        self.config = analysis_config or {}
        self.dpi = int(self.config.get("figure_dpi", 170))

    def write_all(
        self,
        metrics: List[Dict[str, object]],
        failures: List[Dict[str, object]],
    ) -> Dict[str, str]:
        self.figure_directory.mkdir(parents=True, exist_ok=True)
        self.montage_directory.mkdir(parents=True, exist_ok=True)
        frame = pd.DataFrame(metrics)
        if frame.empty:
            raise RuntimeError("没有成功完成的数据集，无法生成总体报告。")
        frame = self._sort_frame(frame)

        paths = {}
        summary_csv = self.overall_directory / "batch_summary.csv"
        frame.to_csv(summary_csv, index=False)
        paths["batch_summary_csv"] = str(summary_csv)
        paths["batch_summary_json"] = self._write_json(
            self.overall_directory / "batch_summary.json",
            json.loads(frame.to_json(orient="records")),
        )
        failure_csv = self.overall_directory / "failed_datasets.csv"
        pd.DataFrame(failures).to_csv(failure_csv, index=False)
        paths["failed_datasets_csv"] = str(failure_csv)
        paths["failed_datasets_json"] = self._write_json(
            self.overall_directory / "failed_datasets.json",
            failures,
        )

        paths["angular_error_png"] = self._metric_small_multiples(
            frame,
            "centroid_angular_error_deg",
            "01_angular_error_vs_energy.png",
            "Centroid angular error (deg)",
            "Source localization error",
        )
        paths["containment_png"] = self._metric_small_multiples(
            frame,
            "containment_r68_deg",
            "02_r68_vs_energy.png",
            "R68 containment radius (deg)",
            "Image concentration around truth",
        )
        paths["energy_error_png"] = self._metric_small_multiples(
            frame,
            "energy_mae_mev",
            "03_energy_mae_vs_energy.png",
            "Per-event energy MAE (MeV)",
            "Energy reconstruction error",
        )
        paths["efficiency_png"] = self._efficiency_plot(frame)
        paths["direction_recovery_png"] = self._direction_recovery(frame)
        paths["angular_heatmap_png"] = self._heatmap(
            frame,
            "centroid_angular_error_deg",
            "06_angular_error_heatmap.png",
            "Centroid angular error (deg)",
        )
        paths["r68_heatmap_png"] = self._heatmap(
            frame,
            "containment_r68_deg",
            "07_r68_heatmap.png",
            "R68 containment radius (deg)",
        )
        paths["overall_dashboard_png"] = self._dashboard(frame, failures)
        paths.update(self._montages(frame))
        return paths

    def _metric_small_multiples(
        self,
        frame,
        column,
        file_name,
        y_label,
        title,
    ) -> str:
        path = self.figure_directory / file_name
        figure, axes = plt.subplots(
            2, 3, figsize=(14.0, 8.0), sharex=True, sharey=True
        )
        axes = axes.ravel()
        for axis, position in zip(axes, self.POSITION_ORDER):
            subset = frame.loc[frame["position_label"] == position]
            for distance, group in subset.groupby("distance_m"):
                group = group.sort_values("energy_mev")
                axis.plot(
                    group["energy_mev"],
                    group[column],
                    marker="o",
                    ms=4,
                    label=f"{distance:g} m",
                )
            axis.set_title(position)
            axis.grid(alpha=0.25)
            axis.set_xlabel("True energy (MeV)")
            axis.set_ylabel(y_label)
        axes[-1].axis("off")
        handles, labels = axes[0].get_legend_handles_labels()
        if handles:
            axes[-1].legend(handles, labels, loc="center", title="Distance")
        figure.suptitle(title, fontsize=15)
        figure.tight_layout(rect=(0, 0, 1, 0.96))
        figure.savefig(path, dpi=self.dpi)
        plt.close(figure)
        return str(path)

    def _efficiency_plot(self, frame) -> str:
        path = self.figure_directory / "04_event_efficiency.png"
        figure, axes = plt.subplots(1, 2, figsize=(12.5, 4.8))
        efficiency_column = (
            "imaging_fraction_of_generated_events"
            if "imaging_fraction_of_generated_events" in frame
            and frame["imaging_fraction_of_generated_events"].notna().any()
            else "imaging_fraction_of_all_events"
        )
        for distance, group in frame.groupby("distance_m"):
            averaged = group.groupby("energy_mev").mean(numeric_only=True)
            axes[0].plot(
                averaged.index,
                averaged[efficiency_column],
                marker="o",
                label=f"{distance:g} m",
            )
            axes[1].plot(
                averaged.index,
                averaged["kernel_survival_fraction_of_used_imaging"],
                marker="o",
                label=f"{distance:g} m",
            )
        axes[0].set_title(
            "Cross-layer imaging fraction of generated events"
            if efficiency_column
            == "imaging_fraction_of_generated_events"
            else "Cross-layer fraction of positive-deposition events"
        )
        axes[1].set_title("Valid-kernel fraction of sampled imaging events")
        for axis in axes:
            axis.set_xlabel("True energy (MeV)")
            axis.set_ylabel("Fraction")
            axis.set_ylim(bottom=0)
            axis.grid(alpha=0.25)
            axis.legend(title="Distance", fontsize=8)
        figure.tight_layout()
        figure.savefig(path, dpi=self.dpi)
        plt.close(figure)
        return str(path)

    def _direction_recovery(self, frame) -> str:
        path = self.figure_directory / "05_expected_vs_reconstructed.png"
        distances = sorted(frame["distance_m"].dropna().unique())
        figure, axes = plt.subplots(
            1,
            len(distances),
            figsize=(5.0 * len(distances), 4.8),
            squeeze=False,
        )
        for axis, distance in zip(axes.ravel(), distances):
            group = frame.loc[frame["distance_m"] == distance]
            axis.add_patch(
                plt.Circle(
                    (0, 0), 1, fill=False, color="black", lw=1.0
                )
            )
            for position in self.POSITION_ORDER:
                position_group = group.loc[
                    group["position_label"] == position
                ]
                if position_group.empty:
                    continue
                expected_x = position_group["expected_direction_x"].iloc[0]
                expected_y = position_group["expected_direction_y"].iloc[0]
                axis.scatter(
                    expected_x,
                    expected_y,
                    marker="*",
                    s=100,
                    color="black",
                )
                axis.scatter(
                    position_group["centroid_direction_x"],
                    position_group["centroid_direction_y"],
                    c=position_group["energy_mev"],
                    cmap="viridis",
                    vmin=frame["energy_mev"].min(),
                    vmax=frame["energy_mev"].max(),
                    s=36,
                )
                for _, row in position_group.iterrows():
                    axis.plot(
                        [
                            row["expected_direction_x"],
                            row["centroid_direction_x"],
                        ],
                        [
                            row["expected_direction_y"],
                            row["centroid_direction_y"],
                        ],
                        color="gray",
                        alpha=0.35,
                        lw=0.7,
                    )
            axis.set(
                title=f"Distance {distance:g} m",
                xlabel="direction x",
                ylabel="direction y",
                aspect="equal",
                xlim=(-0.38, 0.38),
                ylim=(-0.38, 0.38),
            )
            axis.grid(alpha=0.2)
        scalar = plt.cm.ScalarMappable(
            norm=plt.Normalize(
                frame["energy_mev"].min(),
                frame["energy_mev"].max(),
            ),
            cmap="viridis",
        )
        figure.colorbar(
            scalar,
            ax=list(axes.ravel()),
            shrink=0.78,
            label="True energy (MeV)",
        )
        figure.suptitle(
            "Expected stars and reconstructed centroids", fontsize=15
        )
        figure.subplots_adjust(top=0.86, wspace=0.30)
        figure.savefig(path, dpi=self.dpi, bbox_inches="tight")
        plt.close(figure)
        return str(path)

    def _heatmap(self, frame, value, file_name, colorbar_label) -> str:
        path = self.figure_directory / file_name
        condition = frame.apply(
            lambda row: f"z{row['distance_m']:g}m_{row['position_label']}",
            axis=1,
        )
        working = frame.assign(condition=condition)
        pivot = working.pivot_table(
            index="energy_mev",
            columns="condition",
            values=value,
            aggfunc="mean",
        )
        preferred = [
            f"z{distance:g}m_{position}"
            for distance in sorted(frame["distance_m"].unique())
            for position in self.POSITION_ORDER
        ]
        columns = [column for column in preferred if column in pivot]
        pivot = pivot.reindex(columns=columns)

        figure, axis = plt.subplots(
            figsize=(max(10, len(columns) * 0.75), 5.8)
        )
        image = axis.imshow(
            pivot.to_numpy(dtype=float),
            aspect="auto",
            cmap="magma_r",
        )
        axis.set_xticks(np.arange(len(columns)))
        axis.set_xticklabels(columns, rotation=50, ha="right")
        axis.set_yticks(np.arange(len(pivot.index)))
        axis.set_yticklabels([f"{value:g}" for value in pivot.index])
        axis.set(
            xlabel="Distance and source position",
            ylabel="True energy (MeV)",
            title=colorbar_label + " across all datasets",
        )
        plt.colorbar(image, ax=axis, label=colorbar_label)
        figure.tight_layout()
        figure.savefig(path, dpi=self.dpi)
        plt.close(figure)
        return str(path)

    def _dashboard(self, frame, failures) -> str:
        path = self.figure_directory / "08_overall_dashboard.png"
        figure, axes = plt.subplots(2, 2, figsize=(13.5, 9.0))
        for distance, group in frame.groupby("distance_m"):
            averaged = group.groupby("energy_mev").mean(numeric_only=True)
            axes[0, 0].plot(
                averaged.index,
                averaged["centroid_angular_error_deg"],
                marker="o",
                label=f"{distance:g} m",
            )
            axes[0, 1].plot(
                averaged.index,
                averaged["containment_r68_deg"],
                marker="o",
                label=f"{distance:g} m",
            )
            if "energy_mae_mev" in averaged:
                axes[1, 0].plot(
                    averaged.index,
                    1000.0 * averaged["energy_mae_mev"],
                    marker="o",
                    label=f"{distance:g} m",
                )
        axes[0, 0].set_title("Mean localization error over positions")
        axes[0, 1].set_title("Mean R68 over positions")
        axes[1, 0].set_title("Mean energy MAE over positions")
        axes[0, 0].set_ylabel("deg")
        axes[0, 1].set_ylabel("deg")
        axes[1, 0].set_ylabel("keV")
        for axis in (axes[0, 0], axes[0, 1], axes[1, 0]):
            axis.set_xlabel("True energy (MeV)")
            axis.grid(alpha=0.25)
            axis.legend(title="Distance", fontsize=8)

        axes[1, 1].axis("off")
        best = frame.loc[
            frame["centroid_angular_error_deg"].idxmin()
        ]
        worst = frame.loc[
            frame["centroid_angular_error_deg"].idxmax()
        ]
        text = [
            f"Successful datasets: {len(frame)}",
            f"Failed datasets: {len(failures)}",
            "",
            "Median centroid error:",
            f"  {frame['centroid_angular_error_deg'].median():.2f} deg",
            "Median R68:",
            f"  {frame['containment_r68_deg'].median():.2f} deg",
            "",
            "Best localization:",
            f"  {best['dataset_slug']}",
            f"  {best['centroid_angular_error_deg']:.2f} deg",
            "",
            "Worst localization:",
            f"  {worst['dataset_slug']}",
            f"  {worst['centroid_angular_error_deg']:.2f} deg",
        ]
        axes[1, 1].text(
            0.03,
            0.97,
            "\n".join(text),
            va="top",
            family="monospace",
            fontsize=12,
            linespacing=1.35,
        )
        figure.suptitle("SOE1.2 batch imaging quality overview", fontsize=16)
        figure.tight_layout(rect=(0, 0, 1, 0.96))
        figure.savefig(path, dpi=self.dpi)
        plt.close(figure)
        return str(path)

    def _montages(self, frame) -> Dict[str, str]:
        paths = {}
        for distance in sorted(frame["distance_m"].unique()):
            group = frame.loc[frame["distance_m"] == distance]
            energies = sorted(group["energy_mev"].unique())
            figure, axes = plt.subplots(
                len(energies),
                len(self.POSITION_ORDER),
                figsize=(3.0 * len(self.POSITION_ORDER), 2.7 * len(energies)),
                squeeze=False,
            )
            for row_index, energy in enumerate(energies):
                for column_index, position in enumerate(
                    self.POSITION_ORDER
                ):
                    axis = axes[row_index, column_index]
                    row = group.loc[
                        (group["energy_mev"] == energy)
                        & (group["position_label"] == position)
                    ]
                    if row.empty:
                        axis.axis("off")
                        continue
                    dataset_slug = str(row["dataset_slug"].iloc[0])
                    image_path = (
                        self.output_root
                        / "datasets"
                        / dataset_slug
                        / "figures"
                        / "02b_front_hemisphere_smoothed_map.png"
                    )
                    if image_path.exists():
                        axis.imshow(plt.imread(image_path))
                    else:
                        axis.text(0.5, 0.5, "missing image", ha="center")
                    axis.axis("off")
                    if row_index == 0:
                        axis.set_title(position)
                    if column_index == 0:
                        axis.text(
                            -0.05,
                            0.5,
                            f"{energy:g} MeV",
                            transform=axis.transAxes,
                            rotation=90,
                            va="center",
                            ha="right",
                            fontsize=9,
                        )
            figure.suptitle(
                f"Flat-hemisphere image montage: distance {distance:g} m",
                fontsize=16,
            )
            figure.tight_layout(rect=(0, 0, 1, 0.98))
            path = (
                self.montage_directory
                / f"distance_{distance:g}m_front_maps.png"
            )
            figure.savefig(path, dpi=max(100, self.dpi - 30))
            plt.close(figure)
            paths[
                "montage_distance_" + str(distance).replace(".", "p")
            ] = str(path)
        return paths

    @staticmethod
    def _sort_frame(frame):
        position_rank = {
            value: index
            for index, value in enumerate(
                BatchQualityReporter.POSITION_ORDER
            )
        }
        result = frame.copy()
        result["_position_rank"] = result["position_label"].map(
            position_rank
        )
        result = result.sort_values(
            ["energy_mev", "distance_m", "_position_rank"]
        )
        return result.drop(columns=["_position_rank"]).reset_index(drop=True)

    @staticmethod
    def _write_json(path, value) -> str:
        with Path(path).open("w", encoding="utf-8") as file:
            json.dump(
                value,
                file,
                ensure_ascii=False,
                indent=2,
                allow_nan=False,
            )
        return str(path)
