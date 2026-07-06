# from DataReader import DataReader

# reader = DataReader()
# reader.read_data()

# print(reader.ch0.head())
# print(reader.ch0.columns)
# print(reader.energy_response_ch0.head())

from DataReader import DataReader
from DataPreProcessor import DataPreProcessor


reader = DataReader()
reader.read_data()

preprocessor = DataPreProcessor(reader)
final_df = preprocessor.build_final_df()

print(final_df.head())
print(final_df.columns)
print(final_df.shape)