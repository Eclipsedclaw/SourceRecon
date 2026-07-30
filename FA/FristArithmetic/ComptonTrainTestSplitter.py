# ComptonTrainTestSplitter.py

import numpy as np
import pandas as pd


class ComptonTrainTestSplitter:
    """
    Compton MC 数据训练集 / 测试集划分类。

    输入：
        DataPreProcessor 得到的 final_df。

    输出：
        train_df
        test_df

    核心原则：
        按 Geant4 真 EventID 切分，而不是按 DataFrame 行随机切分。

    原因：
        同一个 Geant4 EventID 代表同一个 gamma 产生的一组 hit。
        如果同一个 EventID 同时进入 train 和 test，就会发生数据泄漏。
    """

    def __init__(
        self,
        final_df: pd.DataFrame,
        train_ratio=0.8,
        random_seed=42,
        event_id_column="EventID",
        shuffle=True,
    ):
        self.final_df = final_df
        self.train_ratio = train_ratio
        self.random_seed = random_seed
        self.event_id_column = event_id_column
        self.shuffle = shuffle

        self.train_event_ids = set()
        self.test_event_ids = set()

        self.train_df = None
        self.test_df = None

    def split(self):
        """
        执行 train/test 划分。

        返回：
            train_df, test_df
        """

        self._check_input()

        unique_event_ids = (
            self.final_df[self.event_id_column]
            .dropna()
            .unique()
        )

        unique_event_ids = np.array(unique_event_ids)

        if self.shuffle:
            rng = np.random.default_rng(self.random_seed)
            rng.shuffle(unique_event_ids)

        n_total = len(unique_event_ids)
        n_train = int(n_total * self.train_ratio)

        self.train_event_ids = set(unique_event_ids[:n_train])
        self.test_event_ids = set(unique_event_ids[n_train:])

        self.train_df = self.final_df[
            self.final_df[self.event_id_column].isin(self.train_event_ids)
        ].copy()

        self.test_df = self.final_df[
            self.final_df[self.event_id_column].isin(self.test_event_ids)
        ].copy()

        self.train_df = self.train_df.reset_index(drop=True)
        self.test_df = self.test_df.reset_index(drop=True)

        self._check_no_event_id_leakage()

        return self.train_df, self.test_df

    def _check_input(self):
        """
        检查输入 final_df 是否满足基本要求。
        """

        if self.final_df is None:
            raise ValueError("final_df 是 None，无法划分训练集和测试集。")

        if self.event_id_column not in self.final_df.columns:
            raise ValueError(
                f"final_df 中找不到 {self.event_id_column} 列。"
            )

        if not 0.0 < self.train_ratio < 1.0:
            raise ValueError("train_ratio 必须在 0 和 1 之间。")

    def _check_no_event_id_leakage(self):
        """
        检查 train/test 是否存在 EventID 泄漏。
        """

        overlap = self.train_event_ids.intersection(self.test_event_ids)

        if len(overlap) > 0:
            raise RuntimeError(
                "train/test 出现 EventID 泄漏。"
                f" 重复 EventID 数量 = {len(overlap)}"
            )

    def get_summary(self):
        """
        返回划分结果摘要。
        """

        if self.train_df is None or self.test_df is None:
            raise RuntimeError("请先执行 split()，再调用 get_summary()。")

        summary = {
            "total_rows": len(self.final_df),
            "train_rows": len(self.train_df),
            "test_rows": len(self.test_df),

            "total_event_ids": (
                self.final_df[self.event_id_column]
                .dropna()
                .nunique()
            ),
            "train_event_ids": len(self.train_event_ids),
            "test_event_ids": len(self.test_event_ids),

            "train_ratio": self.train_ratio,
            "random_seed": self.random_seed,
        }

        return summary

    def print_summary(self):
        """
        打印划分结果摘要。
        """

        summary = self.get_summary()

        print("========== Train/Test Split Summary ==========")
        print(f"total rows       : {summary['total_rows']}")
        print(f"train rows       : {summary['train_rows']}")
        print(f"test rows        : {summary['test_rows']}")
        print()
        print(f"total EventID    : {summary['total_event_ids']}")
        print(f"train EventID    : {summary['train_event_ids']}")
        print(f"test EventID     : {summary['test_event_ids']}")
        print()
        print(f"train ratio      : {summary['train_ratio']}")
        print(f"random seed      : {summary['random_seed']}")
        print("==============================================")