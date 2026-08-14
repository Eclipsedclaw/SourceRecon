"""Geant4 ROOT 输入入口。所有参数均由 --config 指定的 JSON 控制。"""

import argparse

from soe1 import Configuration
from soe1.application import SoeApplication


def main():
    parser = argparse.ArgumentParser(
        description="使用 Geant4 event truth 分组运行未知能量多圆锥 SOE。"
    )
    parser.add_argument(
        "--config",
        required=True,
        help="Geant4 JSON 配置文件路径。",
    )
    arguments = parser.parse_args()

    configuration = Configuration.from_json(arguments.config)
    if configuration.section("input").get("type") != "geant4_root":
        raise ValueError("main_geant4.py 要求 input.type=geant4_root。")
    output_paths = SoeApplication(configuration).run()

    print("SOE1 Geant4 reconstruction finished.")
    for name, path in output_paths.items():
        print(name + ": " + path)


if __name__ == "__main__":
    main()

