from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional, Tuple

import matplotlib

# 服务器无显示器，必须在 pyplot 导入前选择离屏 backend。
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .metadata import SimulationMetadata


class DatasetQualityReporter:
    """
    把单组 SOE 数值输出转换为直观图册和可比较质量指标。

    本类只读取重建结果，不参与采样，也不会把模拟真值反馈给算法。
    文件名中的能量和方向仅用于画真值标记及计算误差。
    """

    def __init__(
        self,
        numerical_directory: Path,
        report_directory: Path,
        metadata: Optional[SimulationMetadata] = None,
        analysis_config: Optional[Dict[str, object]] = None,
    ):
        self.numerical_directory = Path(numerical_directory)
        self.report_directory = Path(report_directory)
        self.figure_directory = self.report_directory / "figures"
        self.metadata = metadata
        self.config = analysis_config or {}
        self.dpi = int(self.config.get("figure_dpi", 170))
        self.zoom_deg = float(self.config.get("source_zoom_deg", 45.0))
        self.truth_full_tolerance_mev = float(
            self.config.get("truth_full_tolerance_mev", 0.03)
        )
        self.full_probability_threshold = float(
            self.config.get("full_probability_threshold", 0.5)
        )

    def write_all(self) -> Dict[str, str]:
        self.figure_directory.mkdir(parents=True, exist_ok=True)
        sky = pd.read_csv(self.numerical_directory / "sky_map.csv")
        spectrum = pd.read_csv(
            self.numerical_directory / "spectrum_prior.csv"
        )
        hypotheses = pd.read_csv(
            self.numerical_directory
            / "event_hypothesis_posterior.csv"
        )
        with (
            self.numerical_directory / "run_summary.json"
        ).open("r", encoding="utf-8") as file:
            run_summary = json.load(file)

        expected = (
            self.metadata.expected_direction
            if self.metadata is not None
            else self._weighted_direction(sky)
        )
        metrics = self._calculate_metrics(
            sky,
            hypotheses,
            run_summary,
            expected,
        )
        event_summary = self._event_summary(hypotheses)

        paths = {}
        paths["metadata_json"] = self._write_json(
            "dataset_metadata.json",
            self.metadata.to_dict() if self.metadata else {},
        )
        paths["quality_metrics_json"] = self._write_json(
            "quality_metrics.json",
            metrics,
        )
        event_path = self.report_directory / "event_summary.csv"
        event_summary.to_csv(event_path, index=False)
        paths["event_summary_csv"] = str(event_path)

        paths.update(
            self._write_figures(
                sky=sky,
                spectrum=spectrum,
                hypotheses=hypotheses,
                event_summary=event_summary,
                run_summary=run_summary,
                expected=expected,
                metrics=metrics,
            )
        )
        return paths

    def _calculate_metrics(
        self,
        sky,
        hypotheses,
        run_summary,
        expected,
    ) -> Dict[str, object]:
        weights = sky["posterior_mean_count"].to_numpy(dtype=float)
        vectors = sky[["x", "y", "z"]].to_numpy(dtype=float)
        weighted_vector = np.sum(vectors * weights[:, None], axis=0)
        reconstructed = self._weighted_direction(sky)
        peak = vectors[int(np.argmax(weights))]
        angles = self._angular_distance_deg(vectors, expected)
        radii = self._containment_radii(angles, weights)

        event_summary = self._event_summary(hypotheses)
        input_summary = run_summary.get("input", {})
        total_imaging = int(input_summary.get("imaging_event_count", 0))
        used_imaging = int(
            input_summary.get(
                "imaging_event_count_used",
                total_imaging,
            )
        )
        total_events = int(input_summary.get("event_count", 0))
        generated_events = (
            self.metadata.generated_event_count
            if self.metadata is not None
            else None
        )
        metrics = {
            "dataset_slug": (
                self.metadata.dataset_slug
                if self.metadata is not None
                else self.report_directory.name
            ),
            "energy_mev": (
                self.metadata.energy_mev
                if self.metadata is not None
                else None
            ),
            "distance_m": (
                self.metadata.distance_m
                if self.metadata is not None
                else None
            ),
            "position_label": (
                self.metadata.position_label
                if self.metadata is not None
                else None
            ),
            "expected_direction_x": float(expected[0]),
            "expected_direction_y": float(expected[1]),
            "expected_direction_z": float(expected[2]),
            "centroid_direction_x": float(reconstructed[0]),
            "centroid_direction_y": float(reconstructed[1]),
            "centroid_direction_z": float(reconstructed[2]),
            "peak_direction_x": float(peak[0]),
            "peak_direction_y": float(peak[1]),
            "peak_direction_z": float(peak[2]),
            "centroid_angular_error_deg": self._angle_between_deg(
                reconstructed, expected
            ),
            "peak_angular_error_deg": self._angle_between_deg(
                peak, expected
            ),
            "containment_r50_deg": radii[0.50],
            "containment_r68_deg": radii[0.68],
            "containment_r90_deg": radii[0.90],
            "enhancement_within_10deg": self._regional_enhancement(
                angles, weights, 10.0
            ),
            "enhancement_within_20deg": self._regional_enhancement(
                angles, weights, 20.0
            ),
            "posterior_resultant_length": float(
                np.linalg.norm(weighted_vector)
                / max(weights.sum(), 1e-15)
            ),
            "peak_to_mean_pixel_count": float(
                weights.max() / max(weights.mean(), 1e-15)
            ),
            "generated_event_count": generated_events,
            "positive_deposition_event_count": total_events,
            "total_imaging_event_count": total_imaging,
            "used_imaging_event_count": used_imaging,
            "kernel_count": int(run_summary.get("kernel_count", 0)),
            "kernel_rejected_count": int(
                run_summary.get("kernel_rejected_count", 0)
            ),
            "imaging_fraction_of_all_events": (
                float(total_imaging / total_events)
                if total_events > 0
                else None
            ),
            "imaging_fraction_of_generated_events": (
                float(total_imaging / generated_events)
                if generated_events is not None
                and generated_events > 0
                else None
            ),
            "kernel_survival_fraction_of_used_imaging": (
                float(run_summary.get("kernel_count", 0) / used_imaging)
                if used_imaging > 0
                else None
            ),
            "acceptance_rate": float(
                run_summary.get("acceptance_rate", np.nan)
            ),
            "event_posterior_count": int(len(event_summary)),
        }
        metrics.update(self._energy_metrics(event_summary))
        return self._json_safe(metrics)

    def _energy_metrics(self, event_summary) -> Dict[str, object]:
        if self.metadata is None or event_summary.empty:
            return {}

        truth = float(self.metadata.energy_mev)
        estimates = event_summary["posterior_mean_energy_mev"].to_numpy(
            dtype=float
        )
        residual = estimates - truth
        result = {
            "energy_bias_mev": float(np.mean(residual)),
            "energy_mae_mev": float(np.mean(np.abs(residual))),
            "energy_rmse_mev": float(np.sqrt(np.mean(residual**2))),
            "energy_within_30kev_fraction": float(
                np.mean(np.abs(residual) <= 0.03)
            ),
            "energy_within_60kev_fraction": float(
                np.mean(np.abs(residual) <= 0.06)
            ),
        }
        if "deposited_energy_mev" not in event_summary:
            return result

        two_hit = event_summary.loc[event_summary["n_hits"] == 2].copy()
        if two_hit.empty:
            return result
        truth_full = (
            np.abs(
                two_hit["deposited_energy_mev"].to_numpy(dtype=float)
                - truth
            )
            <= self.truth_full_tolerance_mev
        )
        predicted_full = (
            two_hit["posterior_full_probability"].to_numpy(dtype=float)
            >= self.full_probability_threshold
        )
        true_positive = int(np.sum(truth_full & predicted_full))
        predicted_positive = int(np.sum(predicted_full))
        actual_positive = int(np.sum(truth_full))
        result.update(
            {
                "truth_full_event_fraction": float(np.mean(truth_full)),
                "predicted_full_event_fraction": float(
                    np.mean(predicted_full)
                ),
                "full_classification_precision": (
                    float(true_positive / predicted_positive)
                    if predicted_positive
                    else None
                ),
                "full_classification_recall": (
                    float(true_positive / actual_positive)
                    if actual_positive
                    else None
                ),
            }
        )
        return result

    def _event_summary(self, hypotheses) -> pd.DataFrame:
        rows = []
        for event_index, group in hypotheses.groupby(
            "event_index", sort=False
        ):
            posterior = group[
                "soe_posterior_visit_fraction"
            ].to_numpy(dtype=float)
            total = posterior.sum()
            if total <= 0.0:
                posterior = group[
                    "independent_prior_probability"
                ].to_numpy(dtype=float)
                total = posterior.sum()
            posterior = posterior / max(total, 1e-15)
            energy = group["incident_energy_mev"].to_numpy(dtype=float)
            class_values = group["deposition_class"].astype(str).to_numpy()
            mean_energy = float(np.sum(posterior * energy))
            variance = float(
                np.sum(posterior * (energy - mean_energy) ** 2)
            )
            full_probability = float(
                posterior[class_values == "full"].sum()
            )

            row = {
                "event_index": int(event_index),
                "event_id": str(group["event_id"].iloc[0]),
                "n_hits": int(group["n_hits"].iloc[0]),
                "terminal_channel": str(
                    group["terminal_channel"].iloc[0]
                ),
                "posterior_mean_energy_mev": mean_energy,
                "posterior_sigma_energy_mev": float(np.sqrt(variance)),
                "posterior_full_probability": full_probability,
                "posterior_escape_probability": float(
                    posterior[class_values == "escape"].sum()
                ),
                "posterior_geometry_probability": float(
                    posterior[class_values == "geometry_recovered"].sum()
                ),
            }
            missing_column = "diagnostic_missing_energy_mev"
            if missing_column in group:
                missing = group[missing_column].to_numpy(dtype=float)
                finite = np.isfinite(missing)
                if np.any(finite):
                    deposited = energy[finite] - missing[finite]
                    row["deposited_energy_mev"] = float(
                        np.average(
                            deposited,
                            weights=posterior[finite],
                        )
                    )
            rows.append(row)
        return pd.DataFrame(rows)

    def _write_figures(
        self,
        sky,
        spectrum,
        hypotheses,
        event_summary,
        run_summary,
        expected,
        metrics,
    ) -> Dict[str, str]:
        paths = {}
        paths["all_sky_png"] = self._all_sky_map(
            sky, expected, metrics
        )
        paths["front_hemisphere_png"] = self._front_hemisphere(
            sky, expected, metrics
        )
        paths["source_zoom_png"] = self._source_centered_zoom(
            sky, expected, metrics
        )
        paths["radial_containment_png"] = self._radial_containment(
            sky, expected, metrics
        )
        paths["energy_prior_posterior_png"] = self._energy_plot(
            spectrum, hypotheses
        )
        paths["full_escape_png"] = self._full_escape_plot(event_summary)
        paths["event_energy_png"] = self._event_energy_plot(event_summary)
        paths["uncertainty_map_png"] = self._uncertainty_map(
            sky, expected
        )
        paths["dashboard_png"] = self._dashboard(
            sky,
            spectrum,
            hypotheses,
            event_summary,
            run_summary,
            expected,
            metrics,
        )
        return paths

    def _all_sky_map(self, sky, expected, metrics) -> str:
        path = self.figure_directory / "01_all_sky_mollweide.png"
        figure = plt.figure(figsize=(10.5, 5.8))
        axis = figure.add_subplot(111, projection="mollweide")
        longitude = np.deg2rad(
            sky["longitude_deg"].to_numpy(dtype=float)
        )
        latitude = np.deg2rad(
            sky["latitude_deg"].to_numpy(dtype=float)
        )
        scatter = axis.scatter(
            longitude,
            latitude,
            c=sky["posterior_mean_count"],
            s=12,
            cmap="turbo",
            linewidths=0,
        )
        expected_lon = np.arctan2(expected[1], expected[0])
        expected_lat = np.arcsin(np.clip(expected[2], -1.0, 1.0))
        centroid = np.array(
            [
                metrics["centroid_direction_x"],
                metrics["centroid_direction_y"],
                metrics["centroid_direction_z"],
            ]
        )
        centroid_lon = np.arctan2(centroid[1], centroid[0])
        centroid_lat = np.arcsin(np.clip(centroid[2], -1.0, 1.0))
        axis.scatter(
            [expected_lon],
            [expected_lat],
            marker="*",
            s=180,
            color="white",
            edgecolor="black",
            label="truth",
            zorder=5,
        )
        axis.scatter(
            [centroid_lon],
            [centroid_lat],
            marker="x",
            s=90,
            color="black",
            linewidth=2.0,
            label="posterior centroid",
            zorder=6,
        )
        axis.set_title("All-sky SOE posterior (Mollweide projection)")
        axis.grid(alpha=0.28)
        axis.legend(loc="lower left", fontsize=8)
        plt.colorbar(
            scatter,
            ax=axis,
            orientation="horizontal",
            pad=0.08,
            shrink=0.75,
            label="posterior mean origin count",
        )
        figure.tight_layout()
        figure.savefig(path, dpi=self.dpi)
        plt.close(figure)
        return str(path)

    def _front_hemisphere(self, sky, expected, metrics) -> str:
        path = self.figure_directory / "02_front_hemisphere_flat.png"
        figure, axis = plt.subplots(figsize=(7.4, 6.6))
        self._draw_front_map(axis, sky, expected, metrics)
        figure.tight_layout()
        figure.savefig(path, dpi=self.dpi)
        plt.close(figure)
        return str(path)

    def _draw_front_map(self, axis, sky, expected, metrics):
        front = sky["z"].to_numpy(dtype=float) <= 0.0
        weights = sky["posterior_mean_count"].to_numpy(dtype=float)
        scatter = axis.scatter(
            sky.loc[front, "x"],
            sky.loc[front, "y"],
            c=weights[front],
            s=15,
            cmap="turbo",
            linewidths=0,
        )
        axis.add_patch(
            plt.Circle((0.0, 0.0), 1.0, fill=False, color="black", lw=1.2)
        )
        axis.scatter(
            [expected[0]],
            [expected[1]],
            marker="*",
            s=180,
            color="white",
            edgecolor="black",
            linewidth=1.0,
            label="truth",
            zorder=5,
        )
        axis.scatter(
            [metrics["centroid_direction_x"]],
            [metrics["centroid_direction_y"]],
            marker="x",
            s=90,
            color="black",
            linewidth=2.0,
            label="posterior centroid",
            zorder=6,
        )
        axis.set(
            aspect="equal",
            xlim=(-1.06, 1.06),
            ylim=(-1.06, 1.06),
            xlabel="Detector direction x",
            ylabel="Detector direction y",
            title="Detector-facing hemisphere projected to a flat disk",
        )
        axis.grid(alpha=0.18)
        axis.legend(loc="upper right", fontsize=8)
        plt.colorbar(
            scatter,
            ax=axis,
            shrink=0.82,
            label="posterior mean origin count",
        )

    def _source_centered_zoom(self, sky, expected, metrics) -> str:
        path = self.figure_directory / "03_source_centered_zoom.png"
        figure, axis = plt.subplots(figsize=(7.2, 6.4))
        self._draw_zoom_map(axis, sky, expected, metrics)
        figure.tight_layout()
        figure.savefig(path, dpi=self.dpi)
        plt.close(figure)
        return str(path)

    def _draw_zoom_map(self, axis, sky, expected, metrics):
        vectors = sky[["x", "y", "z"]].to_numpy(dtype=float)
        x_value, y_value, radius = self._azimuthal_coordinates(
            vectors, expected
        )
        mask = radius <= self.zoom_deg
        scatter = axis.scatter(
            x_value[mask],
            y_value[mask],
            c=sky.loc[mask, "posterior_mean_count"],
            s=24,
            cmap="turbo",
            linewidths=0,
        )
        centroid = np.array(
            [
                metrics["centroid_direction_x"],
                metrics["centroid_direction_y"],
                metrics["centroid_direction_z"],
            ]
        )
        cx, cy, _ = self._azimuthal_coordinates(
            centroid.reshape(1, 3), expected
        )
        axis.scatter(
            [0.0],
            [0.0],
            marker="*",
            s=180,
            color="white",
            edgecolor="black",
            label="truth",
            zorder=5,
        )
        axis.scatter(
            cx,
            cy,
            marker="x",
            s=90,
            linewidth=2.0,
            color="black",
            label="posterior centroid",
            zorder=6,
        )
        for radius_deg in (10, 20, 30, 45):
            if radius_deg <= self.zoom_deg:
                axis.add_patch(
                    plt.Circle(
                        (0.0, 0.0),
                        radius_deg,
                        fill=False,
                        color="white",
                        alpha=0.55,
                        lw=0.8,
                    )
                )
                axis.text(
                    radius_deg / np.sqrt(2),
                    radius_deg / np.sqrt(2),
                    str(radius_deg) + "°",
                    fontsize=7,
                    color="black",
                )
        axis.set(
            aspect="equal",
            xlim=(-self.zoom_deg, self.zoom_deg),
            ylim=(-self.zoom_deg, self.zoom_deg),
            xlabel="Angular offset along local horizontal (deg)",
            ylabel="Angular offset along local vertical (deg)",
            title="Source-centered azimuthal projection",
        )
        axis.grid(alpha=0.18)
        axis.legend(loc="upper right", fontsize=8)
        plt.colorbar(
            scatter,
            ax=axis,
            shrink=0.82,
            label="posterior mean origin count",
        )

    def _radial_containment(self, sky, expected, metrics) -> str:
        path = self.figure_directory / "04_radial_containment.png"
        angles = self._angular_distance_deg(
            sky[["x", "y", "z"]].to_numpy(dtype=float),
            expected,
        )
        weights = sky["posterior_mean_count"].to_numpy(dtype=float)
        order = np.argsort(angles)
        cumulative = np.cumsum(weights[order]) / max(weights.sum(), 1e-15)
        uniform = (1.0 - np.cos(np.deg2rad(angles[order]))) / 2.0

        figure, axis = plt.subplots(figsize=(7.4, 4.8))
        axis.plot(angles[order], cumulative, lw=2.0, label="SOE posterior")
        axis.plot(
            angles[order],
            uniform,
            "--",
            color="gray",
            lw=1.2,
            label="uniform-sky reference",
        )
        for level in (50, 68, 90):
            value = metrics["containment_r" + str(level) + "_deg"]
            axis.axvline(
                value,
                alpha=0.6,
                lw=1.0,
                label="R" + str(level) + " = " + f"{value:.1f}°",
            )
        axis.set(
            xlim=(0, 180),
            ylim=(0, 1.01),
            xlabel="Angular distance from true source (deg)",
            ylabel="Cumulative posterior fraction",
            title="Directional containment",
        )
        axis.grid(alpha=0.25)
        axis.legend(fontsize=8)
        figure.tight_layout()
        figure.savefig(path, dpi=self.dpi)
        plt.close(figure)
        return str(path)

    def _energy_plot(self, spectrum, hypotheses) -> str:
        path = self.figure_directory / "05_energy_prior_and_posterior.png"
        aggregate = hypotheses.groupby("incident_energy_mev")[
            "soe_posterior_visit_fraction"
        ].sum()
        aggregate = aggregate / max(aggregate.sum(), 1e-15)

        figure, axis = plt.subplots(figsize=(7.8, 4.8))
        prior = spectrum["prior_probability"].to_numpy(dtype=float)
        prior = prior / max(prior.sum(), 1e-15)
        axis.plot(
            spectrum["incident_energy_mev"],
            prior,
            lw=1.6,
            label="global prior",
        )
        axis.plot(
            aggregate.index,
            aggregate.to_numpy(),
            lw=2.0,
            label="aggregate event posterior",
        )
        if self.metadata is not None:
            axis.axvline(
                self.metadata.energy_mev,
                color="black",
                ls="--",
                lw=1.4,
                label="true energy",
            )
        axis.set(
            xlabel="Incident energy (MeV)",
            ylabel="Normalized probability",
            title="Energy prior versus SOE posterior",
        )
        axis.grid(alpha=0.25)
        axis.legend()
        figure.tight_layout()
        figure.savefig(path, dpi=self.dpi)
        plt.close(figure)
        return str(path)

    def _full_escape_plot(self, events) -> str:
        path = self.figure_directory / "06_full_escape_probability.png"
        figure, axis = plt.subplots(figsize=(7.4, 4.8))
        bins = np.linspace(0.0, 1.0, 21)
        two_hit = events.loc[events["n_hits"] == 2]
        if (
            self.metadata is not None
            and "deposited_energy_mev" in two_hit
        ):
            truth_full = (
                np.abs(
                    two_hit["deposited_energy_mev"]
                    - self.metadata.energy_mev
                )
                <= self.truth_full_tolerance_mev
            )
            axis.hist(
                [
                    two_hit.loc[
                        truth_full, "posterior_full_probability"
                    ],
                    two_hit.loc[
                        ~truth_full, "posterior_full_probability"
                    ],
                ],
                bins=bins,
                stacked=True,
                label=["truth full-like", "truth escaped-like"],
                color=["tab:blue", "tab:orange"],
                alpha=0.85,
            )
        else:
            axis.hist(
                two_hit["posterior_full_probability"],
                bins=bins,
                color="tab:blue",
                alpha=0.85,
            )
        axis.axvline(
            self.full_probability_threshold,
            color="black",
            ls="--",
            label="classification threshold",
        )
        axis.set(
            xlim=(0, 1),
            xlabel="Posterior P(full absorption)",
            ylabel="Event count",
            title="2-hit full/escape ambiguity",
        )
        axis.grid(alpha=0.2)
        axis.legend(fontsize=8)
        figure.tight_layout()
        figure.savefig(path, dpi=self.dpi)
        plt.close(figure)
        return str(path)

    def _event_energy_plot(self, events) -> str:
        path = self.figure_directory / "07_event_energy_reconstruction.png"
        figure, axes = plt.subplots(1, 2, figsize=(11.2, 4.5))
        axes[0].hist(
            events["posterior_mean_energy_mev"],
            bins=35,
            color="tab:purple",
            alpha=0.85,
        )
        if self.metadata is not None:
            axes[0].axvline(
                self.metadata.energy_mev,
                color="black",
                ls="--",
                label="true energy",
            )
        axes[0].set(
            xlabel="Posterior mean incident energy (MeV)",
            ylabel="Event count",
            title="Per-event reconstructed energy",
        )
        axes[0].legend(fontsize=8)
        axes[0].grid(alpha=0.2)

        if "deposited_energy_mev" in events:
            color = events["posterior_full_probability"]
            scatter = axes[1].scatter(
                events["deposited_energy_mev"],
                events["posterior_mean_energy_mev"],
                c=color,
                cmap="viridis",
                s=13,
                alpha=0.75,
            )
            maximum = float(
                max(
                    events["deposited_energy_mev"].max(),
                    events["posterior_mean_energy_mev"].max(),
                )
            )
            axes[1].plot([0, maximum], [0, maximum], "--", color="gray")
            if self.metadata is not None:
                axes[1].axhline(
                    self.metadata.energy_mev,
                    color="black",
                    ls=":",
                )
            axes[1].set(
                xlabel="Observed deposited energy (MeV)",
                ylabel="Posterior mean incident energy (MeV)",
                title="Deposit versus inferred incident energy",
            )
            plt.colorbar(
                scatter,
                ax=axes[1],
                label="posterior P(full)",
            )
        else:
            axes[1].axis("off")
        axes[1].grid(alpha=0.2)
        figure.tight_layout()
        figure.savefig(path, dpi=self.dpi)
        plt.close(figure)
        return str(path)

    def _uncertainty_map(self, sky, expected) -> str:
        path = self.figure_directory / "08_source_zoom_uncertainty.png"
        vectors = sky[["x", "y", "z"]].to_numpy(dtype=float)
        x_value, y_value, radius = self._azimuthal_coordinates(
            vectors, expected
        )
        mask = radius <= self.zoom_deg
        standard_deviation = np.sqrt(
            np.clip(
                sky["posterior_variance"].to_numpy(dtype=float),
                0.0,
                None,
            )
        )
        figure, axis = plt.subplots(figsize=(7.2, 6.4))
        scatter = axis.scatter(
            x_value[mask],
            y_value[mask],
            c=standard_deviation[mask],
            s=24,
            cmap="magma",
            linewidths=0,
        )
        axis.scatter(
            [0.0],
            [0.0],
            marker="*",
            s=180,
            color="white",
            edgecolor="black",
        )
        axis.set(
            aspect="equal",
            xlim=(-self.zoom_deg, self.zoom_deg),
            ylim=(-self.zoom_deg, self.zoom_deg),
            xlabel="Angular offset horizontal (deg)",
            ylabel="Angular offset vertical (deg)",
            title="Posterior uncertainty near the true source",
        )
        axis.grid(alpha=0.18)
        plt.colorbar(
            scatter,
            ax=axis,
            shrink=0.82,
            label="posterior count standard deviation",
        )
        figure.tight_layout()
        figure.savefig(path, dpi=self.dpi)
        plt.close(figure)
        return str(path)

    def _dashboard(
        self,
        sky,
        spectrum,
        hypotheses,
        events,
        run_summary,
        expected,
        metrics,
    ) -> str:
        path = self.figure_directory / "09_dataset_dashboard.png"
        figure = plt.figure(figsize=(15.5, 9.2))
        grid = figure.add_gridspec(2, 3)
        self._draw_front_map(
            figure.add_subplot(grid[0, 0]), sky, expected, metrics
        )
        self._draw_zoom_map(
            figure.add_subplot(grid[0, 1]), sky, expected, metrics
        )

        axis = figure.add_subplot(grid[0, 2])
        aggregate = hypotheses.groupby("incident_energy_mev")[
            "soe_posterior_visit_fraction"
        ].sum()
        aggregate /= max(aggregate.sum(), 1e-15)
        axis.plot(aggregate.index, aggregate.to_numpy(), lw=2)
        if self.metadata is not None:
            axis.axvline(
                self.metadata.energy_mev,
                color="black",
                ls="--",
            )
        axis.set(
            title="Aggregate energy posterior",
            xlabel="Energy (MeV)",
            ylabel="Probability",
        )
        axis.grid(alpha=0.2)

        axis = figure.add_subplot(grid[1, 0])
        angles = self._angular_distance_deg(
            sky[["x", "y", "z"]].to_numpy(dtype=float),
            expected,
        )
        weights = sky["posterior_mean_count"].to_numpy(dtype=float)
        order = np.argsort(angles)
        axis.plot(
            angles[order],
            np.cumsum(weights[order]) / max(weights.sum(), 1e-15),
        )
        axis.set(
            xlim=(0, 90),
            ylim=(0, 1),
            title="Directional containment",
            xlabel="Angular distance (deg)",
            ylabel="Cumulative posterior",
        )
        axis.grid(alpha=0.2)

        axis = figure.add_subplot(grid[1, 1])
        axis.hist(
            events.loc[
                events["n_hits"] == 2,
                "posterior_full_probability",
            ],
            bins=np.linspace(0, 1, 21),
            color="tab:orange",
        )
        axis.set(
            title="Full-absorption posterior",
            xlabel="P(full)",
            ylabel="Events",
        )
        axis.grid(alpha=0.2)

        axis = figure.add_subplot(grid[1, 2])
        axis.axis("off")
        input_summary = run_summary.get("input", {})
        labels = [
            "Dataset: " + str(metrics["dataset_slug"]),
            "Centroid error: "
            + f"{metrics['centroid_angular_error_deg']:.2f} deg",
            "Peak error: "
            + f"{metrics['peak_angular_error_deg']:.2f} deg",
            "R68: " + f"{metrics['containment_r68_deg']:.2f} deg",
            "Resultant concentration: "
            + f"{metrics['posterior_resultant_length']:.3f}",
            "Enhancement <10 deg: "
            + f"{metrics['enhancement_within_10deg']:.2f} x uniform",
            "Positive-deposition events: "
            + f"{int(input_summary.get('event_count', 0)):,}",
            "Imaging events (all): "
            + f"{int(input_summary.get('imaging_event_count', 0)):,}",
            "Imaging events (used): "
            + f"{int(input_summary.get('imaging_event_count_used', input_summary.get('imaging_event_count', 0))):,}",
            "Valid kernels: "
            + f"{int(run_summary.get('kernel_count', 0)):,}",
            "SOE acceptance: "
            + f"{float(run_summary.get('acceptance_rate', 0.0)):.3f}",
        ]
        if self.metadata is not None and (
            self.metadata.generated_event_count is not None
        ):
            labels.insert(
                5,
                "Generated events: "
                + f"{self.metadata.generated_event_count:,}",
            )
        if metrics.get("energy_mae_mev") is not None:
            labels.insert(
                4,
                "Energy MAE: "
                + f"{1000.0 * metrics['energy_mae_mev']:.1f} keV",
            )
        axis.text(
            0.03,
            0.97,
            "\n".join(labels),
            va="top",
            ha="left",
            fontsize=12,
            linespacing=1.55,
            family="monospace",
        )
        figure.suptitle(
            "SOE1 single-dataset imaging report",
            fontsize=16,
        )
        figure.tight_layout(rect=(0, 0, 1, 0.97))
        figure.savefig(path, dpi=self.dpi)
        plt.close(figure)
        return str(path)

    @staticmethod
    def _weighted_direction(sky) -> np.ndarray:
        vectors = sky[["x", "y", "z"]].to_numpy(dtype=float)
        weights = sky["posterior_mean_count"].to_numpy(dtype=float)
        vector = np.sum(vectors * weights[:, None], axis=0)
        norm = np.linalg.norm(vector)
        if norm <= 1e-15:
            return vectors[int(np.argmax(weights))]
        return vector / norm

    @staticmethod
    def _angle_between_deg(first, second) -> float:
        return float(
            np.rad2deg(
                np.arccos(
                    np.clip(
                        np.dot(first, second)
                        / (np.linalg.norm(first) * np.linalg.norm(second)),
                        -1.0,
                        1.0,
                    )
                )
            )
        )

    @staticmethod
    def _angular_distance_deg(vectors, reference) -> np.ndarray:
        return np.rad2deg(
            np.arccos(
                np.clip(
                    np.asarray(vectors, dtype=float)
                    @ np.asarray(reference, dtype=float),
                    -1.0,
                    1.0,
                )
            )
        )

    @staticmethod
    def _containment_radii(angles, weights):
        order = np.argsort(angles)
        ordered_angles = angles[order]
        cumulative = np.cumsum(weights[order])
        cumulative /= max(cumulative[-1], 1e-15)
        return {
            level: float(
                ordered_angles[
                    min(
                        np.searchsorted(cumulative, level),
                        len(ordered_angles) - 1,
                    )
                ]
            )
            for level in (0.50, 0.68, 0.90)
        }

    @staticmethod
    def _regional_enhancement(angles, weights, radius_deg) -> float:
        observed = float(weights[angles <= radius_deg].sum())
        observed /= max(float(weights.sum()), 1e-15)
        uniform = (1.0 - np.cos(np.deg2rad(radius_deg))) / 2.0
        return float(observed / max(uniform, 1e-15))

    @staticmethod
    def _azimuthal_coordinates(
        vectors,
        center,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        center = np.asarray(center, dtype=float)
        center /= np.linalg.norm(center)
        vertical_hint = (
            np.array([0.0, 1.0, 0.0])
            if abs(center[1]) < 0.9
            else np.array([1.0, 0.0, 0.0])
        )
        horizontal = np.cross(center, vertical_hint)
        horizontal /= np.linalg.norm(horizontal)
        vertical = np.cross(horizontal, center)
        vertical /= np.linalg.norm(vertical)

        vectors = np.asarray(vectors, dtype=float)
        angle = np.arccos(
            np.clip(vectors @ center, -1.0, 1.0)
        )
        sine = np.sin(angle)
        scale = np.divide(
            np.rad2deg(angle),
            sine,
            out=np.zeros_like(angle),
            where=np.abs(sine) > 1e-12,
        )
        x_value = scale * (vectors @ horizontal)
        y_value = scale * (vectors @ vertical)
        return x_value, y_value, np.rad2deg(angle)

    def _write_json(self, name, value) -> str:
        path = self.report_directory / name
        with path.open("w", encoding="utf-8") as file:
            json.dump(value, file, ensure_ascii=False, indent=2)
        return str(path)

    @classmethod
    def _json_safe(cls, value):
        if isinstance(value, dict):
            return {
                str(key): cls._json_safe(item)
                for key, item in value.items()
            }
        if isinstance(value, (np.integer,)):
            return int(value)
        if isinstance(value, (np.floating, float)):
            numeric = float(value)
            return numeric if np.isfinite(numeric) else None
        return value
