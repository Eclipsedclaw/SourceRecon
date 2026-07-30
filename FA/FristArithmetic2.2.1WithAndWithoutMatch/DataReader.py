import pandas as pd

class DataReader:
    def __init__(
        self,
        ch0_path=None,
        ch1_path=None,
        ch2_path=None,
        calibration_ch0_path=None,
        calibration_ch1_path=None,
        calibration_ch2_path=None,
    ):
        #只是为了增加可读性
        self.ch0 = None
        self.ch1 = None
        self.ch2 = None

        self.energy_response_ch0 = None
        self.energy_response_ch1 = None
        self.energy_response_ch2 = None

        self.ch0_path = ch0_path
        self.ch1_path = ch1_path
        self.ch2_path = ch2_path
        self.calibration_ch0_path = calibration_ch0_path
        self.calibration_ch1_path = calibration_ch1_path
        self.calibration_ch2_path = calibration_ch2_path

    def read_data(self):

        #这个对于不同的数据集需要手动修改
        #后期可以写一个遍历之类的，这也是我单独把他做成一个类的初衷

        paths = {
            "ch0": self.ch0_path,
            "ch1": self.ch1_path,
            "ch2": self.ch2_path,
            "calibration_ch0": self.calibration_ch0_path,
            "calibration_ch1": self.calibration_ch1_path,
            "calibration_ch2": self.calibration_ch2_path,
        }
        missing = [name for name, path in paths.items() if not path]
        if missing:
            raise ValueError(
                "DataReader 缺少输入路径：" + ", ".join(missing)
            )

        self.ch0 = pd.read_csv(self.ch0_path, sep="\t")
        self.ch1 = pd.read_csv(self.ch1_path, sep="\t")
        self.ch2 = pd.read_csv(self.ch2_path, sep="\t")
        self.energy_response_ch0 = pd.read_csv(
            self.calibration_ch0_path, sep="\t"
        )
        self.energy_response_ch1 = pd.read_csv(
            self.calibration_ch1_path, sep="\t"
        )
        self.energy_response_ch2 = pd.read_csv(
            self.calibration_ch2_path, sep="\t"
        )

        
