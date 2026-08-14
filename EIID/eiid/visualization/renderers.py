"""无交互后端的 skymap、能谱、联合分布和收敛图输出。"""

from __future__ import annotations

from pathlib import Path
from typing import Mapping, Sequence

import numpy as np


class SphericalMapSmoother:
    """对等面积像素中心执行分块球面高斯平滑，并保持总强度。"""

    @staticmethod
    def smooth(
        values,
        directions,
        sigma_rad: float,
        chunk_size: int = 256,
        maximum_pixel_count: int = 4096,
    ):
        sky = np.asarray(values, dtype=float).reshape(-1)
        vectors = np.asarray(directions, dtype=float)
        sigma = float(sigma_rad)
        if vectors.shape != (sky.size, 3):
            raise ValueError("天空值和像素中心方向数量不一致。")
        if sky.size > int(maximum_pixel_count):
            raise MemoryError(
                "纯 NumPy 球面平滑像素数超过配置上限；"
                "请降低 nside、提高显式上限或接入 healpy 加速。"
            )
        if sigma <= 0.0 or not np.isfinite(sigma):
            raise ValueError("球面平滑 sigma 必须是正有限数。")
        result = np.empty_like(sky)
        for start in range(0, sky.size, int(chunk_size)):
            stop = min(sky.size, start + int(chunk_size))
            cosine = np.clip(vectors[start:stop] @ vectors.T, -1.0, 1.0)
            angle = np.arccos(cosine)
            weights = np.exp(-0.5 * (angle / sigma) ** 2)
            denominator = np.sum(weights, axis=1)
            result[start:stop] = (weights @ sky) / denominator
        original_total = float(np.sum(sky))
        smoothed_total = float(np.sum(result))
        if smoothed_total > 0.0:
            result *= original_total / smoothed_total
        return result


class CameraProjection:
    """以配置的相机正前方和显示向上方向建立展示坐标。"""

    def __init__(self, boresight, display_up):
        front = np.asarray(boresight, dtype=float)
        up_reference = np.asarray(display_up, dtype=float)
        front /= np.linalg.norm(front)
        up_reference /= np.linalg.norm(up_reference)
        right = np.cross(front, up_reference)
        right_norm = float(np.linalg.norm(right))
        if right_norm <= 1e-8:
            raise ValueError("display_up 不能与 boresight 平行。")
        right /= right_norm
        up = np.cross(right, front)
        up /= np.linalg.norm(up)
        self.front = front
        self.right = right
        self.up = up

    def full_sky_raster(self, sky_grid, sky_values, width: int, height: int):
        """生成相机正前方位于中心的等经纬填充栅格。"""

        longitudes = np.linspace(-np.pi, np.pi, int(width), endpoint=False)
        latitudes = np.linspace(-0.5 * np.pi, 0.5 * np.pi, int(height))
        longitude, latitude = np.meshgrid(longitudes, latitudes)
        cosine_latitude = np.cos(latitude)
        directions = (
            cosine_latitude[..., np.newaxis]
            * np.cos(longitude)[..., np.newaxis]
            * self.front
            + cosine_latitude[..., np.newaxis]
            * np.sin(longitude)[..., np.newaxis]
            * self.right
            + np.sin(latitude)[..., np.newaxis] * self.up
        )
        pixels = sky_grid.directions_to_pixels(directions)
        return np.asarray(sky_values, dtype=float)[pixels]

    def front_orthographic_raster(
        self, sky_grid, sky_values, width: int, height: int
    ):
        """生成以相机正前方为中心的正交投影，圆外使用 NaN。"""

        horizontal = np.linspace(-1.0, 1.0, int(width))
        vertical = np.linspace(-1.0, 1.0, int(height))
        x, y = np.meshgrid(horizontal, vertical)
        radius_squared = x * x + y * y
        inside = radius_squared <= 1.0
        forward = np.sqrt(np.maximum(0.0, 1.0 - radius_squared))
        directions = (
            forward[..., np.newaxis] * self.front
            + x[..., np.newaxis] * self.right
            + y[..., np.newaxis] * self.up
        )
        raster = np.full(x.shape, np.nan, dtype=float)
        pixels = sky_grid.directions_to_pixels(directions[inside])
        raster[inside] = np.asarray(sky_values, dtype=float)[pixels]
        return raster


