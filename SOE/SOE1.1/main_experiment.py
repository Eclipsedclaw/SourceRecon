"""实验 TSV 输入入口。所有参数均由 --config 指定的 JSON 控制。"""

import argparse

from soe1 import Configuration
from soe1.application import SoeApplication


def main():
    parser = argparse.ArgumentParser(
        description="使用实验 EventID 分组运行未知能量多圆锥 SOE。"
    )
    parser.add_argument(
        "--config",
        required=True,
        help="实验 JSON 配置文件路径。",
    )
    arguments = parser.parse_args()

    configuration = Configuration.from_json(arguments.config)
    if configuration.section("input").get("type") != "experiment_tsv":
        raise ValueError("main_experiment.py 要求 input.type=experiment_tsv。")
    output_paths = SoeApplication(configuration).run()

    print("SOE1 experimental reconstruction finished.")
    for name, path in output_paths.items():
        print(name + ": " + path)


if __name__ == "__main__":
    main()

