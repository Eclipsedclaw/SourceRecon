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
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help=(
            "批处理 worker 进程数；省略时使用 JSON 中的 "
            "batch.parallel_workers。"
        ),
    )
    arguments = parser.parse_args()

    configuration = Configuration.from_json(arguments.config)
    input_type = configuration.section("input").get("type")
    if arguments.workers is not None:
        if input_type != "geant4_batch":
            raise ValueError("--workers 只适用于 input.type=geant4_batch。")
        if arguments.workers <= 0:
            raise ValueError("--workers 必须大于 0。")
        payload = configuration.as_dict()
        payload.setdefault("batch", {})["parallel_workers"] = (
            arguments.workers
        )
        configuration = configuration.derived(payload)
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
