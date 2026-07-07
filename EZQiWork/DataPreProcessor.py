import pandas as pd

from DataReader import DataReader


class DataPreProcessor:
    """
    Compton 相机数据预处理类。

    本类接收 DataReader 已经读取好的原始数据和能量刻度表，
    对 ch0/ch1/ch2 分别进行能量校准，并将三个通道的数据
    按 EventID 合并成一个事件级别的大表 final_df。

    输出：
        final_df:
            每一行对应一个 EventID，包含不同通道的击中位置和能量信息。
            例如：
                ch0_x, ch0_y, ch0_z, ch0_energy
                ch1_x, ch1_y, ch1_z, ch1_energy
                ch2_x, ch2_y, ch2_z, ch2_energy
    """

    def __init__(self, datareader: DataReader):
        """
        参数：
            datareader:
                已经执行过 read_data() 的 DataReader 对象。
                其中应包含 ch0/ch1/ch2 原始数据，以及三个通道的能量刻度表。
        """

        self.datareader = datareader
        self.final_df = None

    def process_channel(self, df_raw, df_calib, prefix):
        """
        对单个探测器通道进行预处理。

        主要步骤：
            1. 根据 PixelID 将原始数据和能量刻度参数合并；
            2. 使用线性刻度公式将 TotalEnergy 转换为物理能量；
            3. 将能量单位从 keV 转换为 MeV；
            4. 给列名加上通道前缀，避免合并时列名冲突；
            5. 只保留后续分析所需的列。

        参数：
            df_raw:
                某一个通道的原始数据表。

            df_calib:
                该通道对应的能量刻度表，应包含：
                    PixelID
                    a(keV/ADC)
                    b(keV)

            prefix:
                通道名前缀，例如 "ch0"、"ch1"、"ch2"。

        返回：
            处理后的单通道 DataFrame。
        """

        # 根据 PixelID 匹配每个像素对应的能量刻度参数 a 和 b。
        merged = pd.merge(
            df_raw,
            df_calib[["PixelID", "a(keV/ADC)", "b(keV)"]],
            on="PixelID",
            how="left",
        )

        # 使用线性能量刻度公式：
        # energy_keV = TotalEnergy * a + b
        merged["energy_keV"] = (
            merged["TotalEnergy"] * merged["a(keV/ADC)"]
            + merged["b(keV)"]
        )

        # 后续 Compton 分析通常使用 MeV，因此这里将 keV 转换为 MeV。
        merged["energy_MeV"] = merged["energy_keV"] / 1000.0

        # 给列名加上通道前缀，避免 ch0/ch1/ch2 合并时出现重名列。
        merged = merged.rename(
            columns={
                "PixelID": f"{prefix}_pixelid",
                "pos_x_mm": f"{prefix}_x",
                "pos_y_mm": f"{prefix}_y",
                "z": f"{prefix}_z",
                "energy_MeV": f"{prefix}_energy",
            }
        )

        # 只保留后续分析需要的列，避免 final_df 过于冗余。
        return merged[
            [
                "EventID",
                f"{prefix}_pixelid",
                f"{prefix}_x",
                f"{prefix}_y",
                f"{prefix}_z",
                f"{prefix}_energy",
            ]
        ]

    def build_final_df(self):
        """
        构建最终事件表 final_df。

        该函数会分别处理 ch0/ch1/ch2，然后按照 EventID 进行 outer merge。
        使用 outer merge 的原因是：
            只要某个 EventID 在任意一个通道中出现，就保留下来；
            若该事件在某些通道中没有信号，对应列会显示为 NaN。
        """

        df0 = self.process_channel(
            self.datareader.ch0,
            self.datareader.energy_response_ch0,
            "ch0",
        )

        df1 = self.process_channel(
            self.datareader.ch1,
            self.datareader.energy_response_ch1,
            "ch1",
        )

        df2 = self.process_channel(
            self.datareader.ch2,
            self.datareader.energy_response_ch2,
            "ch2",
        )

        # 先合并 ch0 和 ch1。
        final_df = pd.merge(df0, df1, on="EventID", how="outer")

        # 再将 ch2 合并进来。
        final_df = pd.merge(final_df, df2, on="EventID", how="outer")

        # 按照 EventID 排序并重置索引，看起来更整洁
        final_df = final_df.sort_values(by='EventID').reset_index(drop=True)

        self.final_df = final_df
        return final_df