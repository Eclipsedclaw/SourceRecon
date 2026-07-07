
import os
import time
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
import matplotlib.colors as mcolors
import matplotlib.patches as mpatches
from scipy.optimize import curve_fit


class DataPlotter:
    """
    面向对象版画图类。

    输入:
        final_df: 已经由 DataPreProcessor 得到的大表。
                  至少应包含:
                  EventID,
                  ch0_x/ch0_y/ch0_z/ch0_energy,
                  ch1_x/ch1_y/ch1_z/ch1_energy,
                  ch2_x/ch2_y/ch2_z/ch2_energy

    设计原则:
        1. 本类只画图、做重建相关计算，不负责读取 txt/csv。
        2. 每个方法对应师兄 notebook 中的一类图。
        3. 每个画图方法都返回 fig/ax，方便保存、调试、二次修改。
    """

    def __init__(
        self,
        final_df,
        save_dir=None,
        channels=("ch0", "ch1", "ch2"),
        m_e=0.511,
    ):
        self.final_df = final_df
        self.channels = list(channels)
        self.m_e = m_e

        if save_dir is None:
            self.save_dir = None
        else:
            self.save_dir = Path(save_dir)
            self.save_dir.mkdir(parents=True, exist_ok=True)

    # ============================================================
    # 通用小工具
    # ============================================================

    @staticmethod
    def _gauss(x, a, mu, sigma):
        """高斯函数。"""
        return a * np.exp(-((x - mu) ** 2) / (2 * sigma**2))

    def _save(self, fig, filename):
        """如果设置了 save_dir，就保存图片。"""
        if self.save_dir is not None and filename is not None:
            fig.savefig(self.save_dir / filename, dpi=300, bbox_inches="tight")

    @staticmethod
    def _finish(fig, show=True):
        """统一控制 tight_layout 和 show。"""
        fig.tight_layout()
        if show:
            plt.show()

    def _get_valid_energy(self, channel):
        """
        提取某个 channel 的有效能量数据。

        去掉:
            1. NaN
            2. 小于等于 0 的能量
        """
        energy_col = f"{channel}_energy"

        if energy_col not in self.final_df.columns:
            raise KeyError(f"final_df 里没有这一列: {energy_col}")

        energy = self.final_df[energy_col].dropna()
        energy = energy[energy > 0]
        return energy

    def _get_energy_series_filled(self):
        """返回填充 NaN 为 0 后的 ch0/ch1/ch2 能量 Series。"""
        e0 = self.final_df["ch0_energy"].fillna(0)
        e1 = self.final_df["ch1_energy"].fillna(0)
        e2 = self.final_df["ch2_energy"].fillna(0)
        return e0, e1, e2

    def _plot_hist_with_optional_gaussian_fit(
        self,
        ax,
        data,
        title,
        color="#1f77b4",
        plot_min=0.0,
        plot_max=1.0,
        n_bins=200,
        fit=True,
        fit_min=0.60,
        fit_max=0.72,
        initial_mu=0.662,
        initial_sigma=0.02,
        legend_loc="upper right",
        resolution_use_fwhm=True,
    ):
        """
        画一维能谱，并可选择在指定区间做高斯拟合。

        注意:
            原 notebook 中“单通道能谱”的高斯拟合代码被注释掉了。
            这里把它做成参数 fit=True/False，方便你自由开关。
        """
        data = pd.Series(data).dropna()
        data = data[data > 0]
        total_events = len(data)

        counts, bin_edges, _ = ax.hist(
            data,
            bins=n_bins,
            range=(plot_min, plot_max),
            color=color,
            alpha=0.8,
            histtype="step",
            linewidth=1.5,
            label=f"Total Events: {total_events}",
        )

        if fit:
            bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
            mask = (bin_centers >= fit_min) & (bin_centers <= fit_max)
            x_fit = bin_centers[mask]
            y_fit = counts[mask]

            if len(x_fit) > 0 and np.max(y_fit) > 0:
                p0 = [np.max(y_fit), initial_mu, initial_sigma]
                try:
                    popt, _ = curve_fit(self._gauss, x_fit, y_fit, p0=p0)
                    _, mu_opt, sigma_opt = popt
                    sigma_opt = abs(sigma_opt)

                    # 师兄 cell 2 用 FWHM/mu，cell 3 用 sigma/mu。
                    # 这里默认采用更常见的 FWHM/mu，也可以关掉。
                    if resolution_use_fwhm:
                        fwhm = 2.355 * sigma_opt
                        resolution = fwhm / mu_opt * 100
                    else:
                        resolution = sigma_opt / mu_opt * 100

                    x_plot = np.linspace(fit_min, fit_max, 200)
                    y_plot = self._gauss(x_plot, *popt)

                    fit_label = (
                        "Fit (0.662 MeV):\n"
                        f"$\\mu$ = {mu_opt:.4f} MeV\n"
                        f"$\\sigma$ = {sigma_opt:.4f} MeV\n"
                        f"Res = {resolution:.2f}%"
                    )

                    ax.plot(
                        x_plot,
                        y_plot,
                        "k--",
                        linewidth=2,
                        label=fit_label,
                    )

                except Exception as e:
                    print(f"{title} 高斯拟合失败: {e}")

        ax.set_title(title)
        ax.set_xlabel("Energy (MeV)")
        ax.set_ylabel("Counts")
        ax.set_xlim(plot_min, plot_max)
        ax.legend(loc=legend_loc, framealpha=0.9)
        ax.grid(True, linestyle="--", alpha=0.5)

        return counts, bin_edges

    def _iter_hits(self, row):
        """
        从 final_df 的一行中提取有效 hit。

        返回:
            [(x, y, z, energy, channel), ...]
        """
        hits = []
        for ch in self.channels:
            e_col = f"{ch}_energy"
            if not hasattr(row, e_col):
                continue

            e_val = getattr(row, e_col)
            if pd.notna(e_val) and e_val > 0:
                x = getattr(row, f"{ch}_x")
                y = getattr(row, f"{ch}_y")
                z = getattr(row, f"{ch}_z")
                hits.append((x, y, z, e_val, ch))

        return hits

    def _extract_two_hit_compton_events(
        self,
        energy_window=(0.64, 0.68),
        require_no_ch0=False,
    ):
        """
        提取两次击中的康普顿事件。

        返回:
            r1_positions: 第一次相互作用位置数组
            axes: 从第二次击中点指向第一次击中点的轴向量
            angles: 由能量公式反推出的散射角，单位 rad
        """
        r1_positions = []
        axes = []
        angles = []

        total_processed = 0
        energy_rejected = 0

        for row in self.final_df.itertuples(index=False):
            hits = self._iter_hits(row)

            if len(hits) < 2:
                continue

            total_processed += 1
            e_total = sum(h[3] for h in hits)

            if not (energy_window[0] <= e_total <= energy_window[1]):
                energy_rejected += 1
                continue

            # 假设源在 +Z 方向，所以光子先打到 Z 更大的层。
            hits.sort(key=lambda item: item[2], reverse=True)

            # 和师兄 notebook 中 ARM / MLEM 的版本保持一致: 只要两次击中。
            if len(hits) != 2:
                continue

            if require_no_ch0:
                ch0_e = getattr(row, "ch0_energy")
                if pd.notna(ch0_e) and ch0_e > 0:
                    continue

            p1 = hits[0]
            p2 = hits[1]

            pos1 = np.array([p1[0], p1[1], p1[2]], dtype=float)
            pos2 = np.array([p2[0], p2[1], p2[2]], dtype=float)

            e2_total = p2[3]

            vec = pos1 - pos2
            norm = np.linalg.norm(vec)
            if norm == 0:
                continue

            axis = vec / norm
            cos_theta = 1 - self.m_e * (1 / e2_total - 1 / e_total)

            if -1 <= cos_theta <= 1:
                r1_positions.append(pos1)
                axes.append(axis)
                angles.append(np.arccos(cos_theta))

        print(f"处理的双/三击中事件总数: {total_processed}")
        print(f"因未落在全能峰 {energy_window} MeV 被剔除的事件: {energy_rejected}")
        print(f"有效物理事件总数: {len(axes)}")

        return (
            np.asarray(r1_positions, dtype=float),
            np.asarray(axes, dtype=float),
            np.asarray(angles, dtype=float),
        )

    # ============================================================
    # 1. 单通道能谱，对应 notebook cell 2
    # ============================================================

    def plot_single_channel_spectra(
        self,
        plot_min=0.0,
        plot_max=1.0,
        n_bins=200,
        fit=True,
        fit_min=0.60,
        fit_max=0.72,
        show=True,
        filename="single_channel_spectra.png",
    ):
        """
        画 ch0/ch1/ch2 三个通道各自的能谱。

        和你当前版本相比:
            1. 保留原 notebook 的颜色。
            2. 加回可选高斯拟合曲线。
        """
        colors = ["#1f77b4", "#ff7f0e", "#2ca02c"]

        fig, axes = plt.subplots(1, 3, figsize=(18, 5))

        for i, ch in enumerate(self.channels):
            energy = self._get_valid_energy(ch)
            self._plot_hist_with_optional_gaussian_fit(
                axes[i],
                energy,
                title=f"{ch.upper()} Energy Spectrum",
                color=colors[i],
                plot_min=plot_min,
                plot_max=plot_max,
                n_bins=n_bins,
                fit=fit,
                fit_min=fit_min,
                fit_max=fit_max,
                legend_loc="upper right",
                resolution_use_fwhm=True,
            )

        self._finish(fig, show=show)
        self._save(fig, filename)
        return fig, axes

    # ============================================================
    # 2. 加和能谱 + CH1/CH2 二维图，对应 notebook cell 3 第一张图
    # ============================================================

    def plot_sum_energy_and_ch1_ch2_2d(
        self,
        plot_min=0.0,
        plot_max=1.5,
        n_bins=200,
        fit=True,
        fit_min=0.60,
        fit_max=0.78,
        show=True,
        filename="sum_energy_and_ch1_ch2_2d.png",
    ):
        """
        画:
            1. ch0 + ch1 + ch2 加和能谱
            2. ch1 + ch2 加和能谱
            3. ch1 vs ch2 二维直方图

        这是 notebook cell 3 的第一张 1x3 图。
        """
        e0, e1, e2 = self._get_energy_series_filled()

        mask_all3 = (e0 > 0) & (e1 > 0) & (e2 > 0)
        mask_12 = (e1 > 0) & (e2 > 0)

        e_sum_all3 = (e0 + e1 + e2)[mask_all3]
        e_sum_12 = (e1 + e2)[mask_12]
        e_ch1_2d = e1[mask_12]
        e_ch2_2d = e2[mask_12]

        fig, axes = plt.subplots(1, 3, figsize=(18, 5))

        self._plot_hist_with_optional_gaussian_fit(
            axes[0],
            e_sum_all3,
            title="Sum Energy (CH0 > 0)",
            color="#d62728",
            plot_min=plot_min,
            plot_max=plot_max,
            n_bins=n_bins,
            fit=fit,
            fit_min=fit_min,
            fit_max=fit_max,
            legend_loc="upper left",
            resolution_use_fwhm=False,
        )

        self._plot_hist_with_optional_gaussian_fit(
            axes[1],
            e_sum_12,
            title="Sum Energy (CH0 > 0)",
            color="#9467bd",
            plot_min=plot_min,
            plot_max=plot_max,
            n_bins=n_bins,
            fit=fit,
            fit_min=fit_min,
            fit_max=fit_max,
            legend_loc="upper left",
            resolution_use_fwhm=False,
        )

        _, _, _, image = axes[2].hist2d(
            e_ch1_2d,
            e_ch2_2d,
            bins=150,
            range=[[plot_min, plot_max], [plot_min, plot_max]],
            cmap="viridis",
            cmin=1,
            norm=LogNorm(),
        )

        fig.colorbar(image, ax=axes[2], label="Counts")
        axes[2].set_title("CH1 vs CH2 Coincidence (2D)")
        axes[2].set_xlabel("CH1 Energy (MeV)")
        axes[2].set_ylabel("CH2 Energy (MeV)")
        axes[2].grid(True, linestyle="--", alpha=0.3)

        self._finish(fig, show=show)
        self._save(fig, filename)
        return fig, axes

    # 兼容你原来的函数名
    def plot_sum_energy_spectra(
        self,
        plot_min=0.0,
        plot_max=1.5,
        n_bins=200,
        show=True,
    ):
        """
        兼容旧接口: 只画两个加和谱。
        """
        e0, e1, e2 = self._get_energy_series_filled()

        mask_all3 = (e0 > 0) & (e1 > 0) & (e2 > 0)
        mask_12 = (e1 > 0) & (e2 > 0)

        e_sum_all3 = e0[mask_all3] + e1[mask_all3] + e2[mask_all3]
        e_sum_12 = e1[mask_12] + e2[mask_12]

        fig, axes = plt.subplots(1, 2, figsize=(12, 5))

        self._plot_hist_with_optional_gaussian_fit(
            axes[0],
            e_sum_all3,
            title="CH0 + CH1 + CH2 Energy Sum",
            color="#d62728",
            plot_min=plot_min,
            plot_max=plot_max,
            n_bins=n_bins,
            fit=True,
            fit_min=0.60,
            fit_max=0.78,
            legend_loc="upper left",
            resolution_use_fwhm=False,
        )

        self._plot_hist_with_optional_gaussian_fit(
            axes[1],
            e_sum_12,
            title="CH1 + CH2 Energy Sum",
            color="#9467bd",
            plot_min=plot_min,
            plot_max=plot_max,
            n_bins=n_bins,
            fit=True,
            fit_min=0.60,
            fit_max=0.78,
            legend_loc="upper left",
            resolution_use_fwhm=False,
        )

        self._finish(fig, show=show)
        return fig, axes

    def plot_ch1_ch2_2d_hist(
        self,
        plot_min=0.0,
        plot_max=1.5,
        n_bins=150,
        show=True,
    ):
        """
        兼容旧接口: 只画 CH1 energy vs CH2 energy 的二维直方图。
        """
        e1 = self.final_df["ch1_energy"].fillna(0)
        e2 = self.final_df["ch2_energy"].fillna(0)

        mask = (e1 > 0) & (e2 > 0)
        e1_valid = e1[mask]
        e2_valid = e2[mask]

        fig, ax = plt.subplots(figsize=(6, 5))

        _, _, _, image = ax.hist2d(
            e1_valid,
            e2_valid,
            bins=n_bins,
            range=[[plot_min, plot_max], [plot_min, plot_max]],
            cmap="viridis",
            cmin=1,
            norm=LogNorm(),
        )

        fig.colorbar(image, ax=ax, label="Counts")
        ax.set_title("CH1 vs CH2 Coincidence (2D)")
        ax.set_xlabel("CH1 Energy (MeV)")
        ax.set_ylabel("CH2 Energy (MeV)")
        ax.grid(True, linestyle="--", alpha=0.3)

        self._finish(fig, show=show)
        return fig, ax

    # ============================================================
    # 3. 三层加和能谱 vs 反推入射能量 E0，对应 notebook cell 3 第二张图
    # ============================================================

    def plot_energy_reconstruction_comparison(
        self,
        plot_min=0.0,
        plot_max=1.5,
        n_bins=200,
        fit=True,
        fit_min=0.60,
        fit_max=0.78,
        show=True,
        filename="energy_reconstruction_comparison.png",
    ):
        """
        画三层直接加和能谱与三层运动学反推 E0 的对比。
        """
        e0, e1, e2 = self._get_energy_series_filled()
        mask_all3 = (e0 > 0) & (e1 > 0) & (e2 > 0)

        e_sum_all3 = (e0 + e1 + e2)[mask_all3]

        p1 = self.final_df.loc[mask_all3, ["ch0_x", "ch0_y", "ch0_z"]].to_numpy(dtype=float)
        p2 = self.final_df.loc[mask_all3, ["ch1_x", "ch1_y", "ch1_z"]].to_numpy(dtype=float)
        p3 = self.final_df.loc[mask_all3, ["ch2_x", "ch2_y", "ch2_z"]].to_numpy(dtype=float)

        v1 = p2 - p1
        v2 = p3 - p2

        dot_product = np.sum(v1 * v2, axis=1)
        norm_v1 = np.linalg.norm(v1, axis=1)
        norm_v2 = np.linalg.norm(v2, axis=1)

        valid_norm_mask = (norm_v1 > 0) & (norm_v2 > 0)

        cos_theta2 = np.zeros_like(dot_product, dtype=float)
        cos_theta2[valid_norm_mask] = (
            dot_product[valid_norm_mask] / (norm_v1[valid_norm_mask] * norm_v2[valid_norm_mask])
        )

        d_e1 = e0[mask_all3].to_numpy(dtype=float)
        d_e2 = e1[mask_all3].to_numpy(dtype=float)

        valid_angle_mask = (1 - cos_theta2) > 1e-5

        e0_reconstructed = np.zeros_like(d_e1, dtype=float)
        term_under_sqrt = (
            d_e2[valid_angle_mask] ** 2
            + 4 * d_e2[valid_angle_mask] * self.m_e / (1 - cos_theta2[valid_angle_mask])
        )
        term_sqrt = np.sqrt(np.maximum(term_under_sqrt, 0))

        e0_reconstructed[valid_angle_mask] = (
            d_e1[valid_angle_mask] + (d_e2[valid_angle_mask] + term_sqrt) / 2
        )

        final_valid_mask = valid_norm_mask & valid_angle_mask & (e0_reconstructed > 0)

        e_sum_plot_data = e_sum_all3.to_numpy(dtype=float)[final_valid_mask]
        e0_plot_data = e0_reconstructed[final_valid_mask]

        fig, axes = plt.subplots(1, 2, figsize=(12, 5))

        self._plot_hist_with_optional_gaussian_fit(
            axes[0],
            e_sum_plot_data,
            title="3-Layer Sum Energy (CH0+CH1+CH2)",
            color="#ff7f0e",
            plot_min=plot_min,
            plot_max=plot_max,
            n_bins=n_bins,
            fit=fit,
            fit_min=fit_min,
            fit_max=fit_max,
            legend_loc="upper left",
            resolution_use_fwhm=False,
        )

        self._plot_hist_with_optional_gaussian_fit(
            axes[1],
            e0_plot_data,
            title=r"Reconstructed Incident Energy ($E_0$)",
            color="#2ca02c",
            plot_min=plot_min,
            plot_max=plot_max,
            n_bins=n_bins,
            fit=fit,
            fit_min=fit_min,
            fit_max=fit_max,
            legend_loc="upper left",
            resolution_use_fwhm=False,
        )

        fig.suptitle(
            "Energy Reconstruction Comparison (3-Layer Coincidence)",
            fontsize=14,
            fontweight="bold",
        )

        self._finish(fig, show=show)
        self._save(fig, filename)
        return fig, axes

    # ============================================================
    # 4. 3D Pixelated Brightness Map，对应 notebook cell 4
    # ============================================================

    def plot_3d_pixel_brightness_map(
        self,
        true_z_map=None,
        pixel_dx=3,
        pixel_dy=3,
        pixel_dz=3,
        show=True,
        filename="3d_pixel_brightness_map.png",
    ):
        """
        画 3D 像素亮度图。
        """
        if true_z_map is None:
            true_z_map = {
                "ch0": -61.5,
                "ch1": -25.0,
                "ch2": 0.0,
            }

        fig = plt.figure(figsize=(12, 10))
        ax = fig.add_subplot(111, projection="3d")

        global_max_count = 1
        pixel_data_list = []

        for ch in self.channels:
            mask = self.final_df[f"{ch}_energy"] > 0
            df_valid = self.final_df[mask]

            if not df_valid.empty:
                pixel_counts = (
                    df_valid.groupby([f"{ch}_x", f"{ch}_y"])
                    .size()
                    .reset_index(name="counts")
                )
                pixel_data_list.append(pixel_counts)
                global_max_count = max(global_max_count, pixel_counts["counts"].max())
            else:
                pixel_data_list.append(None)

        cmap = plt.get_cmap("jet")
        norm = mcolors.Normalize(vmin=1, vmax=global_max_count)
        legend_patches = []

        for i, ch in enumerate(self.channels):
            pixel_counts = pixel_data_list[i]
            if pixel_counts is None or pixel_counts.empty:
                continue

            x_center = pixel_counts[f"{ch}_x"].to_numpy(dtype=float)
            y_center = pixel_counts[f"{ch}_y"].to_numpy(dtype=float)
            counts = pixel_counts["counts"].to_numpy(dtype=float)

            real_z_val = true_z_map[ch]

            x_pos = x_center - pixel_dx / 2
            y_pos = y_center - pixel_dy / 2
            z_pos = np.full_like(x_center, real_z_val - pixel_dz / 2, dtype=float)

            dx = np.full_like(x_center, pixel_dx, dtype=float)
            dy = np.full_like(x_center, pixel_dy, dtype=float)
            dz = np.full_like(x_center, pixel_dz, dtype=float)

            colors = cmap(norm(counts))

            ax.bar3d(
                x_pos,
                y_pos,
                z_pos,
                dx,
                dy,
                dz,
                color=colors,
                alpha=0.9,
                shade=True,
            )

            legend_patches.append(
                mpatches.Patch(
                    color=cmap(0.5 - i * 0.2),
                    label=f"{ch.upper()} Layer (Z = {real_z_val} mm)",
                )
            )

        ax.set_title(
            "3D Pixelated Brightness Map (Grid Voxel)",
            fontsize=15,
            fontweight="bold",
            pad=20,
        )
        ax.set_xlabel("X Position (mm)")
        ax.set_ylabel("Y Position (mm)")
        ax.set_zlabel("Z Position (mm)")
        ax.set_zlim(-70, 10)
        ax.view_init(elev=20, azim=45)

        ax.legend(handles=legend_patches, loc="upper left", fontsize=10, framealpha=0.9)

        sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])
        cbar = fig.colorbar(sm, ax=ax, pad=0.1, shrink=0.7)
        cbar.set_label("Hit Counts (Brightness)", fontsize=12)

        self._finish(fig, show=show)
        self._save(fig, filename)
        return fig, ax

    # ============================================================
    # 5. 圆环重叠重建，对应 notebook cell 5
    # ============================================================

    def plot_overlapping_rings(
        self,
        z_plane=20.0,
        resolution=400,
        fov=100.0,
        num_events=100000,
        energy_window=(0.64, 0.68),
        require_no_ch0=True,
        line_thickness_deg=1.5,
        show=True,
        filename="overlapping_rings.png",
    ):
        """
        在给定 Z 平面上画康普顿圆环重叠图。
        """
        print("1. 从 final_df 中提取事件顶点、轴线与张角...")

        r1_positions, axes, angles = self._extract_two_hit_compton_events(
            energy_window=energy_window,
            require_no_ch0=require_no_ch0,
        )

        total_valid = len(axes)
        if total_valid == 0:
            print("没有找到符合物理规律的康普顿散射事件！请检查能量刻度或能量窗。")
            return None, None

        plot_num = min(total_valid, num_events)
        print(f"抽取 {plot_num} 个事件画圆环...")

        print(f"2. 在 Z = {z_plane} mm 平面上生成圆环轨迹...")
        x = np.linspace(-fov, fov, resolution)
        y = np.linspace(-fov, fov, resolution)
        xx, yy = np.meshgrid(x, y)
        zz = np.full_like(xx, z_plane)

        grid_points = np.stack((xx.ravel(), yy.ravel(), zz.ravel()), axis=1)
        image_array = np.zeros(len(grid_points), dtype=float)

        line_thickness = np.radians(line_thickness_deg)

        for i in range(plot_num):
            r1 = r1_positions[i]
            v_axis = axes[i]
            theta_expected = angles[i]

            v_pixel = grid_points - r1
            v_pixel_norms = np.linalg.norm(v_pixel, axis=1)

            valid = v_pixel_norms > 0
            cos_alpha = np.zeros_like(v_pixel_norms)
            cos_alpha[valid] = np.dot(v_pixel[valid], v_axis) / v_pixel_norms[valid]
            cos_alpha = np.clip(cos_alpha, -1.0, 1.0)
            alpha = np.arccos(cos_alpha)

            hit_mask = np.abs(alpha - theta_expected) < line_thickness
            image_array[hit_mask] += 1

        print("3. 绘制重叠圆环图像...")
        image_2d = image_array.reshape((resolution, resolution))

        max_idx = np.unravel_index(np.argmax(image_2d), image_2d.shape)
        peak_x = x[max_idx[1]]
        peak_y = y[max_idx[0]]
        max_overlap = int(np.max(image_2d))

        fig, ax = plt.subplots(figsize=(9, 7))
        im = ax.pcolormesh(x, y, image_2d, cmap="jet", shading="auto")

        ax.plot(
            peak_x,
            peak_y,
            "w+",
            markersize=20,
            markeredgewidth=2,
            label=f"Source: X={peak_x:.1f}, Y={peak_y:.1f}\nMax Overlap: {max_overlap} rings",
        )

        ax.set_title(
            f"Superposition of {plot_num} Valid Compton Rings at Z = {z_plane} mm",
            fontweight="bold",
        )
        ax.set_xlabel("X Position (mm)")
        ax.set_ylabel("Y Position (mm)")
        fig.colorbar(im, ax=ax, label="Number of Overlapping Rings")
        ax.legend(loc="upper right")

        det_size = 14 * 3.36 / 2
        ax.plot(
            [-det_size, det_size, det_size, -det_size, -det_size],
            [-det_size, -det_size, det_size, det_size, -det_size],
            "w--",
            alpha=0.5,
            label="Detector FOV (47x47mm)",
        )

        ax.set_aspect("equal", adjustable="box")

        self._finish(fig, show=show)
        self._save(fig, filename)
        return fig, ax

    # ============================================================
    # 6. ARM，对应 notebook cell 6
    # ============================================================

    def plot_arm(
        self,
        source_pos=(0.0, 0.0, 20.0),
        energy_window=(0.64, 0.68),
        show=True,
        filename=None,
    ):
        """
        计算并绘制 ARM 分布，返回:
            fig, ax, fwhm, fit_sigma
        """
        src = np.array(source_pos, dtype=float)
        arm_list = []

        print(f"1. 正在提取事件并计算 ARM (假定源位置: {source_pos})...")

        for row in self.final_df.itertuples(index=False):
            hits = self._iter_hits(row)

            if len(hits) != 2:
                continue

            e_total = sum(h[3] for h in hits)
            if not (energy_window[0] <= e_total <= energy_window[1]):
                continue

            hits.sort(key=lambda item: item[2], reverse=True)
            p1, p2 = hits[0], hits[1]

            pos1 = np.array([p1[0], p1[1], p1[2]], dtype=float)
            pos2 = np.array([p2[0], p2[1], p2[2]], dtype=float)
            e2_total = p2[3]

            cos_theta_meas = 1 - self.m_e * (1 / e2_total - 1 / e_total)
            if not (-1 <= cos_theta_meas <= 1):
                continue

            theta_meas = np.arccos(cos_theta_meas)

            vec_in = pos1 - src
            vec_out = pos2 - pos1

            norm_in = np.linalg.norm(vec_in)
            norm_out = np.linalg.norm(vec_out)

            if norm_in == 0 or norm_out == 0:
                continue

            cos_theta_geo = np.dot(vec_in, vec_out) / (norm_in * norm_out)
            cos_theta_geo = np.clip(cos_theta_geo, -1.0, 1.0)
            theta_geo = np.arccos(cos_theta_geo)

            arm_deg = np.degrees(theta_meas - theta_geo)
            arm_list.append(arm_deg)

        arm_array = np.asarray(arm_list, dtype=float)
        if len(arm_array) == 0:
            print("❌ 错误：没有提取到任何有效事件，无法计算 ARM。")
            return None, None, None, None

        print(f"✅ 成功计算 {len(arm_array)} 个事件的 ARM。正在进行高斯拟合...")

        fit_range = (-15, 15)
        filtered_arm = arm_array[(arm_array >= fit_range[0]) & (arm_array <= fit_range[1])]

        counts, bin_edges = np.histogram(filtered_arm, bins=60, density=True)
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

        p0 = [np.max(counts), 0.0, 3.0]

        try:
            popt, _ = curve_fit(self._gauss, bin_centers, counts, p0=p0)
            fit_mu = popt[1]
            fit_sigma = abs(popt[2])
            fwhm = 2.355 * fit_sigma
            fit_success = True
        except Exception as e:
            print(f"⚠️ 高斯拟合失败，使用常规统计标准差代替: {e}")
            fit_success = False
            fit_mu = np.mean(filtered_arm)
            fit_sigma = np.std(filtered_arm)
            fwhm = 2.355 * fit_sigma

        fig, ax = plt.subplots(figsize=(8, 6))

        ax.hist(
            arm_array,
            bins=100,
            range=(-25, 25),
            density=True,
            alpha=0.6,
            color="steelblue",
            edgecolor="black",
            label="ARM Distribution",
        )

        if fit_success:
            x_fit = np.linspace(-25, 25, 500)
            ax.plot(
                x_fit,
                self._gauss(x_fit, *popt),
                "r-",
                lw=2.5,
                label=(
                    "Gaussian Fit\n"
                    f"$\\mu$ = {fit_mu:.2f}$^\\circ$\n"
                    f"$\\sigma$ = {fit_sigma:.2f}$^\\circ$"
                ),
            )

        ax.axvline(0, color="gray", linestyle="--", lw=1.5)

        bbox_props = dict(
            boxstyle="round,pad=0.4",
            fc="ivory",
            ec="darkred",
            lw=1.5,
        )
        ax.text(
            0.05,
            0.85,
            f"System FWHM: {fwhm:.2f}°\n(Source: {source_pos})",
            transform=ax.transAxes,
            fontsize=12,
            fontweight="bold",
            color="darkred",
            bbox=bbox_props,
        )

        ax.set_title("Compton Angular Resolution Measure (ARM)", fontweight="bold", fontsize=14)
        ax.set_xlabel(r"ARM = $\theta_{measured} - \theta_{geometric}$ (Degrees)", fontsize=12)
        ax.set_ylabel("Probability Density", fontsize=12)
        ax.legend(loc="upper right")
        ax.grid(True, alpha=0.3, linestyle="--")

        self._finish(fig, show=show)
        self._save(fig, filename)
        return fig, ax, fwhm, fit_sigma

    def scan_arm_positions(
        self,
        x_range=range(16, 20),
        y_range=range(13, 17),
        z=20.0,
        energy_window=(0.652, 0.672),
        show=True,
    ):
        """
        复现 notebook cell 6 里 16 个源位置的 ARM 扫描。
        """
        results = []

        for x in x_range:
            for y in y_range:
                fig, ax, fwhm, sigma = self.plot_arm(
                    source_pos=(x, y, z),
                    energy_window=energy_window,
                    show=show,
                    filename=f"arm_source_x{x}_y{y}_z{z}.png" if self.save_dir is not None else None,
                )

                results.append(
                    {
                        "x": x,
                        "y": y,
                        "z": z,
                        "fwhm": fwhm,
                        "sigma": sigma,
                    }
                )

        return pd.DataFrame(results)

    # ============================================================
    # 7. MLEM，对应 notebook cell 7/8/9
    # ============================================================

    def plot_mlem_reconstruction(
        self,
        z_plane=20.0,
        resolution=250,
        fov=60.0,
        num_events=100000,
        energy_window=(0.64, 0.68),
        iterations=15,
        sigma_deg=2.5,
        show=True,
        filename="mlem_reconstruction.png",
    ):
        """
        List-Mode MLEM 重建图。

        cell 7/8/9 的主体代码基本相同，只是 energy_window 和 sigma_deg 不同。
        所以这里做成参数。
        """
        print("1. 正在提取和筛选康普顿事件...")

        r1_positions, axes, angles = self._extract_two_hit_compton_events(
            energy_window=energy_window,
            require_no_ch0=False,
        )

        plot_num = min(len(axes), num_events)
        if plot_num == 0:
            print("❌ 错误：没有提取到任何有效事件，请检查 final_df 数据格式或能量窗！")
            return None, None

        print(f"✅ 成功提取 {plot_num} 个有效事件。")

        print(f"2. 初始化 Z = {z_plane} mm 平面网格...")
        x = np.linspace(-fov, fov, resolution)
        y = np.linspace(-fov, fov, resolution)
        xx, yy = np.meshgrid(x, y)
        grid_points = np.stack((xx.ravel(), yy.ravel(), np.full_like(xx.ravel(), z_plane)), axis=1)

        image_mlem = np.ones(len(grid_points), dtype=float)
        sigma_rad = np.radians(sigma_deg)

        print(f"3. 开始 List-Mode MLEM 迭代 ({iterations} 次)...")
        start_time = time.time()

        for it in range(iterations):
            update_factor = np.zeros(len(grid_points), dtype=float)
            valid_events_this_iter = 0

            for i in range(plot_num):
                v_pixel = grid_points - r1_positions[i]
                v_pixel_norms = np.linalg.norm(v_pixel, axis=1) + 1e-10

                cos_alpha = np.sum(v_pixel * axes[i], axis=1) / v_pixel_norms
                cos_alpha = np.clip(cos_alpha, -1.0, 1.0)
                alpha = np.arccos(cos_alpha)

                t_i = np.exp(-0.5 * ((alpha - angles[i]) / sigma_rad) ** 2)
                t_i[t_i < 1e-3] = 0.0

                f_i = np.sum(t_i * image_mlem)

                if f_i > 1e-12:
                    update_factor += t_i / f_i
                    valid_events_this_iter += 1

            image_mlem = image_mlem * update_factor

            max_val = np.max(image_mlem)
            print(
                f"   - 迭代 {it + 1}/{iterations} | "
                f"参与事件: {valid_events_this_iter}/{plot_num} | "
                f"图像峰值: {max_val:.2e}"
            )

        print(f"迭代完成，耗时: {time.time() - start_time:.2f} 秒")

        print("4. 绘制 MLEM 重建结果...")
        image_2d = image_mlem.reshape((resolution, resolution))

        max_image = np.max(image_2d)
        if max_image > 0:
            image_2d = image_2d / max_image

        max_idx = np.unravel_index(np.argmax(image_2d), image_2d.shape)
        peak_x = x[max_idx[1]]
        peak_y = y[max_idx[0]]

        fig, ax = plt.subplots(figsize=(9, 7))
        im = ax.pcolormesh(x, y, image_2d, cmap="jet", shading="auto")

        ax.plot(
            peak_x,
            peak_y,
            "c+",
            markersize=20,
            markeredgewidth=2,
            label=f"Reconstructed Source\nX: {peak_x:.1f} mm, Y: {peak_y:.1f} mm",
        )

        ax.set_title(
            f"MLEM Reconstruction (Iter={iterations}, Z={z_plane}mm)",
            fontweight="bold",
        )
        ax.set_xlabel("X Position (mm)")
        ax.set_ylabel("Y Position (mm)")
        fig.colorbar(im, ax=ax, label="Relative Intensity")

        det_size = 14 * 3.36 / 2
        ax.plot(
            [-det_size, det_size, det_size, -det_size, -det_size],
            [-det_size, -det_size, det_size, det_size, -det_size],
            "w--",
            alpha=0.5,
            label="Detector FOV (47x47mm)",
        )

        ax.legend(loc="upper right")
        ax.set_aspect("equal", adjustable="box")

        self._finish(fig, show=show)
        self._save(fig, filename)
        return fig, ax

    # ============================================================
    # 一键输出
    # ============================================================

    def plot_all_basic(self, show=False):
        """
        输出基础图片，不包含耗时很长的 ARM 扫描和 MLEM。
        """
        self.plot_single_channel_spectra(show=show)
        self.plot_sum_energy_and_ch1_ch2_2d(show=show)
        self.plot_energy_reconstruction_comparison(show=show)
        self.plot_3d_pixel_brightness_map(show=show)
        self.plot_overlapping_rings(show=show)

    def plot_all_original_like(self, show=False):
        """
        尽量复现 notebook 里所有主要图片。

        注意:
            1. ARM 扫描会画 16 张图。
            2. MLEM 很耗时。
            3. cell 7/8/9 的 MLEM 代码基本重复，这里按三个参数组输出三张。
        """
        self.plot_single_channel_spectra(show=show)
        self.plot_sum_energy_and_ch1_ch2_2d(show=show)
        self.plot_energy_reconstruction_comparison(show=show)
        self.plot_3d_pixel_brightness_map(show=show)
        self.plot_overlapping_rings(show=show)

        self.scan_arm_positions(show=show)

        self.plot_mlem_reconstruction(
            energy_window=(0.64, 0.68),
            sigma_deg=2.5,
            filename="mlem_window_064_068_sigma_25.png",
            show=show,
        )
        self.plot_mlem_reconstruction(
            energy_window=(0.652, 0.672),
            sigma_deg=8.0,
            filename="mlem_window_0652_0672_sigma_80.png",
            show=show,
        )
        self.plot_mlem_reconstruction(
            energy_window=(0.652, 0.672),
            sigma_deg=8.3,
            filename="mlem_window_0652_0672_sigma_83.png",
            show=show,
        )
    def plot_all(self, show=False, full=False):
        """
        兼容旧版接口。

        full=False:
            只画基础图，等价于 plot_all_basic()

        full=True:
            尝试画完整复现图，等价于 plot_all_original_like()
        """

        if full:
            return self.plot_all_original_like(show=show)
        else:
            return self.plot_all_basic(show=show)
