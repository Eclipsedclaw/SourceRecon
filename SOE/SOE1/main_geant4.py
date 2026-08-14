"""Geant4 ROOT 输入入口。所有参数均由 --config 指定的 JSON 控制。"""

import argparse

from soe1 import Configuration
from soe1.application import SimulationBatchApplication, SoeApplication


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
    input_type = configuration.section("input").get("type")
    if input_type == "geant4_root":
        output_paths = SoeApplication(configuration).run()
    elif input_type == "geant4_batch":
        output_paths = SimulationBatchApplication(configuration).run()
    else:
        raise ValueError(
            "main_geant4.py 要求 input.type=geant4_root 或 geant4_batch。"
        )

    print("SOE1 Geant4 reconstruction finished.", flush=True)
    for name, path in output_paths.items():
        print(name + ": " + path, flush=True)


if __name__ == "__main__":
    main()
