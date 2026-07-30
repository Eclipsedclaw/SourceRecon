# Geant4RootInterface.py

from typing import Any

import numpy as np
import pandas as pd


class Geant4RootInterface:
    """
    Geant4 ROOT 数据专用接口。

    作用：
        读取 Geant4 .root 文件，把 step-level 数据转换成 hit-level dataframe。

    最终输出 hit_df 的标准列：

        true_event_id
        hit_id
        layer
        channel
        pixelid
        x
        y
        z
        energy
        primary_energy

    重要说明：
        你的 ROOT 文件中每一行更像是 Geant4 step，而不是最终 detector hit。

        所以本接口会做两件重要处理：

        1. 删除 eDep_MeV = 0 的 step
        2. 把同一个 true_event_id + layer + pixelid 的多个 step 合并成一个 hit

    其中：
        true_event_id 来自 Geant4 eventID。
        它表示同一条 gamma 的真实 event 编号，是训练 y_match 的核心 truth 信息。
    """

    def __init__(
        self,
        root_path,
        tree_name=None,
        branch_map=None,
        energy_unit="MeV",
        position_unit="mm",
        fixed_primary_energy_mev=None,
        n_layers=3,
    ):
        """
        参数
        ----
        root_path:
            ROOT 文件路径。

        tree_name:
            TTree 名字。
            如果为 None，则自动寻找第一个 TTree。

        branch_map:
            ROOT branch 名字映射。
            例如：
                {
                    "EventID": "eventID",
                    "TotalEnergy": "eDep_MeV",
                    "pos_x_mm": "x_post",
                    "pos_y_mm": "y_post",
                    "z": "z_post",
                    "PixelID": "pixelID",
                }

        energy_unit:
            能量单位，默认 MeV。

        position_unit:
            位置单位，默认 mm。

        fixed_primary_energy_mev:
            如果 ROOT 中没有 primary energy branch，
            但你的 Geant4 源是单能 gamma，可以在这里手动指定。

            例如 662 keV：
                fixed_primary_energy_mev=0.662

            如果为 None，则 primary_energy 填 NaN。

        n_layers:
            探测器层数。你的相机是三层，所以默认 3。
        """

        self.root_path = root_path
        self.tree_name = tree_name
        self.branch_map = branch_map or {}

        self.energy_unit = energy_unit
        self.position_unit = position_unit

        self.fixed_primary_energy_mev = fixed_primary_energy_mev
        self.n_layers = n_layers

        self.file: Any = None
        self.tree: Any = None
        self.hit_df = None

    # ============================================================
    # public API
    # ============================================================

    def load(self):
        """
        打开 ROOT 文件，读取 tree，生成标准 hit_df。
        """

        try:
            import uproot
        except ImportError:
            raise ImportError(
                "需要安装 uproot 才能读取 ROOT 文件：pip install uproot awkward"
            )

        root_file: Any = uproot.open(self.root_path)
        self.file = root_file

        if self.tree_name is None:
            self.tree_name = self._auto_find_tree_name()

        tree: Any = root_file[self.tree_name]

        if not hasattr(tree, "arrays"):
            raise TypeError(
                str(self.tree_name) + " 不是 TTree，不能调用 arrays()。"
            )

        self.tree = tree

        print("[Geant4RootInterface] using tree:", self.tree_name)
        print("[Geant4RootInterface] branches:")
        for b in self.tree.keys():
            print("   ", b)

        self.hit_df = self._build_hit_dataframe()

        return self.hit_df

    def print_summary(self):
        """
        打印 hit_df 简要信息。
        """

        if self.hit_df is None:
            raise RuntimeError("请先调用 load()。")

        print("========== Geant4 ROOT Summary ==========")
        print("hit number:", len(self.hit_df))
        print("true event number:", self.hit_df["true_event_id"].nunique())
        print()
        print("layers:")
        print(self.hit_df["layer"].value_counts().sort_index())
        print()
        print("head:")
        print(self.hit_df.head())
        print("=========================================")

    # ============================================================
    # tree / branch helper
    # ============================================================

    def _auto_find_tree_name(self):
        """
        自动寻找 ROOT 文件中的第一个 TTree。
        """

        assert self.file is not None, "请先打开 ROOT 文件。"

        for key in self.file.keys():
            obj = self.file[key]

            if hasattr(obj, "arrays") and hasattr(obj, "num_entries"):
                return key

        raise RuntimeError("ROOT 文件中没有找到可读取的 TTree。")

    def _find_branch(self, candidates, required=True):
        """
        在 ROOT tree branches 中，根据候选名自动找 branch。

        优先级：
            1. branch_map 手动指定
            2. 完全匹配，忽略大小写
            3. 模糊包含匹配
        """

        assert self.tree is not None, "请先设置 self.tree。"

        branches = list(self.tree.keys())
        lower_to_real = {}

        for b in branches:
            lower_to_real[b.lower()] = b

        # 1. 用户手动指定优先
        for key in candidates:
            if key in self.branch_map:
                mapped_name = self.branch_map[key]

                if mapped_name not in branches:
                    raise KeyError(
                        "branch_map 指定的 branch 不存在："
                        + str(mapped_name)
                        + "\n当前 ROOT branches:\n"
                        + "\n".join(branches)
                    )

                return mapped_name

        # 2. 完全匹配，忽略大小写
        for cand in candidates:
            cand_lower = cand.lower()
            if cand_lower in lower_to_real:
                return lower_to_real[cand_lower]

        # 3. 模糊包含匹配
        for cand in candidates:
            cand_lower = cand.lower()

            for b in branches:
                if cand_lower in b.lower():
                    return b

        if required:
            raise KeyError(
                "找不到 branch。候选名："
                + str(candidates)
                + "\n当前 ROOT branches:\n"
                + "\n".join(branches)
            )

        return None

    # ============================================================
    # main dataframe builder
    # ============================================================

    def _build_hit_dataframe(self):
        """
        从 ROOT tree 生成标准 hit_df。

        你的 ROOT 文件每一行是 Geant4 step。
        后续算法需要的是 detector hit。

        因此这里会：

            1. 读取 step-level 数据；
            2. 如果没有 layer branch，用 z 坐标聚成三层；
            3. 删除 energy = 0 的 step；
            4. 按 true_event_id + layer + pixelid 合并 step；
            5. 输出 hit-level dataframe。
        """

        assert self.tree is not None, "请先加载 ROOT tree。"

        # ========================================================
        # 1. 找 branch
        # ========================================================

        event_branch = self._find_branch(
            [
                "EventID",
                "eventID",
                "event_id",
                "evt",
                "evtID",
                "gammaID",
            ]
        )

        energy_branch = self._find_branch(
            [
                "TotalEnergy",
                "edep",
                "Edep",
                "eDep_MeV",
                "energy",
                "Energy",
                "depEnergy",
            ]
        )

        x_branch = self._find_branch(
            [
                "pos_x_mm",
                "x_post",
                "x_pre",
                "x",
                "X",
                "posX",
                "PositionX",
            ]
        )

        y_branch = self._find_branch(
            [
                "pos_y_mm",
                "y_post",
                "y_pre",
                "y",
                "Y",
                "posY",
                "PositionY",
            ]
        )

        z_branch = self._find_branch(
            [
                "z",
                "Z",
                "z_post",
                "z_pre",
                "pos_z_mm",
                "posZ",
                "PositionZ",
            ]
        )

        layer_branch = self._find_branch(
            [
                "layer",
                "Layer",
                "channel",
                "Channel",
                "detectorID",
                "DetectorID",
            ],
            required=False,
        )

        pixel_branch = self._find_branch(
            [
                "PixelID",
                "pixelID",
                "pixelid",
                "copyNo",
                "CopyNo",
            ],
            required=False,
        )

        primary_energy_branch = self._find_branch(
            [
                "PrimaryEnergy",
                "primary_energy",
                "E0",
                "gammaEnergy",
                "GammaEnergy",
                "sourceEnergy",
            ],
            required=False,
        )

        print("[Geant4RootInterface] selected branches:")
        print("    event branch        :", event_branch)
        print("    energy branch       :", energy_branch)
        print("    x branch            :", x_branch)
        print("    y branch            :", y_branch)
        print("    z branch            :", z_branch)
        print("    layer branch        :", layer_branch)
        print("    pixel branch        :", pixel_branch)
        print("    primary energy      :", primary_energy_branch)

        # ========================================================
        # 2. 读取 ROOT branch
        # ========================================================

        branches_to_read = [
            event_branch,
            energy_branch,
            x_branch,
            y_branch,
            z_branch,
        ]

        optional_branches = [
            layer_branch,
            pixel_branch,
            primary_energy_branch,
        ]

        for b in optional_branches:
            if b is not None and b not in branches_to_read:
                branches_to_read.append(b)

        arrays = self.tree.arrays(branches_to_read, library="pd")

        # ========================================================
        # 3. 先生成 step-level dataframe
        # ========================================================

        df = pd.DataFrame()

        df["true_event_id"] = arrays[event_branch].values
        df["energy"] = arrays[energy_branch].astype(float).values
        df["x"] = arrays[x_branch].astype(float).values
        df["y"] = arrays[y_branch].astype(float).values
        df["z"] = arrays[z_branch].astype(float).values

        if layer_branch is not None:
            df["layer"] = arrays[layer_branch].astype(int).values
        else:
            df["layer"] = self._infer_layer_from_z(df["z"])

        if pixel_branch is not None:
            df["pixelid"] = arrays[pixel_branch].values
        else:
            df["pixelid"] = np.arange(len(df))

        if primary_energy_branch is not None:
            df["primary_energy"] = arrays[primary_energy_branch].astype(float).values
        else:
            if self.fixed_primary_energy_mev is not None:
                df["primary_energy"] = float(self.fixed_primary_energy_mev)
            else:
                df["primary_energy"] = np.nan

        # ========================================================
        # 4. 删除 eDep = 0 的 step
        # ========================================================

        before_filter = len(df)

        df = df[df["energy"] > 0.0].copy()

        after_filter = len(df)

        print(
            "[Geant4RootInterface] remove zero-energy steps:",
            before_filter,
            "->",
            after_filter,
        )

        if len(df) == 0:
            raise RuntimeError(
                "过滤 energy > 0 后没有剩余 hit。请检查能量 branch 是否选错。"
            )

        # ========================================================
        # 5. 把 step 聚合成 detector hit
        # ========================================================
        #
        # 同一个 true_event_id + layer + pixelid 的多个 step
        # 应该合并成一个 hit。
        #
        # energy:
        #     求和
        #
        # x, y, z:
        #     能量加权平均
        # ========================================================

        group_cols = ["true_event_id", "layer", "pixelid"]

        rows = []

        for group_key, group in df.groupby(group_cols):
            true_event_id, layer, pixelid = group_key

            energies = group["energy"].values.astype(float)
            energy_sum = float(np.sum(energies))

            x_values = group["x"].values.astype(float)
            y_values = group["y"].values.astype(float)
            z_values = group["z"].values.astype(float)

            if energy_sum > 0:
                x_mean = float(np.sum(x_values * energies) / energy_sum)
                y_mean = float(np.sum(y_values * energies) / energy_sum)
                z_mean = float(np.sum(z_values * energies) / energy_sum)
            else:
                x_mean = float(np.mean(x_values))
                y_mean = float(np.mean(y_values))
                z_mean = float(np.mean(z_values))

            primary_values = group["primary_energy"].dropna().values

            if len(primary_values) > 0:
                primary_energy = float(primary_values[0])
            else:
                primary_energy = np.nan

            rows.append(
                {
                    "true_event_id": true_event_id,
                    "layer": int(layer),
                    "pixelid": pixelid,
                    "x": x_mean,
                    "y": y_mean,
                    "z": z_mean,
                    "energy": energy_sum,
                    "primary_energy": primary_energy,
                }
            )

        hit_df = pd.DataFrame(rows)

        print(
            "[Geant4RootInterface] merge steps to hits:",
            after_filter,
            "->",
            len(hit_df),
        )

        # ========================================================
        # 6. 补充 channel 和 hit_id
        # ========================================================

        hit_df["channel"] = hit_df["layer"].apply(
            lambda v: "ch" + str(int(v))
        )

        hit_df = hit_df.reset_index(drop=True)

        hit_df["hit_id"] = hit_df.index.map(
            lambda i: "mc_hit_" + str(i)
        )

        # ========================================================
        # 7. 整理列顺序
        # ========================================================

        hit_df = hit_df[
            [
                "true_event_id",
                "hit_id",
                "layer",
                "channel",
                "pixelid",
                "x",
                "y",
                "z",
                "energy",
                "primary_energy",
            ]
        ]

        return hit_df

    # ============================================================
    # layer inference
    # ============================================================

    def _infer_layer_from_z(self, z_values, n_layers=None):
        """
        如果 ROOT 中没有明确的 layer branch，就根据 z 坐标自动聚类成 n_layers 层。

        不能直接用 unique z 分层，因为 Geant4 step 的 z_post / z_pre 往往是连续值。
        """

        if n_layers is None:
            n_layers = self.n_layers

        # 强制转成普通 numpy float array，避免 Pylance / pandas ExtensionArray 报错
        z_array = np.asarray(z_values, dtype=float)

        # 去掉 NaN
        valid_mask = ~np.isnan(z_array)
        valid_z = z_array[valid_mask]

        if len(valid_z) == 0:
            raise ValueError("z_values 全是 NaN，无法根据 z 推断 layer。")

        # 用分位数初始化 n_layers 个中心
        percent_points = np.linspace(0.0, 100.0, n_layers)
        centers = np.percentile(valid_z, percent_points)
        centers = np.asarray(centers, dtype=float)

        labels = np.zeros(len(z_array), dtype=int)

        # 简单一维 k-means
        for _ in range(50):
            valid_distances = np.abs(valid_z[:, None] - centers[None, :])
            valid_labels = np.argmin(valid_distances, axis=1)

            new_centers = []

            for i in range(n_layers):
                if np.any(valid_labels == i):
                    new_centers.append(np.mean(valid_z[valid_labels == i]))
                else:
                    new_centers.append(centers[i])

            new_centers = np.asarray(new_centers, dtype=float)

            if np.allclose(new_centers, centers):
                break

            centers = new_centers

        valid_distances = np.abs(valid_z[:, None] - centers[None, :])
        valid_labels = np.argmin(valid_distances, axis=1)

        labels[valid_mask] = valid_labels
        labels[~valid_mask] = 0

        # 按 z 从小到大重新编号：
        # 最小 z -> layer 0
        # 中间 z -> layer 1
        # 最大 z -> layer 2
        order = np.argsort(centers)

        remap = {}
        for new_label, old_label in enumerate(order):
            remap[int(old_label)] = int(new_label)

        mapped_labels = np.array(
            [remap[int(label)] for label in labels],
            dtype=int,
        )

        print("[Geant4RootInterface] inferred z-layer centers:")
        for old_label in order:
            print(
                "    layer "
                + str(remap[int(old_label)])
                + ": z center = "
                + format(float(centers[int(old_label)]), ".3f")
                + " mm"
            )

        return mapped_labels