class EiidFigureSuite:
    """生成阶段 5 规定的七类 PNG，所有文件名来自配置。"""

    _DIRECTORIES = {
        "full_sky_raw": "skymap",
        "front_raw": "skymap",
        "front_smoothed": "skymap",
        "energy_spectrum": "spectra",
        "joint_distribution": "joint_energy_sky",
        "convergence": "convergence",
        "dashboard": "diagnostics",
        "front_centered": "skymap",
        "planar_projection": "projections",
        "source_zoom": "projections",
        "energy_band_skymaps": "skymap",
        "iteration_snapshots": "convergence",
        "event_diagnostics": "diagnostics",
    }

    def __init__(
        self,
        figure_root,
        visualization_config,
        boresight,
        physical_use_allowed: bool = False,
        response_label: str = "prototype",
    ):
        self.figure_root = Path(figure_root).resolve()
        self.config = visualization_config
        self.physical_use_allowed = bool(physical_use_allowed)
        self.response_label = str(response_label)
        self.title_prefix = "" if self.physical_use_allowed else "PROTOTYPE "
        self.projection = CameraProjection(
            boresight, visualization_config.display_up_direction
        )

    @staticmethod
    def _pyplot():
        try:
            import matplotlib

            matplotlib.use("Agg", force=True)
            import matplotlib.pyplot as plt
        except ImportError as error:
            raise ImportError(
                "生成阶段 5 图片需要 matplotlib；请安装项目 science 依赖。"
            ) from error
        return plt

    def _path(self, key: str) -> Path:
        directory = self.figure_root / self._DIRECTORIES[key]
        directory.mkdir(parents=True, exist_ok=True)
        return directory / self.config.file_names[key]

    def _save(self, figure, key: str) -> Path:
        path = self._path(key)
        figure.savefig(path, dpi=self.config.dpi, bbox_inches="tight")
        self._pyplot().close(figure)
        return path

    @staticmethod
    def _image_panel(axes, raster, title, extent=None):
        image = axes.imshow(
            raster,
            origin="lower",
            interpolation="nearest",
            aspect="auto" if extent is not None else "equal",
            extent=extent,
            cmap="inferno",
        )
        axes.set_title(title)
        return image

    def render(
        self,
        joint_image,
        energy_grid,
        sky_grid,
        telemetry: Sequence,
        energy_standard_error=None,
        event_responses=None,
    ) -> Mapping[str, str]:
        plt = self._pyplot()
        joint = np.asarray(joint_image, dtype=float).reshape(
            sky_grid.pixel_count, energy_grid.bin_count
        )
        raw_sky = np.sum(joint, axis=1)
        directions = sky_grid.all_pixel_directions()
        smoothed_sky = SphericalMapSmoother.smooth(
            raw_sky,
            directions,
            np.deg2rad(self.config.smoothing_sigma_deg),
            chunk_size=self.config.smoothing_chunk_size,
            maximum_pixel_count=(
                self.config.maximum_numpy_smoothing_pixels
            ),
        )
        full_raw = self.projection.full_sky_raster(
            sky_grid,
            raw_sky,
            self.config.raster_width,
            self.config.raster_height,
        )
        front_width = self.config.raster_height
        front_raw = self.projection.front_orthographic_raster(
            sky_grid,
            raw_sky,
            front_width,
            self.config.raster_height,
        )
        front_smoothed = self.projection.front_orthographic_raster(
            sky_grid,
            smoothed_sky,
            front_width,
            self.config.raster_height,
        )
        outputs = {}

        figure, axes = plt.subplots(figsize=(12, 5))
        image = self._image_panel(
            axes,
            full_raw,
            self.title_prefix + "raw full-sky HEALPix map (camera front at center)",
            extent=(-180.0, 180.0, -90.0, 90.0),
        )
        axes.set_xlabel("camera-centered longitude [deg]")
        axes.set_ylabel("camera-centered latitude [deg]")
        figure.colorbar(image, ax=axes, label="reconstructed intensity")
        outputs["full_sky_raw"] = str(self._save(figure, "full_sky_raw"))

        full_smoothed = self.projection.full_sky_raster(
            sky_grid,
            smoothed_sky,
            self.config.raster_width,
            self.config.raster_height,
        )
        figure, axes = plt.subplots(figsize=(12, 5))
        image = self._image_panel(
            axes,
            full_smoothed,
            self.title_prefix + "camera-centered planar projection",
            extent=(-180.0, 180.0, -90.0, 90.0),
        )
        axes.set_xlabel("camera-centered longitude [deg]")
        axes.set_ylabel("camera-centered latitude [deg]")
        figure.colorbar(image, ax=axes, label="reconstructed intensity")
        outputs["planar_projection"] = str(self._save(figure, "planar_projection"))

        for key, raster, title in (
            ("front_raw", front_raw, self.title_prefix + "camera-front raw map"),
            (
                "front_smoothed",
                front_smoothed,
                self.title_prefix + "camera-front smoothed map",
            ),
        ):
            figure, axes = plt.subplots(figsize=(6, 6))
            image = self._image_panel(axes, raster, title, extent=(-1, 1, -1, 1))
            axes.set_xlabel("camera right (orthographic)")
            axes.set_ylabel("camera up (orthographic)")
            figure.colorbar(image, ax=axes, label="reconstructed intensity")
            outputs[key] = str(self._save(figure, key))

        figure, axes = plt.subplots(figsize=(7, 7))
        image = self._image_panel(
            axes,
            front_smoothed,
            self.title_prefix + "camera-front centered display",
            extent=(-1, 1, -1, 1),
        )
        axes.axhline(0.0, color="white", linewidth=0.5, alpha=0.7)
        axes.axvline(0.0, color="white", linewidth=0.5, alpha=0.7)
        axes.set_xlabel("camera right")
        axes.set_ylabel("camera up")
        figure.colorbar(image, ax=axes, label="reconstructed intensity")
        outputs["front_centered"] = str(self._save(figure, "front_centered"))

        zoom_radius = 0.45
        height, width = front_smoothed.shape
        x0, x1 = int(width * (0.5 - zoom_radius / 2)), int(width * (0.5 + zoom_radius / 2))
        y0, y1 = int(height * (0.5 - zoom_radius / 2)), int(height * (0.5 + zoom_radius / 2))
        figure, axes = plt.subplots(figsize=(7, 6))
        image = self._image_panel(
            axes,
            front_smoothed[y0:y1, x0:x1],
            self.title_prefix + "camera-front central zoom",
            extent=(-zoom_radius, zoom_radius, -zoom_radius, zoom_radius),
        )
        axes.set_xlabel("camera right")
        axes.set_ylabel("camera up")
        figure.colorbar(image, ax=axes, label="reconstructed intensity")
        outputs["source_zoom"] = str(self._save(figure, "source_zoom"))

        spectrum = np.sum(joint, axis=0)
        figure, axes = plt.subplots(figsize=(9, 5))
        axes.stairs(spectrum, energy_grid.edges_mev, fill=True, alpha=0.5)
        if energy_standard_error is not None:
            error = np.asarray(energy_standard_error, dtype=float)
            centers = energy_grid.centers_mev
            finite = np.isfinite(error)
            axes.fill_between(
                centers[finite],
                np.maximum(0.0, spectrum[finite] - error[finite]),
                spectrum[finite] + error[finite],
                alpha=0.25,
                step="mid",
                label="diagonal Fisher approximation",
            )
            axes.legend()
        axes.set_xlabel("incident energy [MeV]")
        axes.set_ylabel("reconstructed intensity")
        axes.set_title(self.title_prefix + "reconstructed energy spectrum")
        axes.grid(alpha=0.25)
        outputs["energy_spectrum"] = str(
            self._save(figure, "energy_spectrum")
        )

        figure, axes = plt.subplots(figsize=(11, 6))
        image = axes.imshow(
            joint.T,
            origin="lower",
            aspect="auto",
            interpolation="nearest",
            extent=(
                0,
                sky_grid.pixel_count,
                energy_grid.edges_mev[0],
                energy_grid.edges_mev[-1],
            ),
            cmap="viridis",
        )
        axes.set_xlabel("HEALPix RING pixel index")
        axes.set_ylabel("incident energy [MeV]")
        axes.set_title(self.title_prefix + "joint direction-energy distribution")
        figure.colorbar(image, ax=axes, label="reconstructed intensity")
        outputs["joint_distribution"] = str(
            self._save(figure, "joint_distribution")
        )

        bands = tuple(self.config.energy_bands_mev)
        columns = 2
        rows = int(np.ceil(len(bands) / columns))
        figure, axes = plt.subplots(rows, columns, figsize=(12, 5 * rows), squeeze=False)
        for axis, (lower, upper) in zip(axes.reshape(-1), bands):
            mask = (energy_grid.centers_mev >= lower) & (energy_grid.centers_mev < upper + 1e-12)
            band_sky = np.sum(joint[:, mask], axis=1)
            raster = self.projection.front_orthographic_raster(
                sky_grid, band_sky, front_width, self.config.raster_height
            )
            image = self._image_panel(
                axis, raster, "{:.3g}--{:.3g} MeV".format(lower, upper), extent=(-1, 1, -1, 1)
            )
            figure.colorbar(image, ax=axis, fraction=0.046)
        for axis in axes.reshape(-1)[len(bands):]:
            axis.axis("off")
        figure.suptitle(self.title_prefix + "energy-band camera-front skymaps")
        outputs["energy_band_skymaps"] = str(self._save(figure, "energy_band_skymaps"))

        iterations = np.asarray([item.iteration for item in telemetry])
        likelihood = np.asarray([item.log_likelihood for item in telemetry])
        image_change = np.asarray([item.l1_relative_change for item in telemetry])
        spectrum_change = np.asarray(
            [item.energy_marginal_l1_change for item in telemetry]
        )
        figure, axes = plt.subplots(1, 3, figsize=(15, 4))
        axes[0].plot(iterations, likelihood)
        axes[0].set_title("Poisson log-likelihood")
        axes[1].semilogy(iterations[1:], np.maximum(image_change[1:], 1e-16))
        axes[1].set_title("joint image L1 change")
        axes[2].semilogy(
            iterations[1:], np.maximum(spectrum_change[1:], 1e-16)
        )
        axes[2].set_title("energy spectrum L1 change")
        for axis in axes:
            axis.set_xlabel("iteration")
            axis.grid(alpha=0.25)
        outputs["convergence"] = str(self._save(figure, "convergence"))

        checkpoint_paths = sorted((self.figure_root.parent / "checkpoints").glob("iteration_*.npz"))
        selected_checkpoints = checkpoint_paths
        if len(selected_checkpoints) > 6:
            positions = np.linspace(0, len(selected_checkpoints) - 1, 6).astype(int)
            selected_checkpoints = [selected_checkpoints[index] for index in positions]
        figure, axes = plt.subplots(2, 3, figsize=(15, 10), squeeze=False)
        for axis, checkpoint in zip(axes.reshape(-1), selected_checkpoints):
            with np.load(str(checkpoint), allow_pickle=False) as loaded:
                checkpoint_sky = np.asarray(loaded["sky_marginal"], dtype=float)
                iteration_value = int(np.asarray(loaded["iteration"]).reshape(-1)[0])
            raster = self.projection.front_orthographic_raster(
                sky_grid, checkpoint_sky, front_width, self.config.raster_height
            )
            self._image_panel(axis, raster, "iteration {}".format(iteration_value), extent=(-1, 1, -1, 1))
        for axis in axes.reshape(-1)[len(selected_checkpoints):]:
            axis.axis("off")
        figure.suptitle(self.title_prefix + "representative iteration snapshots")
        outputs["iteration_snapshots"] = str(self._save(figure, "iteration_snapshots"))

        responses = tuple(event_responses or ())
        counts = np.asarray([item.nonzero_count for item in responses], dtype=float)
        supported = int(np.sum(counts > 0)) if counts.size else 0
        unsupported = int(np.sum(counts == 0)) if counts.size else 0
        figure, axes = plt.subplots(1, 2, figsize=(12, 4))
        if counts.size:
            axes[0].hist(counts, bins=min(30, max(5, counts.size)))
        axes[0].set_title("event sparse-kernel cell count")
        axes[0].set_xlabel("nonzero joint cells")
        axes[1].bar(("supported", "unsupported"), (supported, unsupported))
        axes[1].set_title("event response support")
        figure.suptitle(self.title_prefix + "event-response diagnostics")
        outputs["event_diagnostics"] = str(self._save(figure, "event_diagnostics"))

        figure, axes = plt.subplots(2, 3, figsize=(16, 9))
        first = self._image_panel(
            axes[0, 0], front_raw, "raw camera-front", extent=(-1, 1, -1, 1)
        )
        figure.colorbar(first, ax=axes[0, 0], fraction=0.046)
        second = self._image_panel(
            axes[0, 1],
            front_smoothed,
            "smoothed camera-front",
            extent=(-1, 1, -1, 1),
        )
        figure.colorbar(second, ax=axes[0, 1], fraction=0.046)
        axes[0, 2].stairs(spectrum, energy_grid.edges_mev, fill=True)
        axes[0, 2].set_title("energy spectrum")
        joint_panel = axes[1, 0].imshow(
            joint.T, origin="lower", aspect="auto", interpolation="nearest"
        )
        axes[1, 0].set_title("direction-energy joint map")
        figure.colorbar(joint_panel, ax=axes[1, 0], fraction=0.046)
        axes[1, 1].plot(iterations, likelihood)
        axes[1, 1].set_title("log-likelihood")
        axes[1, 2].axis("off")
        axes[1, 2].text(
            0.02,
            0.95,
            ("VALIDATED PHYSICAL\n" if self.physical_use_allowed else "PROTOTYPE\n")
            + "response: " + self.response_label + "\n"
            + "physical use allowed: " + ("YES" if self.physical_use_allowed else "NO") + "\n"
            "camera front is centered in skymaps",
            va="top",
            family="monospace",
        )
        figure.suptitle("EIID reconstruction dashboard")
        outputs["dashboard"] = str(self._save(figure, "dashboard"))
        return outputs
