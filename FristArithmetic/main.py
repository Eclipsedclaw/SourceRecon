# from DataReader import DataReader
# from DataPreProcessor import DataPreProcessor



# reader = DataReader()
# reader.read_data()

# preprocessor = DataPreProcessor(reader)
# final_df = preprocessor.build_final_df()

# # final_df.head
# print(final_df.head())

# Putinforarithmetic = final_df[["ch0_pixelid","ch0_x","ch0_y","ch0_z","ch0_energy","ch1_pixelid","ch1_x","ch1_y","ch1_z","ch1_energy","ch2_pixelid","ch2_x","ch2_y","ch2_z","ch2_energy"]]

# print(Putinforarithmetic.head())

# main.py

# =========================================================
# 测试EventSeparator的功能

# from DataReader import DataReader
# from DataPreProcessor import DataPreProcessor
# from EventSeparator import EventSeparator


# reader = DataReader()
# reader.read_data()

# preprocessor = DataPreProcessor(reader)
# final_df = preprocessor.build_final_df()

# separator = EventSeparator(
#     final_df=final_df,
#     min_energy=0.0,
#     allow_backscatter=False,
#     sigma_delta_cos=0.15,
# )

# event_list = separator.separate()

# print("event 总数:", len(event_list))
# print("event 索引:", event_list.get_indexes()[:10])

# event_df = event_list.to_dataframe()

# print(event_df.head())

# # 查看第 0 个 event 对象
# event0 = event_list.get_event(0)

# print("第 0 个 event 类型:", event0.event_type)
# print("第 0 个 event 分数:", event0.score)
# print("第 0 个 event 通道:", event0.channels)
# print("第 0 个 event 能量:", event0.E_total)

# ==============================================================

# from DataReader import DataReader
# from DataPreProcessor import DataPreProcessor
# from EventSeparator import EventSeparator
# from ComptonEventScorer import ComptonEventScorer


# reader = DataReader()
# reader.read_data()

# preprocessor = DataPreProcessor(reader)
# final_df = preprocessor.build_final_df()

# separator = EventSeparator(
#     final_df=final_df,
#     min_energy=0.0,
#     allow_backscatter=False,
#     sigma_delta_cos=0.15,
# )

# event_list = separator.separate()

# print("打分前第 0 个 event 分数:", event_list.get_event(0).score)

# scorer = ComptonEventScorer(event_list)
# scorer.score_all_events()

# print("打分后第 0 个 event 分数:", event_list.get_event(0).score)
# print("第 0 个 event 特征:", event_list.get_event(0).score_features)

# event_df = event_list.to_dataframe()
# print(event_df.head())

# =========================================================

# from DataReader import DataReader
# from DataPreProcessor import DataPreProcessor
# from EventSeparator import EventSeparator
# from ComptonEventScorer import ComptonEventScorer
# from ComptonGradientTrainer import ComptonGradientTrainer
# from EventMatcher import EventMatcher


# reader = DataReader()
# reader.read_data()

# preprocessor = DataPreProcessor(reader)
# final_df = preprocessor.build_final_df()

# separator = EventSeparator(final_df)
# event_list = separator.separate()

# scorer = ComptonEventScorer(event_list)
# scorer.score_all_events()

# # labels 来自 Monte Carlo 真值
# # 例如：
# # labels = {
# #     0: 1,
# #     1: 0,
# #     2: 0,
# #     3: 1,
# # }
# labels = {}

# trainer = ComptonGradientTrainer(
#     scorer=scorer,
#     learning_rate=0.05,
# )

# trainer.fit(
#     labels=labels,
#     epochs=200,
#     verbose=True,
# )

# matcher = EventMatcher(event_list)
# matched_event_list = matcher.match()

# print("matching 后 event 数量:", len(matched_event_list))

# =========================================================

# main.py

from DataReader import DataReader
from DataPreProcessor import DataPreProcessor

from EventSeparator import EventSeparator
from ComptonEventScorer import ComptonEventScorer
from ComptonGradientTrainer import ComptonGradientTrainer
from EventMatcher import EventMatcher
from ComptonConeImager import ComptonConeImager


