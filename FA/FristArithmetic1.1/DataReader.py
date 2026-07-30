import pandas as pd

class DataReader:
    def __init__(self):
        #只是为了增加可读性
        self.ch0 = None
        self.ch1 = None
        self.ch2 = None

        self.energy_response_ch0 = None
        self.energy_response_ch1 = None
        self.energy_response_ch2 = None

    def read_data(self):

        #这个对于不同的数据集需要手动修改
        #后期可以写一个遍历之类的，这也是我单独把他做成一个类的初衷

        self.ch0 = pd.read_csv("/data/data/jiancheng/SourceRecon_data/compton_work_0513/compton_work_100_100_100_40pt_28.5V_4hours_0513_rd_ch0.txt",sep="\t")
        self.ch1 = pd.read_csv("/data/data/jiancheng/SourceRecon_data/compton_work_0513/compton_work_100_100_100_40pt_28.5V_4hours_0513_rd_ch1.txt",sep="\t")
        self.ch2 = pd.read_csv("/data/data/jiancheng/SourceRecon_data/compton_work_0513/compton_work_100_100_100_40pt_28.5V_4hours_0513_rd_ch2.txt",sep="\t")
        self.energy_response_ch0 = pd.read_csv("/data/data/compton_camera/calib_result/Calib_28.5V_new_firmware_40pt/calibration_results_fixed_ch0/calibration_results.txt",sep="\t")
        self.energy_response_ch1 = pd.read_csv("/data/data/compton_camera/calib_result/Calib_28.5V_new_firmware_40pt/calibration_results_fixed_ch1/calibration_results.txt",sep="\t")
        self.energy_response_ch2 = pd.read_csv("/data/data/compton_camera/calib_result/Calib_28.5V_new_firmware_40pt/calibration_results_fixed_ch2/calibration_results.txt",sep="\t")

        

