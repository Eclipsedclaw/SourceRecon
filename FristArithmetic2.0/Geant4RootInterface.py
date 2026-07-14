from typing import Any

import numpy as np
import pandas as pd


class Geant4RootInterface:
    """
    Geant4 ROOT 数据专用接口。

    输出标准 hit_df，列名统一为：

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

    其中：
        true_event_id 是 Geant4 里同一个 gamma 的真实 EventID。
        这是训练 y_match 的核心信息。
    """
    def __init__(
        self,
        root_path,
        tree_name=None,
        branch_map=None,
        energy_unit="MeV",
        position_unit="mm",
    ):
        self.root_path = root_path
        self.tree_name = tree_name
        self.branch_map = branch_map or {}

        self.energy_unit = energy_unit
        self.position_unit = position_unit

        self.file: Any = None
        self.tree: Any = None
        self.hit_df = None

    def load(self):
        try:
            import uproot
        except ImportError:
            raise ImportError(
                "需要安装 uproot 才能读取 ROOT 文件：pip install uproot awkward"
            )

        root_file = uproot.open(self.root_path)
        self.file = root_file

        if self.tree_name is None:
            self.tree_name = self._auto_find_tree_name()

        tree = root_file[self.tree_name]

        if not hasattr(tree, "arrays"):
            raise TypeError(
                f"{self.tree_name} 不是 TTree，不能调用 arrays()。"
            )

        self.tree = tree

        print(f"[Geant4RootInterface] using tree: {self.tree_name}")
        print("[Geant4RootInterface] branches:")
        for b in self.tree.keys():
            print("   ", b)

        self.hit_df = self._build_hit_dataframe()

        return self.hit_df

    def _auto_find_tree_name(self):
        """
        自动寻找第一个 TTree。
        """

        assert self.file is not None, "请先打开 ROOT 文件。"

        for key in self.file.keys():
            obj = self.file[key]

            # uproot TTree 通常有 arrays 和 num_entries
            if hasattr(obj, "arrays") and hasattr(obj, "num_entries"):
                return key

        raise RuntimeError("ROOT 文件中没有找到可读取的 TTree。")

    def _find_branch(self, candidates, required=True):
        """
        在 tree branches 中根据候选名自动找 branch。
        """

        assert self.tree is not None, "请先设置 self.tree。"

        branches = list(self.tree.keys())
        lower_to_real = {b.lower(): b for b in branches}

        # 用户手动指定优先
        for key, value in self.branch_map.items():
            if key in candidates:
                return value

        for cand in candidates:
            cand_lower = cand.lower()
            if cand_lower in lower_to_real:
                return lower_to_real[cand_lower]

        # 模糊包含
        for cand in candidates:
            cand_lower = cand.lower()
            for b in branches:
                if cand_lower in b.lower():
                    return b

        if required:
            raise KeyError(
                "找不到 branch。候选名："
                + str(candidates)
                + "\n当前 branches：\n"
                + "\n".join(branches)
            )

        return None

    def _build_hit_dataframe(self):
        """
        从 ROOT tree 生成标准 hit_df。
        """

        assert self.tree is not None, "请先加载 ROOT tree。"

        event_branch = self._find_branch(
            ["EventID", "eventID", "event_id", "evt", "evtID", "TrackID", "gammaID"]
        )

        energy_branch = self._find_branch(
            ["TotalEnergy", "edep", "Edep", "energy", "Energy", "depEnergy"]
        )

        x_branch = self._find_branch(
            ["pos_x_mm", "x", "X", "posX", "PositionX"]
        )

        y_branch = self._find_branch(
            ["pos_y_mm", "y", "Y", "posY", "PositionY"]
        )

        z_branch = self._find_branch(
            ["z", "Z", "pos_z_mm", "posZ", "PositionZ"]
        )

        layer_branch = self._find_branch(
            ["layer", "Layer", "channel", "Channel", "detectorID", "DetectorID"],
            required=False,
        )

        pixel_branch = self._find_branch(
            ["PixelID", "pixelID", "pixelid", "copyNo", "CopyNo"],
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

        branches_to_read = [
            event_branch,
            energy_branch,
            x_branch,
            y_branch,
            z_branch,
        ]

        optional = [layer_branch, pixel_branch, primary_energy_branch]
        for b in optional:
            if b is not None and b not in branches_to_read:
                branches_to_read.append(b)

        arrays = self.tree.arrays(branches_to_read, library="pd")

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
            df["primary_energy"] = np.nan

        df["channel"] = df["layer"].apply(lambda v: f"ch{int(v)}")

        df = df.reset_index(drop=True)
        df["hit_id"] = df.index.map(lambda i: f"mc_hit_{i}")

        df = df[
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

        return df

    def _infer_layer_from_z(self, z_values):
        """
        如果 ROOT 中没有 layer branch，就按 z 坐标自动分层。

        对三层探测器：
            z 的不同取值通常对应不同 layer。
        """

        unique_z = np.sort(pd.Series(z_values).dropna().unique())

        z_to_layer = {
            z: i
            for i, z in enumerate(unique_z)
        }

        return pd.Series(z_values).map(z_to_layer).astype(int).values

    def print_summary(self):
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