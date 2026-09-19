#!/usr/bin/env bash
set -euo pipefail
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -f "$project_dir/config/environment.sh" ]]; then
    set +u
    source "$project_dir/config/environment.sh"
    set -u
fi
if [[ ! -f "$project_dir/build/configure.ok" || ! -f "$project_dir/build/runtime_paths.sh" ]]; then
    echo 'Missing build/runtime_paths.sh. Run make configure and make all on this machine.' >&2
    exit 1
fi
source "$project_dir/build/runtime_paths.sh"
if [[ -n "$EFF_GEANT4_SH" ]]; then
    # 清掉旧安装留下的数据路径，再加载编译时选中的 Geant4 数据集。
    unset G4LEDATA G4ENSDFSTATEDATA G4LEVELGAMMADATA G4RADIOACTIVEDATA G4PARTICLEXSDATA
    unset G4NEUTRONHPDATA G4PIIDATA G4REALSURFACEDATA G4SAIDXSDATA G4ABLADATA G4INCLDATA
    # 上游环境脚本未必兼容 nounset。
    set +u
    source "$EFF_GEANT4_SH"
    set -u

    # 某些安装的 geant4.sh 没有导出数据路径，即使数据目录已经存在。
    # 从同一 bin 目录的 geant4-config 查询清单，不使用 PATH 中另一版本的工具。
    eff_geant4_config="$(dirname -- "$EFF_GEANT4_SH")/geant4-config"
    if [[ ! -x "$eff_geant4_config" ]]; then
        echo "Cannot query Geant4 datasets: $eff_geant4_config is not executable." >&2
        exit 1
    fi
    if ! eff_dataset_list="$("$eff_geant4_config" --datasets)" || [[ -z "$eff_dataset_list" ]]; then
        echo "Cannot read dataset list from $eff_geant4_config --datasets." >&2
        exit 1
    fi
    # 清单每行是：数据集名称 环境变量名 目录。按字段读取，不 eval 执行文本。
    while read -r eff_dataset_name eff_dataset_variable eff_dataset_path; do
        [[ -z "$eff_dataset_name" ]] && continue
        if [[ ! "$eff_dataset_variable" =~ ^G4[A-Z0-9_]*DATA$ || -z "$eff_dataset_path" ]]; then
            echo "Invalid Geant4 dataset entry: $eff_dataset_name $eff_dataset_variable $eff_dataset_path" >&2
            exit 1
        fi
        # 同一安装的 geant4.sh 已经设置了有效目录时保留；否则用清单补齐。
        eff_existing_dataset="${!eff_dataset_variable:-}"
        if [[ -n "$eff_existing_dataset" && -d "$eff_existing_dataset" ]]; then
            continue
        fi
        unset "$eff_dataset_variable"
        if [[ -d "$eff_dataset_path" ]]; then
            export "$eff_dataset_variable=$eff_dataset_path"
        else
            # 缺失数据不伪造路径、不下载；模拟器会拒绝缺少必需数据的运行。
            # ROOT 合并/测试本身无需 Geant4 物理数据，因此这里仅报告缺失目录。
            echo "Warning: Geant4 dataset $eff_dataset_name ($eff_dataset_variable) not found: $eff_dataset_path" >&2
        fi
    done <<< "$eff_dataset_list"
fi
unset G4FORCENUMBEROFTHREADS
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
if [[ -n "$EFF_LIBRARY_PATH" ]]; then
    export LD_LIBRARY_PATH="$EFF_LIBRARY_PATH${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
fi
export LD_BIND_NOW=1
exec "$@"
