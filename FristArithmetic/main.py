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

from DataReader import DataReader
from DataPreProcessor import DataPreProcessor
from EventSeparator import EventSeparator


reader = DataReader()
reader.read_data()

preprocessor = DataPreProcessor(reader)
final_df = preprocessor.build_final_df()

separator = EventSeparator(
    final_df=final_df,
    min_energy=0.0,
    allow_backscatter=False,
    sigma_delta_cos=0.15,
)

event_list = separator.separate()

print("event 总数:", len(event_list))
print("event 索引:", event_list.get_indexes()[:10])

event_df = event_list.to_dataframe()

print(event_df.head())

# 查看第 0 个 event 对象
event0 = event_list.get_event(0)

print("第 0 个 event 类型:", event0.event_type)
print("第 0 个 event 分数:", event0.score)
print("第 0 个 event 通道:", event0.channels)
print("第 0 个 event 能量:", event0.E_total)