# ComptonConeImager.py

import os
import numpy as np
import matplotlib.pyplot as plt


class ComptonConeImager:
    """
    康普顿锥加权成像类（物理管线版）。

    相比旧版本的核心变化：

        1. 2-hit 默认不参与成像（include_two_hit=False）。
           2-hit 没有冗余约束无法自证，未知能谱下锥角不可信；
           等 MC 训练出全吸收门控后再打开。

        2. min_score 门控真正生效。
           3-hit 的 score = exp(-pull^2/2)，阈值可按 sigma 换算：
               min_score=0.61 等价于 |pull|<1
               min_score=0.14 等价于 |pull|<2

        3. 每个 event 的锥响应可归一化（normalize_response），
           避免大环因覆盖像素多而在图像边缘堆出伪影
           （旧图右上角的亮区就是这么来的）。

        4. 新增诊断图：
               pull 分布图（替代裸 delta 图，判读更直接）
               通过筛选事件的 E_total 谱（"自测能谱"，
               不需要任何源先验，本身就是在轨科学产出）。

        5. 新增 z 平面扫描 scan_plane_distance()：
           环在真实源距离处聚焦，峰均比最大的平面就是源所在平面，
           同时检验 z 方向符号假设。
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
        min_score=0.2,
        include_two_hit=False,
        two_hit_weight_factor=0.25,
        max_abs_pull=None,
        normalize_response=True,
        output_dir="figure/compton_imaging",
    ):
        """
        新增参数说明：

            min_score:
                参与成像的最低分数。默认 0.2（约 |pull| < 1.8）。

            include_two_hit:
                是否允许 2-hit 参与成像。默认 False。

            two_hit_weight_factor:
                include_two_hit=True 时 2-hit 分数的额外折减因子。

            max_abs_pull:
                可选的 pull 硬切割（例如 2.0）。
                None 表示只用 min_score 门控。

            normalize_response:
                是否把每个 event 的锥响应归一化成总和为 1。
                默认 True，抑制大环的边缘伪影。
        """

        self.event_list = event_list

        self.image_plane_z = image_plane_z
        self.plane_distance_mm = plane_distance_mm

        self.x_range = x_range
        self.y_range = y_range
        self.n_pixels = n_pixels

        self.sigma_angle = np.deg2rad(sigma_angle_deg)
        self.min_score = min_score

        self.include_two_hit = include_two_hit
        self.two_hit_weight_factor = two_hit_weight_factor
        self.max_abs_pull = max_abs_pull
        self.normalize_response = normalize_response

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
        根据 event.score 和门控条件决定成像权重。

        3-hit：
            通过 min_score（以及可选的 max_abs_pull）→ weight = score
        2-hit：
            默认权重 0（不参与）。
            include_two_hit=True 时 weight = factor * score。
        """

        score = float(getattr(event, "score", 0.0))
        n_hits = getattr(event, "n_hits", None)

        if n_hits == 3:
            if self.max_abs_pull is not None:
                pull = getattr(event, "pull_second", np.nan)

                if pull is None or not np.isfinite(pull):
                    return 0.0

                if abs(pull) > self.max_abs_pull:
                    return 0.0

            if score < self.min_score:
                return 0.0

            return score

        if n_hits == 2:
            if not self.include_two_hit:
                return 0.0

            if score < self.min_score:
                return 0.0

            return self.two_hit_weight_factor * score

        return 0.0

    # ============================================================
    # 2. 成像平面与网格
    # ============================================================

    def _front_z(self):
        """
        所有 event 第一个 hit 的最小 z，视为探测器最前层。
        """

        z_values = []

        for event in self.event_list.events:
            if hasattr(event, "r1"):
                z_values.append(float(event.r1[2]))

        if len(z_values) == 0:
            raise ValueError("EventList 中没有可用的 r1 坐标。")

        return min(z_values)

    def _auto_set_image_plane_z(self):
        """
        自动选择成像平面 z。

        没有手动给 image_plane_z 时，
        用最前层 z 再向前移 plane_distance_mm。
        方向假设：源在探测器前方的负 z 侧。
        如果坐标系相反，手动传入 image_plane_z，
        或用 scan_plane_distance() 两个方向都扫一遍验证。
        """

        if self.image_plane_z is not None:
            return self.image_plane_z

        self.image_plane_z = self._front_z() - self.plane_distance_mm

        return self.image_plane_z

    def _build_grid_at_z(self, z0):
        """
        构造给定 z 处的成像平面网格。
        """

        x = np.linspace(self.x_range[0], self.x_range[1], self.n_pixels)
        y = np.linspace(self.y_range[0], self.y_range[1], self.n_pixels)

        self.x_grid, self.y_grid = np.meshgrid(x, y)

        z_grid = np.full_like(self.x_grid, z0, dtype=float)

        return self.x_grid, self.y_grid, z_grid

    # ============================================================
    # 3. 单个 event 的 cone response
    # ============================================================

    def _get_event_compton_angle(self, event):
        if hasattr(event, "theta_c") and getattr(event, "n_hits", None) == 2:
            return float(event.theta_c)

        if hasattr(event, "theta_c_first"):
            return float(event.theta_c_first)

        if hasattr(event, "theta_c"):
            return float(event.theta_c)

        return np.nan

    def _event_cone_response(self, event, x_grid, y_grid, z_grid):
        """
        计算单个 event 在成像平面上的 cone response。
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
    # 4. 成像核心
    # ============================================================

    def _collect_weighted_events(self):
        """
        收集所有通过门控的 (weight, event)。
        """

        weighted = []

        for event in self.event_list.events:
            weight = self.calculate_event_weight(event)

            if weight > 0:
                weighted.append((weight, event))

        return weighted

    def _reconstruct_at_z(self, z0, weighted_events, track=False):
        """
        在给定 z 平面上叠加所有 cone response。
        """

        x_grid, y_grid, z_grid = self._build_grid_at_z(z0)

        image = np.zeros_like(x_grid, dtype=float)

        if track:
            self.event_weights = []
            self.used_events = []

        for weight, event in weighted_events:
            response = self._event_cone_response(
                event, x_grid, y_grid, z_grid
            )

            if response is None:
                continue

            if self.normalize_response:
                total = response.sum()

                if total <= 0:
                    continue

                response = response / total

            image += weight * response

            if track:
                self.event_weights.append(weight)
                self.used_events.append(event)

        return image

    def reconstruct_image(self):
        """
        在默认成像平面上重建图像。
        """

        z0 = self._auto_set_image_plane_z()

        weighted_events = self._collect_weighted_events()

        self.image = self._reconstruct_at_z(
            z0, weighted_events, track=True
        )

        return self.image

    # ============================================================
    # 5. z 平面扫描（调焦）
    # ============================================================

    def scan_plane_distance(
        self,
        d_min=20.0,
        d_max=300.0,
        n_planes=15,
        filename="08_plane_distance_scan.png",
        save_best_image=True,
    ):
        """
        扫描成像平面到最前层的距离，寻找环聚焦最锐的平面。

        对每个距离 d：
            z = front_z - d
            重建图像，计算峰均比 image.max() / image.mean()

        峰均比最大的 d 对应源的真实距离。
        如果所有 d 峰均比都平坦接近 1，
        说明环没有公共交点——要么方向假设错了
        （试试 z = front_z + d），要么事件质量还不够。

        返回：
            best_distance, best_z, distances, metrics
        """

        front_z = self._front_z()

        weighted_events = self._collect_weighted_events()

        if len(weighted_events) == 0:
            raise RuntimeError(
                "没有事件通过门控，无法扫描。请降低 min_score 检查。"
            )

        distances = np.linspace(d_min, d_max, n_planes)

        metrics = []

        for d in distances:
            z0 = front_z - d

            image = self._reconstruct_at_z(z0, weighted_events)

            mean_val = image.mean()

            if mean_val > 0:
                metric = image.max() / mean_val
            else:
                metric = 0.0

            metrics.append(metric)

        metrics = np.array(metrics)

        best_index = int(np.argmax(metrics))
        best_distance = float(distances[best_index])
        best_z = front_z - best_distance

        # ---------- 曲线图 ----------
        plt.figure(figsize=(8, 5))
        plt.plot(distances, metrics, marker="o")
        plt.axvline(
            best_distance,
            color="crimson",
            linestyle="--",
            label=f"best d = {best_distance:.0f} mm (z = {best_z:.1f})",
        )
        plt.xlabel("plane distance to front layer / mm")
        plt.ylabel("peak-to-mean ratio")
        plt.title("Focus Scan over Image Plane Distance")
        plt.legend()
        plt.grid(alpha=0.3)

        path = os.path.join(self.output_dir, filename)
        plt.tight_layout()
        plt.savefig(path, dpi=200)
        plt.close()

        # ---------- 最佳平面的图像 ----------
        if save_best_image:
            best_image = self._reconstruct_at_z(best_z, weighted_events)

            plt.figure(figsize=(7, 6))
            plt.imshow(
                best_image,
                extent=[
                    self.x_range[0], self.x_range[1],
                    self.y_range[0], self.y_range[1],
                ],
                origin="lower",
                aspect="equal",
            )
            plt.colorbar(label="weighted cone intensity")
            plt.xlabel("x / mm")
            plt.ylabel("y / mm")
            plt.title(f"Best-Focus Image at z = {best_z:.1f} mm")

            best_path = os.path.join(
                self.output_dir, "09_best_focus_image.png"
            )
            plt.tight_layout()
            plt.savefig(best_path, dpi=200)
            plt.close()

        return best_distance, best_z, distances, metrics

    # ============================================================
    # 6. 诊断图
    # ============================================================

    def plot_reconstructed_image(self, filename="01_reconstructed_image.png"):
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
        plt.title(
            f"Weighted Compton Cone Image at z = {self.image_plane_z:.1f} mm"
        )

        path = os.path.join(self.output_dir, filename)
        plt.tight_layout()
        plt.savefig(path, dpi=200)
        plt.close()

        return path

    def plot_log_reconstructed_image(
        self, filename="02_log_reconstructed_image.png"
    ):
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

        plt.axvline(
            self.min_score,
            color="crimson",
            linestyle="--",
            linewidth=1.0,
            label=f"min_score = {self.min_score}",
        )

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
        if self.image is None:
            self.reconstruct_image()

        plt.figure(figsize=(7, 5))

        if len(self.event_weights) > 0:
            plt.hist(self.event_weights, bins=50)

        plt.xlabel("event imaging weight")
        plt.ylabel("counts")
        plt.title(
            f"Imaging Weight Distribution "
            f"(n_used = {len(self.event_weights)})"
        )

        path = os.path.join(self.output_dir, filename)
        plt.tight_layout()
        plt.savefig(path, dpi=200)
        plt.close()

        return path

    def plot_pull_histogram(
        self,
        pull_range=(-8.0, 8.0),
        filename="05_pull_second_histogram.png",
    ):
        """
        3-hit 的 pull 分布。

        判读：
            真事件应在 0 附近形成标准正态形状的峰；
            假组合是宽平台。
            配合 MixedEventBackground 的本底模板一起看。
        """

        pulls = []

        for event in self.event_list.events:
            if getattr(event, "n_hits", None) != 3:
                continue

            pull = getattr(event, "pull_second", None)

            if pull is None or not np.isfinite(pull):
                continue

            pulls.append(pull)

        plt.figure(figsize=(7, 5))

        if len(pulls) > 0:
            plt.hist(
                np.clip(pulls, pull_range[0], pull_range[1]),
                bins=100,
            )

        plt.axvline(-2.0, color="gray", linestyle="--", linewidth=0.8)
        plt.axvline(2.0, color="gray", linestyle="--", linewidth=0.8)

        plt.xlabel("pull = delta_cos_second / sigma_delta")
        plt.ylabel("counts")
        plt.title("3-hit Pull Distribution")

        path = os.path.join(self.output_dir, filename)
        plt.tight_layout()
        plt.savefig(path, dpi=200)
        plt.close()

        return path

    def plot_accepted_energy_spectrum(
        self,
        n_bins=120,
        filename="06_accepted_energy_spectrum.png",
    ):
        """
        通过门控、参与成像的事件的 E_total 谱。

        物理含义：
            通过 pull 检验 = 组合正确 + 全吸收，
            此时 E_total 就是入射 gamma 的真实能量。
            这张谱不需要任何源先验，
            天上它就是仪器的自测能谱（科学产出之一）。

        判读（地面验证）：
            如果谱上出现你实验室源的特征峰
            （你知道是什么源，但算法不知道），
            整条筛选链路就被实测数据验证了。
        """

        if self.image is None:
            self.reconstruct_image()

        energies = [
            float(event.E_total)
            for event in self.used_events
            if hasattr(event, "E_total")
        ]

        plt.figure(figsize=(7, 5))

        if len(energies) > 0:
            plt.hist(energies, bins=n_bins)

        plt.xlabel("E_total / MeV")
        plt.ylabel("counts")
        plt.title(
            "Self-measured Spectrum of Accepted Events "
            f"(n = {len(energies)})"
        )

        path = os.path.join(self.output_dir, filename)
        plt.tight_layout()
        plt.savefig(path, dpi=200)
        plt.close()

        return path

    def plot_top_event_responses(
        self,
        n_events=6,
        filename_prefix="07_top_event_response",
    ):
        """
        输出若干个最高权重 event 的单独 cone response（未归一化的原始环）。
        """

        weighted_events = self._collect_weighted_events()

        weighted_events = sorted(
            weighted_events,
            key=lambda item: item[0],
            reverse=True,
        )

        z0 = self._auto_set_image_plane_z()
        x_grid, y_grid, z_grid = self._build_grid_at_z(z0)

        paths = []

        for i, (weight, event) in enumerate(weighted_events[:n_events]):
            response = self._event_cone_response(
                event, x_grid, y_grid, z_grid
            )

            if response is None:
                continue

            pull = getattr(event, "pull_second", np.nan)

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

            if pull is not None and np.isfinite(pull):
                pull_text = f", pull={pull:.2f}"
            else:
                pull_text = ""

            plt.title(
                f"Top event {i}, weight={weight:.3f}, "
                f"type={event.event_type}{pull_text}"
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
        paths.append(self.plot_pull_histogram())
        paths.append(self.plot_accepted_energy_spectrum())
        paths.extend(self.plot_top_event_responses(n_events=6))

        return paths