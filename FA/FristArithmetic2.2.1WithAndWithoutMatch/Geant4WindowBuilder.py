# Geant4WindowBuilder.py

import numpy as np


class Geant4WindowBuilder:
    """
    用 Geant4 hit_df 构造训练用 fake coincidence windows。

    每个 window 包含多个 true_event_id 的 hit。
    这样枚举出来的 candidate 既有真组合，也有假组合。

    hit 来自同一个 true_event_id:
        y_match = 1

    hit 来自不同 true_event_id:
        y_match = 0
    """

    def __init__(
        self,
        hit_df,
        event_ids_per_window=5,
        random_seed=42,
        shuffle=True,
    ):
        self.hit_df = hit_df
        self.event_ids_per_window = event_ids_per_window
        self.random_seed = random_seed
        self.shuffle = shuffle

        self.windows = []

    def build_windows(self):
        event_ids = self.hit_df["true_event_id"].dropna().unique()
        event_ids = np.array(event_ids)

        if self.shuffle:
            rng = np.random.default_rng(self.random_seed)
            rng.shuffle(event_ids)

        windows = []

        for start in range(0, len(event_ids), self.event_ids_per_window):
            ids = event_ids[start:start + self.event_ids_per_window]

            if len(ids) == 0:
                continue

            window_df = self.hit_df[
                self.hit_df["true_event_id"].isin(ids)
            ].copy()

            window = {
                "window_id": len(windows),
                "true_event_ids": list(ids),
                "hit_df": window_df.reset_index(drop=True),
            }

            windows.append(window)

        self.windows = windows
        return windows

    def split_train_test(self, train_ratio=0.8):
        """
        按 true_event_id 切分训练/测试，避免 EventID 泄漏。
        """

        event_ids = self.hit_df["true_event_id"].dropna().unique()
        event_ids = np.array(event_ids)

        rng = np.random.default_rng(self.random_seed)
        rng.shuffle(event_ids)

        n_train = int(len(event_ids) * train_ratio)

        train_ids = set(event_ids[:n_train])
        test_ids = set(event_ids[n_train:])

        train_df = self.hit_df[self.hit_df["true_event_id"].isin(train_ids)].copy()
        test_df = self.hit_df[self.hit_df["true_event_id"].isin(test_ids)].copy()

        return train_df.reset_index(drop=True), test_df.reset_index(drop=True)

    def split_train_validation_test(
        self,
        train_ratio=0.70,
        validation_ratio=0.15,
    ):
        """Group split by true_event_id with no candidate-level leakage."""

        if train_ratio <= 0.0 or validation_ratio <= 0.0:
            raise ValueError("train_ratio 和 validation_ratio 必须为正数。")
        if train_ratio + validation_ratio >= 1.0:
            raise ValueError("train_ratio + validation_ratio 必须小于 1。")

        event_ids = np.asarray(
            self.hit_df["true_event_id"].dropna().unique()
        )
        rng = np.random.default_rng(self.random_seed)
        rng.shuffle(event_ids)

        n_events = len(event_ids)
        n_train = int(n_events * train_ratio)
        n_validation = int(n_events * validation_ratio)
        train_ids = set(event_ids[:n_train])
        validation_ids = set(
            event_ids[n_train:n_train + n_validation]
        )
        test_ids = set(event_ids[n_train + n_validation:])

        train_df = self.hit_df[
            self.hit_df["true_event_id"].isin(train_ids)
        ].copy()
        validation_df = self.hit_df[
            self.hit_df["true_event_id"].isin(validation_ids)
        ].copy()
        test_df = self.hit_df[
            self.hit_df["true_event_id"].isin(test_ids)
        ].copy()
        return (
            train_df.reset_index(drop=True),
            validation_df.reset_index(drop=True),
            test_df.reset_index(drop=True),
        )
