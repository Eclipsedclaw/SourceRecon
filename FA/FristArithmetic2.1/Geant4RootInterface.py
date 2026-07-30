from typing import Any

import numpy as np
import pandas as pd


class Geant4RootInterface:
    """Read Geant4 step data and build detector hits plus training-only truth.

    ``hit_df`` contains only quantities that can also exist in real data.
    Geant4-only information, including the primary energy, is kept in
    ``event_truth_df`` and must never be used by the scorer as an input feature.
    """

    DEFAULT_CHAMBER_TO_LAYER = {
        0: 0,  # chamber 0 -> ch2, YSO, first scatter layer
        1: 1,  # ch1, YSO, second scatter layer
        2: 2,  # chamber 2 -> ch0, LYSO, absorber
    }

    DEFAULT_LAYER_GEOMETRY = {
        0: {
            "channel": "ch2",
            "material": "YSO",
            "thickness_mm": 3.0,
            "bottom_offset_mm": 0.0,
        },
        1: {
            "channel": "ch1",
            "material": "YSO",
            "thickness_mm": 3.0,
            "bottom_offset_mm": 25.0,
        },
        2: {
            "channel": "ch0",
            "material": "LYSO",
            "thickness_mm": 6.0,
            "bottom_offset_mm": 60.0,
        },
    }

    def __init__(
        self,
        root_path,
        tree_name=None,
        branch_map=None,
        energy_unit="MeV",
        position_unit="mm",
        fixed_primary_energy_mev=None,
        primary_energy_mode="none",
        chamber_to_layer=None,
        layer_geometry=None,
        energy_tolerance_mev=0.03,
        strict_layer_assignment=True,
    ):
        self.root_path = root_path
        self.tree_name = tree_name
        self.branch_map = branch_map or {}
        self.energy_unit = energy_unit
        self.position_unit = position_unit

        # This value is training truth only. It is kept in event_truth_df and
        # is never copied into hit_df or scorer features.
        self.fixed_primary_energy_mev = fixed_primary_energy_mev
        self.primary_energy_mode = primary_energy_mode
        self.energy_tolerance_mev = energy_tolerance_mev

        self.chamber_to_layer = dict(
            chamber_to_layer or self.DEFAULT_CHAMBER_TO_LAYER
        )
        self.layer_geometry = dict(
            layer_geometry or self.DEFAULT_LAYER_GEOMETRY
        )
        self.strict_layer_assignment = strict_layer_assignment

        self.file: Any = None
        self.tree: Any = None
        self.step_df = None
        self.hit_df = None
        self.event_truth_df = None
        self.geometry_summary_df = None
        self.primary_energy_source_by_event = {}

    def load(self):
        try:
            import uproot
        except ImportError:
            raise ImportError(
                "需要安装 uproot 才能读取 ROOT 文件：pip install uproot awkward"
            )

        self.file = uproot.open(self.root_path)
        if self.tree_name is None:
            self.tree_name = self._auto_find_tree_name()

        self.tree = self.file[self.tree_name]
        if not hasattr(self.tree, "arrays"):
            raise TypeError(str(self.tree_name) + " 不是可读取的 TTree。")

        print("[Geant4RootInterface] using tree:", self.tree_name)
        print("[Geant4RootInterface] branches:")
        for branch in self.tree.keys():
            print("   ", branch)

        self.hit_df = self._build_hit_dataframe()
        return self.hit_df

    def get_event_truth_df(self):
        if self.event_truth_df is None:
            raise RuntimeError("请先调用 load()。")
        return self.event_truth_df.copy()

    def get_step_df(self):
        if self.step_df is None:
            raise RuntimeError("请先调用 load()。")
        return self.step_df.copy()

    def print_summary(self):
        if self.hit_df is None:
            raise RuntimeError("请先调用 load()。")

        print("========== Geant4 ROOT Summary ==========")
        print("hit number:", len(self.hit_df))
        print("true event number:", self.hit_df["true_event_id"].nunique())
        print("layers:")
        print(self.hit_df["layer"].value_counts().sort_index())
        print("geometry QA:")
        print(self.geometry_summary_df)
        if self.event_truth_df is not None:
            inferred = self.event_truth_df["primary_energy"].dropna()
            print("events with inferred primary energy:", len(inferred))
            if len(inferred) > 0:
                print(inferred.describe())
        print("head:")
        print(self.hit_df.head())
        print("=========================================")

    def _auto_find_tree_name(self):
        for key in self.file.keys():
            obj = self.file[key]
            if hasattr(obj, "arrays") and hasattr(obj, "num_entries"):
                return key
        raise RuntimeError("ROOT 文件中没有找到可读取的 TTree。")

    def _find_branch(self, candidates, required=True):
        branches = list(self.tree.keys())
        lower_to_real = {branch.lower(): branch for branch in branches}

        for key in candidates:
            if key in self.branch_map:
                mapped_name = self.branch_map[key]
                if mapped_name not in branches:
                    raise KeyError(
                        "branch_map 指定的 branch 不存在："
                        + str(mapped_name)
                    )
                return mapped_name

        for candidate in candidates:
            if candidate.lower() in lower_to_real:
                return lower_to_real[candidate.lower()]

        for candidate in candidates:
            for branch in branches:
                if candidate.lower() in branch.lower():
                    return branch

        if required:
            raise KeyError(
                "找不到 branch。候选名："
                + str(candidates)
                + "\n当前 ROOT branches:\n"
                + "\n".join(branches)
            )
        return None

    def _build_hit_dataframe(self):
        event_branch = self._find_branch(
            ["EventID", "eventID", "event_id", "evtID", "gammaID"]
        )
        energy_branch = self._find_branch(
            ["TotalEnergy", "eDep_MeV", "edep", "Edep", "depEnergy"]
        )
        x_branch = self._find_branch(
            ["pos_x_mm", "x_post", "x_pre", "PositionX"]
        )
        y_branch = self._find_branch(
            ["pos_y_mm", "y_post", "y_pre", "PositionY"]
        )
        z_branch = self._find_branch(
            ["z", "z_post", "z_pre", "pos_z_mm", "PositionZ"]
        )
        chamber_branch = self._find_branch(
            ["ChamberID", "chamberID", "chamber_id"], required=False
        )
        explicit_layer_branch = self._find_branch(
            ["layer", "Layer", "layerID", "LayerID"], required=False
        )
        pixel_branch = self._find_branch(
            ["PixelID", "pixelID", "pixelid", "copyNo"], required=False
        )
        primary_energy_branch = self._find_branch(
            ["PrimaryEnergy", "primary_energy", "E0", "gammaEnergy"],
            required=False,
        )
        kinetic_branch = self._find_branch(
            ["kineticEnergy_MeV", "kinetic_energy"], required=False
        )
        track_branch = self._find_branch(["trackID", "TrackID"], required=False)
        step_branch = self._find_branch(["stepID", "StepID"], required=False)
        parent_branch = self._find_branch(
            ["parentID", "ParentID"], required=False
        )
        time_branch = self._find_branch(["time_ns", "globalTime"], required=False)
        particle_branch = self._find_branch(
            ["particleName", "ParticleName"], required=False
        )

        selected = {
            "event": event_branch,
            "energy": energy_branch,
            "x": x_branch,
            "y": y_branch,
            "z": z_branch,
            "chamber": chamber_branch,
            "layer": explicit_layer_branch,
            "pixel": pixel_branch,
            "primary_energy": primary_energy_branch,
            "kinetic_energy": kinetic_branch,
            "track": track_branch,
            "step": step_branch,
            "parent": parent_branch,
            "time": time_branch,
            "particle": particle_branch,
        }
        print("[Geant4RootInterface] selected branches:")
        for name, branch in selected.items():
            print("    " + name.ljust(18) + ":", branch)

        branches_to_read = []
        for branch in selected.values():
            if branch is not None and branch not in branches_to_read:
                branches_to_read.append(branch)
        # NumPy mode also handles string branches such as particleName and
        # avoids uproot's optional awkward-pandas dependency.
        arrays = self.tree.arrays(
            branches_to_read,
            library="np",
            how=dict,
        )

        df = pd.DataFrame()
        df["true_event_id"] = np.asarray(arrays[event_branch])
        df["energy"] = np.asarray(arrays[energy_branch], dtype=float)
        df["x"] = np.asarray(arrays[x_branch], dtype=float)
        df["y"] = np.asarray(arrays[y_branch], dtype=float)
        df["z"] = np.asarray(arrays[z_branch], dtype=float)

        if chamber_branch is not None:
            df["chamberid"] = np.asarray(arrays[chamber_branch], dtype=int)
            unknown = sorted(
                set(df["chamberid"].unique()) - set(self.chamber_to_layer.keys())
            )
            if unknown:
                raise ValueError(
                    "chamber_to_layer 缺少 chamberID：" + str(unknown)
                )
            df["layer"] = df["chamberid"].map(self.chamber_to_layer).astype(int)
        elif explicit_layer_branch is not None:
            df["layer"] = np.asarray(
                arrays[explicit_layer_branch],
                dtype=int,
            )
            df["chamberid"] = np.nan
        elif self.strict_layer_assignment:
            raise RuntimeError(
                "ROOT 中没有 chamberID/layer，正式流程禁止使用 z k-means 分层。"
            )
        else:
            raise RuntimeError(
                "无法确定 layer。请提供 chamberID 或显式 layer branch。"
            )

        if pixel_branch is not None:
            df["pixelid"] = np.asarray(arrays[pixel_branch])
        else:
            df["pixelid"] = np.arange(len(df))

        optional_columns = [
            ("track_id", track_branch, float),
            ("step_id", step_branch, float),
            ("parent_id", parent_branch, float),
            ("time_ns", time_branch, float),
            ("kinetic_energy", kinetic_branch, float),
        ]
        for column, branch, dtype in optional_columns:
            if branch is None:
                df[column] = np.nan
            else:
                df[column] = np.asarray(arrays[branch], dtype=dtype)

        if particle_branch is None:
            df["particle_name"] = None
        else:
            df["particle_name"] = np.asarray(arrays[particle_branch])

        if primary_energy_branch is None:
            df["primary_energy_branch"] = np.nan
        else:
            df["primary_energy_branch"] = np.asarray(
                arrays[primary_energy_branch],
                dtype=float,
            )

        self.geometry_summary_df = self._build_geometry_summary(df)
        self._validate_geometry_summary()

        # Infer primary energy before removing zero-deposition rows. Primary
        # gamma transport steps often have eDep=0 but still carry the initial
        # kinetic-energy truth needed for supervised labels.
        primary_by_event = self._infer_primary_energy_by_event(df)

        before_filter = len(df)
        df = df[df["energy"] > 0.0].copy()
        print(
            "[Geant4RootInterface] remove zero-energy steps:",
            before_filter,
            "->",
            len(df),
        )
        if len(df) == 0:
            raise RuntimeError("过滤 energy > 0 后没有剩余 step。")

        self.step_df = df.reset_index(drop=True)

        rows = []
        group_cols = ["true_event_id", "layer", "pixelid"]
        for group_key, group in self.step_df.groupby(group_cols, sort=False):
            true_event_id, layer, pixelid = group_key
            energies = group["energy"].to_numpy(dtype=float)
            energy_sum = float(np.sum(energies))

            def weighted_mean(column):
                values = group[column].to_numpy(dtype=float)
                return float(np.sum(values * energies) / energy_sum)

            chamber_values = group["chamberid"].dropna()
            first_time_values = group["time_ns"].dropna()
            first_step_values = group["step_id"].dropna()

            rows.append(
                {
                    "true_event_id": true_event_id,
                    "layer": int(layer),
                    "channel": self.layer_geometry[int(layer)]["channel"],
                    "material": self.layer_geometry[int(layer)]["material"],
                    "chamberid": (
                        int(chamber_values.iloc[0])
                        if len(chamber_values) else np.nan
                    ),
                    "pixelid": pixelid,
                    "x": weighted_mean("x"),
                    "y": weighted_mean("y"),
                    "z": weighted_mean("z"),
                    "energy": energy_sum,
                    "first_time_ns": (
                        float(first_time_values.min())
                        if len(first_time_values) else np.nan
                    ),
                    "first_step_id": (
                        float(first_step_values.min())
                        if len(first_step_values) else np.nan
                    ),
                    "n_steps": int(len(group)),
                }
            )

        hit_df = pd.DataFrame(rows).reset_index(drop=True)
        hit_df["hit_id"] = hit_df.index.map(lambda i: "mc_hit_" + str(i))

        step_energy = float(self.step_df["energy"].sum())
        hit_energy = float(hit_df["energy"].sum())
        if not np.isclose(step_energy, hit_energy, rtol=1e-10, atol=1e-12):
            raise RuntimeError("step-to-hit 聚合前后能量不守恒。")

        self.event_truth_df = self._build_event_truth_df(
            hit_df,
            primary_by_event,
        )

        columns = [
            "true_event_id",
            "hit_id",
            "layer",
            "channel",
            "material",
            "chamberid",
            "pixelid",
            "x",
            "y",
            "z",
            "energy",
            "first_time_ns",
            "first_step_id",
            "n_steps",
        ]
        print(
            "[Geant4RootInterface] merge steps to hits:",
            len(self.step_df),
            "->",
            len(hit_df),
        )
        return hit_df[columns]

    def _build_geometry_summary(self, df):
        rows = []
        if "chamberid" not in df.columns:
            return pd.DataFrame()
        for chamberid, group in df.dropna(subset=["chamberid"]).groupby("chamberid"):
            z_values = group["z"].dropna().astype(float)
            if len(z_values) == 0:
                continue
            layer = self.chamber_to_layer[int(chamberid)]
            rows.append(
                {
                    "chamberid": int(chamberid),
                    "layer": int(layer),
                    "channel": self.layer_geometry[int(layer)]["channel"],
                    "material": self.layer_geometry[int(layer)]["material"],
                    "n_steps": int(len(group)),
                    "z_min": float(z_values.min()),
                    "z_q01": float(z_values.quantile(0.01)),
                    "z_median": float(z_values.median()),
                    "z_q99": float(z_values.quantile(0.99)),
                    "z_max": float(z_values.max()),
                }
            )
        return pd.DataFrame(rows).sort_values("layer").reset_index(drop=True)

    def _validate_geometry_summary(self):
        summary = self.geometry_summary_df
        if summary is None or len(summary) == 0:
            return
        observed_layers = set(summary["layer"].astype(int))
        if observed_layers != {0, 1, 2}:
            raise ValueError(
                "几何 QA 未观察到完整的 layer {0,1,2}，实际为："
                + str(sorted(observed_layers))
            )

        medians = summary.sort_values("layer")["z_median"].to_numpy(float)
        if not (medians[0] < medians[1] < medians[2]):
            raise ValueError(
                "layer 的 z 顺序与本项目几何不符：应满足 "
                "ch2/layer0 < ch1/layer1 < ch0/layer2。实际中位数="
                + str(medians.tolist())
            )

    def _infer_primary_energy_by_event(self, df):
        if self.primary_energy_mode not in (
            "infer_truth",
            "branch",
            "fixed",
            "none",
        ):
            raise ValueError("未知 primary_energy_mode：" + str(self.primary_energy_mode))

        result = {}
        sources = {}
        for event_id, group in df.groupby("true_event_id", sort=False):
            energy = np.nan
            source = "missing"

            if self.primary_energy_mode == "fixed":
                if self.fixed_primary_energy_mev is None:
                    raise ValueError(
                        "primary_energy_mode='fixed' 时必须提供 "
                        "fixed_primary_energy_mev。"
                    )
                energy = float(self.fixed_primary_energy_mev)
                source = "fixed_dataset_truth"

            if np.isnan(energy) and self.primary_energy_mode in (
                "branch",
                "infer_truth",
            ):
                branch_values = group["primary_energy_branch"].dropna()
                if len(branch_values) > 0:
                    energy = float(branch_values.iloc[0])
                    source = "root_primary_energy_branch"

            if np.isnan(energy) and self.primary_energy_mode == "infer_truth":
                primary = group.copy()
                if primary["parent_id"].notna().any():
                    primary = primary[primary["parent_id"] == 0]
                if primary["particle_name"].notna().any():
                    names = primary["particle_name"].astype(str).str.lower()
                    gamma_rows = primary[names.str.contains("gamma", na=False)]
                    if len(gamma_rows) > 0:
                        primary = gamma_rows
                kinetic = primary["kinetic_energy"].dropna().astype(float)
                if len(kinetic) > 0:
                    # Diagnostic fallback only. kineticEnergy_MeV is the
                    # particle's step-level kinetic energy and is not generally
                    # the source energy. Production labels should use a true
                    # PrimaryEnergy branch or per-dataset fixed truth.
                    energy = float(kinetic.max())
                    source = "step_kinetic_diagnostic"

            if (
                np.isnan(energy)
                and self.fixed_primary_energy_mev is not None
                and self.primary_energy_mode != "none"
            ):
                energy = float(self.fixed_primary_energy_mev)
                source = "fixed_dataset_fallback"

            result[event_id] = energy
            sources[event_id] = source
        self.primary_energy_source_by_event = sources
        return result

    def _build_event_truth_df(self, hit_df, primary_by_event):
        rows = []
        for event_id, group in hit_df.groupby("true_event_id", sort=False):
            total = float(group["energy"].sum())
            primary = float(primary_by_event.get(event_id, np.nan))
            if np.isnan(primary):
                y_event_full = None
            else:
                y_event_full = int(
                    abs(total - primary) < self.energy_tolerance_mev
                )
            rows.append(
                {
                    "true_event_id": event_id,
                    "primary_energy": primary,
                    "primary_energy_source": (
                        self.primary_energy_source_by_event.get(
                            event_id,
                            "missing",
                        )
                    ),
                    "event_total_deposition": total,
                    "y_event_full": y_event_full,
                    "visible_hit_ids": tuple(group["hit_id"].tolist()),
                    "n_visible_hits": int(len(group)),
                }
            )
        return pd.DataFrame(rows)
