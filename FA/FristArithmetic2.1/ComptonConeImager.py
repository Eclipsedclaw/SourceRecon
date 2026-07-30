# ComptonConeImager.py

import os
import numpy as np
import matplotlib.pyplot as plt


class ComptonConeImager:
    """
    康普顿锥加权成像类。

    输入：
        EventList 对象。

    功能：
        1. 根据每个 event.score 生成该 event 的参考权重；
        2. 将每个 event 转换为探测器前方某一平面上的 Compton cone response；
        3. 把所有 cone response 加权叠加，形成二维图像；
        4. 输出多张诊断图，帮助评估打分和成像效果。

    注意：
        这是第一版 weighted backprojection。
        后期可以升级成 list-mode MLEM。
    """

    def __init__(
        self,
        event_list,
        image_plane_z=None,
        plane_distance_mm=100.0,
        x_range=(-150.0, 150.0),
        y_range=(-150.0, 150.0),
        n_pixels=200,
        sigma_angle_deg=5.0,
        min_score=0.0,
        output_dir=None,
        known_primary_energy_mev=None,
    ):
        self.event_list = event_list

        self.image_plane_z = image_plane_z
        self.plane_distance_mm = plane_distance_mm

        self.x_range = x_range
        self.y_range = y_range
        self.n_pixels = n_pixels

        self.sigma_angle = np.deg2rad(sigma_angle_deg)
        self.min_score = min_score
        self.known_primary_energy_mev = known_primary_energy_mev

        if output_dir is None:
            output_dir = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "output_images",
            )
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

        self.image = None
        self.x_grid = None
        self.y_grid = None

        self.event_weights = []
        self.used_events = []

    # ============================================================
    # 1. 事件权重
    # ============================================================

    def calculate_event_weight(self, event):
        """
        成像权重。

        新逻辑：
            weight = match_prob * full_deposition_prob

        这样非全沉积 event 会被 gate 压低。
        """

        match_prob = float(getattr(event, "match_prob", 0.0))
        full_prob = float(getattr(event, "full_deposition_prob", 0.0))
        if match_prob > 0.0 or full_prob > 0.0:
            weight = float(
                match_prob * full_prob
            )
        else:
            imaging_weight = float(getattr(event, "imaging_weight", 0.0))
            weight = (
                imaging_weight
                if imaging_weight != 0.0
                else float(getattr(event, "score", 0.0))
            )

        if weight < self.min_score:
            return 0.0

        return weight
    # ============================================================
    # 2. 成像平面
    # ============================================================

    def _auto_set_image_plane_z(self):
        """
        自动选择探测器正前方的成像平面 z。

        如果用户没有手动给 image_plane_z，
        就用所有 event 第一个 hit 的 z 坐标的最小值再向前移动 plane_distance_mm。

        你现在 ch0 的 z 看起来是 -61.5 mm，
        如果 ch0 是最前层，那么默认成像平面大概会在：
            -61.5 - 100 = -161.5 mm

        这个方向假设源在 detector 前方的负 z 侧。
        如果你实际坐标系相反，只需要手动传入 image_plane_z。
        """

        if self.image_plane_z is not None:
            return self.image_plane_z

        z_values = []

        for event in self.event_list.events:
            if hasattr(event, "r1"):
                z_values.append(float(event.r1[2]))

        if len(z_values) == 0:
            raise ValueError("EventList 中没有可用的 r1 坐标，无法自动确定成像平面。")

        front_z = min(z_values)
        self.image_plane_z = front_z - self.plane_distance_mm

        return self.image_plane_z

    def _build_image_grid(self):
        """
        构造二维成像平面网格。
        """

        x = np.linspace(self.x_range[0], self.x_range[1], self.n_pixels)
        y = np.linspace(self.y_range[0], self.y_range[1], self.n_pixels)

        self.x_grid, self.y_grid = np.meshgrid(x, y)

        z0 = self._auto_set_image_plane_z()
        z_grid = np.full_like(self.x_grid, z0, dtype=float)

        return self.x_grid, self.y_grid, z_grid

    # ============================================================
    # 3. 单个 event 的 cone response
    # ============================================================

    def _get_event_compton_angle(self, event):
        """
        只有 full_deposition_prob 足够高时，
        才允许使用 deposited-energy-sum 推出来的康普顿角。

        因为这个角度隐含假设：
            E_in = E_dep_sum
        """

        full_prob = float(getattr(event, "full_deposition_prob", 0.0))

        if full_prob < 0.5:
            return np.nan

        # Optional diagnostic interface. Production unknown-energy imaging
        # leaves this as None and uses the deposited-energy sum only after the
        # candidate full-absorption probability gate.
        if self.known_primary_energy_mev is not None:
            e0 = float(self.known_primary_energy_mev)
            e1 = float(getattr(event, "E1", np.nan))
            e_after = e0 - e1
            if e0 <= 0 or e_after <= 0:
                return np.nan
            cos_theta = 1.0 - 0.51099895 * (
                1.0 / e_after - 1.0 / e0
            )
            if cos_theta < -1.0 or cos_theta > 1.0:
                return np.nan
            return float(np.arccos(cos_theta))

        if hasattr(event, "theta_c"):
            return float(event.theta_c)

        if hasattr(event, "theta_c_first"):
            return float(event.theta_c_first)

        return np.nan

    def _event_cone_response(self, event, x_grid, y_grid, z_grid):
        """
        计算单个 event 在成像平面上的 cone response。

        对每个像素 p：
            计算 p -> r1 的入射方向
            计算 r1 -> r2 的散射方向
            比较几何角 theta_geo 和康普顿角 theta_c

        response 越大，说明该像素越可能是源位置。
        """

        theta_c = self._get_event_compton_angle(event)

        if np.isnan(theta_c):
            return None

        if not hasattr(event, "r1") or not hasattr(event, "r2"):
            return None

        r1 = event.r1
        r2 = event.r2

        scatter_axis = r2 - r1
        scatter_norm = np.linalg.norm(scatter_axis)

        if scatter_norm == 0:
            return None

        scatter_axis = scatter_axis / scatter_norm

        # pixel -> r1 的方向，也就是 gamma 入射方向
        vx = r1[0] - x_grid
        vy = r1[1] - y_grid
        vz = r1[2] - z_grid

        norm = np.sqrt(vx ** 2 + vy ** 2 + vz ** 2)

        valid = norm > 0

        ux = np.zeros_like(vx)
        uy = np.zeros_like(vy)
        uz = np.zeros_like(vz)

        ux[valid] = vx[valid] / norm[valid]
        uy[valid] = vy[valid] / norm[valid]
        uz[valid] = vz[valid] / norm[valid]

        cos_theta_geo = (
            ux * scatter_axis[0]
            + uy * scatter_axis[1]
            + uz * scatter_axis[2]
        )

        cos_theta_geo = np.clip(cos_theta_geo, -1.0, 1.0)

        theta_geo = np.arccos(cos_theta_geo)

        delta_theta = theta_geo - theta_c

        response = np.exp(
            -0.5 * (delta_theta / self.sigma_angle) ** 2
        )

        return response

    # ============================================================
    # 4. 总成像
    # ============================================================

    def reconstruct_image(self):
        """
        叠加所有 event 的 Compton cone response。
        """

        x_grid, y_grid, z_grid = self._build_image_grid()

        image = np.zeros_like(x_grid, dtype=float)

        self.event_weights = []
        self.used_events = []

        for event in self.event_list.events:
            weight = self.calculate_event_weight(event)

            if weight <= 0:
                continue

            response = self._event_cone_response(
                event,
                x_grid,
                y_grid,
                z_grid,
            )

            if response is None:
                continue

            image += weight * response

            self.event_weights.append(weight)
            self.used_events.append(event)

        self.image = image

        return image

    # ============================================================
    # 5. 诊断图
    # ============================================================

    def plot_reconstructed_image(self, filename="01_reconstructed_image.png"):
        """
        输出最终叠加图像。
        """

        image = self.image

        if image is None:
            image = self.reconstruct_image()

        plt.figure(figsize=(7, 6))
        plt.imshow(
            image,
            extent=[
                self.x_range[0], self.x_range[1],
                self.y_range[0], self.y_range[1],
            ],
            origin="lower",
            aspect="equal",
        )
        plt.colorbar(label="Weighted cone intensity")
        plt.xlabel("x / mm")
        plt.ylabel("y / mm")
        plt.title(f"Weighted Compton Cone Image at z = {self.image_plane_z:.1f} mm")

        path = os.path.join(self.output_dir, filename)
        plt.tight_layout()
        plt.savefig(path, dpi=200)
        plt.close()

        return path

    def plot_log_reconstructed_image(self, filename="02_log_reconstructed_image.png"):
        """
        输出 log 版本图像，方便看弱结构和背景。
        """

        image = self.image

        if image is None:
            image = self.reconstruct_image()

        log_image = np.log1p(image)

        plt.figure(figsize=(7, 6))
        plt.imshow(
            log_image,
            extent=[
                self.x_range[0], self.x_range[1],
                self.y_range[0], self.y_range[1],
            ],
            origin="lower",
            aspect="equal",
        )
        plt.colorbar(label="log(1 + intensity)")
        plt.xlabel("x / mm")
        plt.ylabel("y / mm")
        plt.title("Log Weighted Compton Cone Image")

        path = os.path.join(self.output_dir, filename)
        plt.tight_layout()
        plt.savefig(path, dpi=200)
        plt.close()

        return path

    def plot_score_histogram(self, filename="03_event_score_histogram.png"):
        """
        输出 EventList 中所有 event 的 score 分布。
        """

        scores_2hit = []
        scores_3hit = []

        for event in self.event_list.events:
            score = float(getattr(event, "score", 0.0))

            if getattr(event, "n_hits", None) == 2:
                scores_2hit.append(score)

            elif getattr(event, "n_hits", None) == 3:
                scores_3hit.append(score)

        plt.figure(figsize=(7, 5))

        if len(scores_2hit) > 0:
            plt.hist(scores_2hit, bins=50, alpha=0.6, label="2-hit")

        if len(scores_3hit) > 0:
            plt.hist(scores_3hit, bins=50, alpha=0.6, label="3-hit")

        plt.xlabel("event score")
        plt.ylabel("counts")
        plt.title("Event Score Distribution")
        plt.legend()

        path = os.path.join(self.output_dir, filename)
        plt.tight_layout()
        plt.savefig(path, dpi=200)
        plt.close()

        return path

    def plot_weight_histogram(self, filename="04_event_weight_histogram.png"):
        """
        输出参与成像的 event 权重分布。
        """

        if self.image is None:
            self.reconstruct_image()

        plt.figure(figsize=(7, 5))
        plt.hist(self.event_weights, bins=50)
        plt.xlabel("event imaging weight")
        plt.ylabel("counts")
        plt.title("Imaging Weight Distribution")

        path = os.path.join(self.output_dir, filename)
        plt.tight_layout()
        plt.savefig(path, dpi=200)
        plt.close()

        return path

    def plot_delta_cos_histogram(self, filename="05_delta_cos_second_histogram.png"):
        """
        输出 3-hit 的 delta_cos_second 分布。
        """

        delta_values = []

        for event in self.event_list.events:
            if getattr(event, "n_hits", None) != 3:
                continue

            value = getattr(event, "delta_cos_second", None)

            if value is None:
                continue

            if np.isnan(value):
                continue

            delta_values.append(value)

        plt.figure(figsize=(7, 5))

        if len(delta_values) > 0:
            plt.hist(delta_values, bins=80)

        plt.xlabel("delta_cos_second")
        plt.ylabel("counts")
        plt.title("3-hit Compton Consistency Distribution")

        path = os.path.join(self.output_dir, filename)
        plt.tight_layout()
        plt.savefig(path, dpi=200)
        plt.close()

        return path

    def plot_top_event_responses(
        self,
        n_events=6,
        filename_prefix="06_top_event_response",
    ):
        """
        输出若干个最高权重 event 的单独 cone response。
        用来检查单个 cone 是否合理。
        """

        if self.image is None:
            self.reconstruct_image()

        x_grid, y_grid, z_grid = self._build_image_grid()

        weighted_events = []

        for event in self.event_list.events:
            weight = self.calculate_event_weight(event)
            if weight <= 0:
                continue

            response = self._event_cone_response(
                event,
                x_grid,
                y_grid,
                z_grid,
            )
            if response is None:
                continue

            response_peak = float(np.max(response))
            if response_peak <= 1e-6:
                continue

            effective_peak = weight * response_peak
            weighted_events.append(
                (effective_peak, weight, event, response)
            )

        weighted_events = sorted(
            weighted_events,
            key=lambda item: item[0],
            reverse=True,
        )

        paths = []

        for i, (_, weight, event, response) in enumerate(
            weighted_events[:n_events]
        ):

            plt.figure(figsize=(6, 5))
            plt.imshow(
                response,
                extent=[
                    self.x_range[0], self.x_range[1],
                    self.y_range[0], self.y_range[1],
                ],
                origin="lower",
                aspect="equal",
            )
            plt.colorbar(label="single event response")
            plt.xlabel("x / mm")
            plt.ylabel("y / mm")
            plt.title(
                f"Top event {i}, weight={weight:.3f}, "
                f"type={event.event_type}"
            )

            path = os.path.join(
                self.output_dir,
                f"{filename_prefix}_{i}.png",
            )
            plt.tight_layout()
            plt.savefig(path, dpi=200)
            plt.close()

            paths.append(path)

        return paths

    def save_all_diagnostic_plots(self):
        """
        一键输出所有诊断图。
        """

        self.reconstruct_image()

        paths = []

        paths.append(self.plot_reconstructed_image())
        paths.append(self.plot_log_reconstructed_image())
        paths.append(self.plot_score_histogram())
        paths.append(self.plot_weight_histogram())
        paths.append(self.plot_delta_cos_histogram())
        paths.extend(self.plot_top_event_responses(n_events=6))

        return paths