def split_train_test_by_event_id(final_df, train_ratio=0.8, random_seed=42):
    """
    按 Geant4 真 EventID 切分训练集和测试集。

    注意：
        这里切的是 EventID，不是 candidate event。
        这样可以避免同一条 MC gamma 的信息同时出现在训练和测试中。
    """

    unique_event_ids = final_df["EventID"].dropna().unique()

    import numpy as np

    rng = np.random.default_rng(random_seed)
    rng.shuffle(unique_event_ids)

    n_train = int(len(unique_event_ids) * train_ratio)

    train_event_ids = set(unique_event_ids[:n_train])
    test_event_ids = set(unique_event_ids[n_train:])

    train_df = final_df[final_df["EventID"].isin(train_event_ids)].copy()
    test_df = final_df[final_df["EventID"].isin(test_event_ids)].copy()

    return train_df, test_df


def build_labels_from_mc_event_list(event_list):
    """
    根据 MC 真值构造标签。

    由于当前 EventSeparator 是从同一个 final_df row 里提取 hit，
    而 final_df row 本身按同一个 EventID 合并，
    所以这一步得到的候选通常都是同一个 MC EventID 内的候选。

    第一版：
        物理合法 event 标为 1；
        物理不合法 event 标为 0。

    更正式的后续版本：
        应该使用“混合时间窗 hit pool”生成正负样本。
        那时候 label 规则应该是：
            candidate 中所有 hit 的 true EventID 相同且顺序正确 → 1
            否则 → 0
    """

    labels = {}

    for idx, event in enumerate(event_list.events):
        if getattr(event, "is_physical", False):
            labels[idx] = 1
        else:
            labels[idx] = 0

    return labels


def run_training_and_imaging():
    # ============================================================
    # 1. 读取数据
    # ============================================================

    reader = DataReader()
    reader.read_data()

    preprocessor = DataPreProcessor(reader)
    final_df = preprocessor.build_final_df()

    print("final_df shape:", final_df.shape)

    # ============================================================
    # 2. train/test 切分
    # ============================================================

    train_df, test_df = split_train_test_by_event_id(
        final_df,
        train_ratio=0.8,
        random_seed=42,
    )

    print("train_df shape:", train_df.shape)
    print("test_df shape:", test_df.shape)

    # ============================================================
    # 3. 生成 train/test EventList
    # ============================================================

    train_separator = EventSeparator(
        final_df=train_df,
        min_energy=0.0,
        allow_backscatter=False,
        sigma_delta_cos=0.15,
    )

    test_separator = EventSeparator(
        final_df=test_df,
        min_energy=0.0,
        allow_backscatter=False,
        sigma_delta_cos=0.15,
    )

    train_event_list = train_separator.separate()
    test_event_list = test_separator.separate()

    print("train event 数量:", len(train_event_list))
    print("test event 数量:", len(test_event_list))

    # ============================================================
    # 4. 构造训练标签
    # ============================================================

    train_labels = build_labels_from_mc_event_list(train_event_list)

    print("train label 数量:", len(train_labels))
    print("正样本数量:", sum(train_labels.values()))
    print("负样本数量:", len(train_labels) - sum(train_labels.values()))

    # ============================================================
    # 5. 训练 scorer
    # ============================================================

    train_scorer = ComptonEventScorer(train_event_list)
    train_scorer.score_all_events()

    trainer = ComptonGradientTrainer(
        scorer=train_scorer,
        learning_rate=0.05,
    )

    trainer.fit(
        labels=train_labels,
        epochs=200,
        verbose=True,
    )

    print("训练完成。")

    # ============================================================
    # 6. 把训练好的参数复制给 test scorer
    # ============================================================

    test_scorer = ComptonEventScorer(
        event_list=test_event_list,
        params=train_scorer.params.copy(),
    )

    test_scorer.score_all_events()

    # ============================================================
    # 7. test 上做 EventMatcher
    # ============================================================

    matcher = EventMatcher(test_event_list)
    matched_test_event_list = matcher.match()

    print("matching 后 test event 数量:", len(matched_test_event_list))

    # ============================================================
    # 8. test 上做康普顿锥成像
    # ============================================================

    imager = ComptonConeImager(
        event_list=matched_test_event_list,

        # 如果你知道源在某个 z 平面，可以手动改这里。
        # 比如 image_plane_z=-160.0
        image_plane_z=None,

        plane_distance_mm=100.0,
        x_range=(-150.0, 150.0),
        y_range=(-150.0, 150.0),
        n_pixels=200,

        sigma_angle_deg=5.0,
        min_score=0.0,

        output_dir="figure/test_compton_imaging",
    )

    figure_paths = imager.save_all_diagnostic_plots()

    print("输出图像：")
    for path in figure_paths:
        print(path)


if __name__ == "__main__":
    run_training_and_imaging()