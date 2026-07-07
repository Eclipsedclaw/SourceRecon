# from DataReader import DataReader

# reader = DataReader()
# reader.read_data()

# print(reader.ch0.head())
# print(reader.ch0.columns)
# print(reader.energy_response_ch0.head())

# from DataReader import DataReader
# from DataPreProcessor import DataPreProcessor


# reader = DataReader()
# reader.read_data()

# preprocessor = DataPreProcessor(reader)
# final_df = preprocessor.build_final_df()

# print(final_df.head())
# print(final_df.columns)
# print(final_df.shape)

from DataReader import DataReader
from DataPreProcessor import DataPreProcessor
from DataPlotter import DataPlotter


reader = DataReader()
reader.read_data()

preprocessor = DataPreProcessor(reader)
final_df = preprocessor.build_final_df()

# plotter = DataPlotter(final_df)

# plotter.plot_single_channel_spectra()
# plotter.plot_sum_energy_spectra()
# plotter.plot_ch1_ch2_2d_hist()
plotter = DataPlotter(
    final_df,
    save_dir="/home/ezqi/labwork/SourceRecon/EZQiWork/figures"
)

plotter.plot_all()