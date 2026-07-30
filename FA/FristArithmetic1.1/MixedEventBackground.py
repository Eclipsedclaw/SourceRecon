# MixedEventBackground.py

import os
import numpy as np
import matplotlib.pyplot as plt

from EventSeparator import EventSeparator
from ThreeHitEvent import ThreeHitEvent


class MixedEventBackground:
    """
    混合事件法（event mixing）估计假组合本底。

    思想：
        故意把来自不同符合窗（不同 final_df 行）的 hit
        拼成 3-hit 组合——这些组合保证是假的。

        算它们的 pull 分布，就得到了"假组合的 pull 模板"。

    用途（全部不需要 MC）：
        1. 与实测 3-hit 的 pull 分布对比：
           0 附近的真信号峰能不能从假组合平台中立起来，
           一张图判定 pull 鉴别路线在该探测器上是否可行；
        2. 定量设置切割阈值：
           给定 |pull| < cut，直接读出假组合的意外通过率；
        3. 估计筛选后样本中的假货污染率。
    """

    def __init__(
        self,
        final_df,
        resolution_model=None,
        channels=("ch0", "ch1", "ch2"),
        min_energy=0.0,
        sigma_delta_cos=0.15,
        n_fake=20000,
        random_seed=42,
        output_dir="figure/mixed_background",
    ):
        """
        参数：
            final_df:
                与真实分析同一份 final_df，
                保证混合本底和真实事件来自同一 hit 总体。

            resolution_model:
                必须与真实分析使用同一个 DetectorResolutionModel，
                否则 pull 不可比。

            n_fake:
                生成的假 3-hit 数量。建议 >= 真实 3-hit 数量的 10 倍。
        """

        self.final_df = final_df
        self.resolution_model = resolution_model
        self.n_fake = n_fake
        self.random_seed = random_seed

        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

        # 复用 EventSeparator 的 hit 提取逻辑，
        # 保证 hit 定义（能量阈值等）与真实分析完全一致。
        self._separator = EventSeparator(
            final_df=final_df,
            channels=channels,
            min_energy=min_energy,
            sigma_delta_cos=sigma_delta_cos,
            resolution_model=resolution_model,
        )

        self.fake_events = []

    # ============================================================
    # 1. 构建假事件
    # ============================================================

    def build(self):
        """
        生成假 3-hit 事件。

        做法：
            ch0 池、ch1 池、ch2 池各随机抽一个 hit，
            要求三个 hit 来自三个不同的 final_df 行
            （即三个不同的符合窗，保证组合必假）。

        返回：
            fake_events: list[ThreeHitEvent]
        """

        pools = {0: [], 1: [], 2: []}

        for row_index, row in self._separator.final_df.iterrows():
            hits = self._separator.extract_hits_from_row(row)

            for hit in hits:
                pools[hit["layer"]].append((row_index, hit))

        for layer, pool in pools.items():
            if len(pool) == 0:
                raise ValueError(
                    f"layer {layer} 的 hit 池为空，无法构建混合本底。"
                )

        rng = np.random.default_rng(self.random_seed)

        self.fake_events = []

        max_attempts = self.n_fake * 10
        attempts = 0

        while len(self.fake_events) < self.n_fake and attempts < max_attempts:
            attempts += 1

            i0 = rng.integers(len(pools[0]))
            i1 = rng.integers(len(pools[1]))
            i2 = rng.integers(len(pools[2]))

            row0, hit0 = pools[0][i0]
            row1, hit1 = pools[1][i1]
            row2, hit2 = pools[2][i2]

            # 三个 hit 必须来自三个不同的符合窗
            if len({row0, row1, row2}) < 3:
                continue

            fake = ThreeHitEvent(
                event_id="mixed",
                hit1=hit0,
                hit2=hit1,
                hit3=hit2,
                resolution_model=self.resolution_model,
            )

            self.fake_events.append(fake)

        print(
            f"MixedEventBackground: 生成假 3-hit {len(self.fake_events)} 个 "
            f"(尝试 {attempts} 次)"
        )

        return self.fake_events

    # ============================================================
    # 2. 提取 pull
    # ============================================================

    def get_fake_pulls(self):
        """
        返回所有假事件中有限的 pull 值。
        """

        pulls = []

        for event in self.fake_events:
            pull = event.pull_second

            if pull is None or not np.isfinite(pull):
                continue

            pulls.append(pull)

        return np.array(pulls)

    @staticmethod
    def get_real_pulls(event_list):
        """
        从真实 EventList 中提取所有 3-hit 的有限 pull 值。
        """

        pulls = []

        for event in event_list.events:
            if getattr(event, "n_hits", None) != 3:
                continue

            pull = getattr(event, "pull_second", None)

            if pull is None or not np.isfinite(pull):
                continue

            pulls.append(pull)

        return np.array(pulls)

    # ============================================================
    # 3. 通过率
    # ============================================================

    def estimate_pass_fraction(self, pulls, cut):
        """
        |pull| < cut 的通过比例。
        """

        if len(pulls) == 0:
            return np.nan

        return float(np.mean(np.abs(pulls) < cut))

    # ============================================================
    # 4. 诊断图
    # ============================================================

    def plot_comparison(
        self,
        event_list,
        pull_range=(-8.0, 8.0),
        n_bins=100,
        filename="pull_real_vs_mixed.png",
    ):
        """
        核心诊断图：实测 3-hit pull 分布 vs 混合本底 pull 分布。

        两个分布都归一化成密度。

        判读：
            实测分布 = 真信号(0 附近正态峰) + 假组合平台。
            混合本底给出平台的形状。
            峰能立起来 → pull 鉴别路线可行；
            实测和混合完全重合 → 数据里几乎没有可用的真 3-hit。
        """

        if len(self.fake_events) == 0:
            self.build()

        real_pulls = self.get_real_pulls(event_list)
        fake_pulls = self.get_fake_pulls()

        plt.figure(figsize=(8, 5))

        bins = np.linspace(pull_range[0], pull_range[1], n_bins)

        if len(real_pulls) > 0:
            plt.hist(
                np.clip(real_pulls, *pull_range),
                bins=bins,
                density=True,
                alpha=0.6,
                label=f"real 3-hit (n={len(real_pulls)})",
            )

        if len(fake_pulls) > 0:
            plt.hist(
                np.clip(fake_pulls, *pull_range),
                bins=bins,
                density=True,
                histtype="step",
                linewidth=1.8,
                color="crimson",
                label=f"mixed fake (n={len(fake_pulls)})",
            )

        plt.axvline(-2.0, color="gray", linestyle="--", linewidth=0.8)
        plt.axvline(2.0, color="gray", linestyle="--", linewidth=0.8)

        plt.xlabel("pull = delta_cos_second / sigma_delta")
        plt.ylabel("density")
        plt.title("3-hit Pull: Real Data vs Mixed-Event Background")
        plt.legend()

        path = os.path.join(self.output_dir, filename)
        plt.tight_layout()
        plt.savefig(path, dpi=200)
        plt.close()

        return path

    def plot_pass_rate_scan(
        self,
        event_list,
        cuts=None,
        filename="pull_cut_scan.png",
    ):
        """
        扫描切割阈值：
            对一系列 |pull| < cut，
            画实测通过率与混合本底通过率两条曲线。

        用法：
            选一个"实测通过率明显高于本底通过率"的 cut，
            两条曲线的差值近似正比于净信号量。
        """

        if len(self.fake_events) == 0:
            self.build()

        if cuts is None:
            cuts = np.linspace(0.25, 5.0, 20)

        real_pulls = self.get_real_pulls(event_list)
        fake_pulls = self.get_fake_pulls()

        real_rates = [
            self.estimate_pass_fraction(real_pulls, c) for c in cuts
        ]
        fake_rates = [
            self.estimate_pass_fraction(fake_pulls, c) for c in cuts
        ]

        plt.figure(figsize=(8, 5))
        plt.plot(cuts, real_rates, marker="o", label="real 3-hit pass rate")
        plt.plot(cuts, fake_rates, marker="s", label="mixed fake pass rate")

        plt.xlabel("|pull| cut")
        plt.ylabel("pass fraction")
        plt.title("Pass Rate vs Pull Cut")
        plt.legend()
        plt.grid(alpha=0.3)

        path = os.path.join(self.output_dir, filename)
        plt.tight_layout()
        plt.savefig(path, dpi=200)
        plt.close()

        return path

    def print_summary(self, event_list, cuts=(1.0, 2.0, 3.0)):
        """
        打印若干典型切割下的通过率对比。
        """

        if len(self.fake_events) == 0:
            self.build()

        real_pulls = self.get_real_pulls(event_list)
        fake_pulls = self.get_fake_pulls()

        print("========== Mixed-Event Background Summary ==========")
        print(f"real 3-hit (finite pull) : {len(real_pulls)}")
        print(f"mixed fake (finite pull) : {len(fake_pulls)}")

        for cut in cuts:
            r = self.estimate_pass_fraction(real_pulls, cut)
            f = self.estimate_pass_fraction(fake_pulls, cut)
            print(
                f"|pull| < {cut:.1f} : real pass = {r:.3f} | "
                f"fake pass = {f:.3f}"
            )

        print("====================================================")