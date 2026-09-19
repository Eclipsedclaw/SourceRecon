#!/usr/bin/env python3
"""准备清单，不运行物理模拟、不提交集群任务；仅使用 Python 标准库。"""
import argparse
import json
import math
import os
import platform
import uuid
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
UINT64_MAX = (1 << 64) - 1


def read_json(path):
    with Path(path).open(encoding="utf-8-sig") as stream:
        return json.load(stream)


def positive_int(value, name, maximum=UINT64_MAX):
    if type(value) is not int or not 0 < value <= maximum:
        raise ValueError("{} must be an integer in [1, {}]".format(name, maximum))
    return value


def validate_sim(sim):
    grid, source, environment, trigger = (sim[k] for k in ("grid", "source", "environment", "trigger"))
    n = positive_int(grid["healpix_nside"], "healpix_nside", 8192)
    if n & (n - 1):
        raise ValueError("healpix_nside must be a power of two")
    energy_count = positive_int(grid["energy_point_count"], "energy_point_count", 1000000)
    particles = positive_int(grid["particles_per_cell"], "particles_per_cell")
    lo, hi = grid["energy_min_MeV"], grid["energy_max_MeV"]
    for key, value in [("energy_min_MeV", lo), ("energy_max_MeV", hi),
                       ("hemisphere_radius_mm", source["hemisphere_radius_mm"]),
                       ("world_margin_mm", environment["world_margin_mm"])]:
        if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
            raise ValueError(key + " must be finite and positive")
    if hi < lo or ((energy_count == 1) != (lo == hi)):
        raise ValueError("One energy point requires min=max; multiple points require max>min")
    if source["particle_name"] != "gamma" or type(source["front_hemisphere_only"]) is not bool:
        raise ValueError("Use gamma and a boolean front_hemisphere_only")
    if environment["world_material"] not in ("G4_AIR", "G4_Galactic"):
        raise ValueError("Unsupported world material")
    margin = source["emission_cone_safety_margin_degree"]
    threshold = trigger["minimum_layer_energy_MeV"]
    if not math.isfinite(margin) or not 0 <= margin < 45 or not math.isfinite(threshold) or threshold < 0:
        raise ValueError("Invalid cone margin or threshold")
    if trigger["front_chamber_id"] != 0 or trigger["rear_chamber_id"] != 1:
        raise ValueError("Geometry requires ch2=0, ch1=1")
    directions = 6 * n * n + 2 * n if source["front_hemisphere_only"] else 12 * n * n
    total = directions * energy_count * particles
    positive_int(total, "total events")
    return total


def run_directory(run_path, run=None):
    run_path = Path(run_path).resolve()
    run = read_json(run_path) if run is None else run
    return (run_path.parent / run["output_directory"]).resolve()


def detect_os():
    if platform.system() != "Linux":
        return "LOCAL"
    values = {}
    try:
        for line in Path("/etc/os-release").read_text().splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                values[key] = value.strip('"')
    except OSError:
        return "LOCAL"
    if values.get("ID") in ("centos", "rhel", "rocky", "almalinux"):
        return "EL" + values.get("VERSION_ID", "").split(".")[0]
    return "LOCAL"


def build_manifest(sim, run):
    total = validate_sim(sim)
    threads = positive_int(run["threads"], "threads", 18)
    jobs = positive_int(run["jobs"], "jobs", 1000000)
    batch = positive_int(run["events_per_chunk"], "events_per_chunk", (1 << 31) - 1)
    positive_int(run["master_seed"], "master_seed")
    if jobs * threads > 300:
        raise ValueError("This template limits requested CPUs to 300; reduce jobs or threads")
    block_count = (total + batch - 1) // batch
    if block_count < jobs:
        raise ValueError("More jobs than chunks; reduce jobs or events_per_chunk")
    if block_count > 1000000:
        raise ValueError("Too many tiny chunks; increase events_per_chunk")
    chunks = [{"id": i, "first_event": i * batch, "event_count": min(batch, total - i * batch),
               "job_id": i % jobs} for i in range(block_count)]
    return {"schema_version": 1, "campaign_id": uuid.uuid4().hex, "sim_config": sim,
            "run_config": run, "total_events": total, "chunks": chunks}


def prepare(sim_path, run_path, cluster_path):
    sim, run, cluster = (read_json(p) for p in (sim_path, run_path, cluster_path))
    proposed = build_manifest(sim, run)
    directory = run_directory(run_path, run)
    # 为 Condor 保持路径无空白和引号；避免参数被错误地拆成多段。
    python = cluster["python_executable"]
    for value in (str(directory), str(PROJECT), python):
        if any(c.isspace() or c in '\"\'' for c in value):
            raise ValueError("Cluster paths must not contain whitespace or quotes")
    for key in ("request_memory_mb", "request_disk_mb", "merge_memory_mb"):
        positive_int(cluster[key], key)
    requested_os = cluster["target_os"]
    if requested_os not in ("auto", "EL7", "EL9"):
        raise ValueError("target_os must be auto, EL7 or EL9")
    target_os = detect_os() if requested_os == "auto" else requested_os
    requirements = cluster.get("requirements", "")
    if "\n" in requirements or "\r" in requirements:
        raise ValueError("requirements must be one line")
    for name in ("chunks", "logs", ".locks"):
        (directory / name).mkdir(parents=True, exist_ok=True)
    manifest_path = directory / "manifest.json"
    if manifest_path.exists():
        existing = read_json(manifest_path)
        for key in ("schema_version", "sim_config", "run_config", "total_events", "chunks"):
            if existing[key] != proposed[key]:
                raise ValueError("Run directory already belongs to another plan. Change output_directory.")
    else:
        # 不覆盖旧计划。源配置随后即使被修改，模拟器也只读取这份冻结的快照。
        with manifest_path.open("x", encoding="utf-8") as stream:
            json.dump(proposed, stream, indent=2)
    if target_os in ("EL7", "EL9"):
        os_rule = '(SJTU_NODE_OS =?= "{}")'.format(target_os)
        if target_os == "EL7":
            # 老节点可能没有新加入的 SJTU_NODE_OS；兼容 Condor 的标准 OS 广告字段。
            os_rule = '(' + os_rule + ' || (OpSysAndVer =?= "CentOS7") || (OpSysAndVer =?= "RedHat7"))'
        requirements = "({}) && ({})".format(os_rule, requirements) if requirements else os_rule
    else:
        # 小服务器可以 prepare/run-local，但未确认 OS 的构建绝不提交到集群。
        requirements = "False"
    replacements = {
        "PROJECT": str(PROJECT), "MANIFEST": str(manifest_path), "RUN": str(directory), "PYTHON": python,
        "THREADS": str(run["threads"]), "JOBS": str(run["jobs"]), "MEMORY": str(cluster["request_memory_mb"]),
        "DISK": str(cluster["request_disk_mb"]), "MERGE_MEMORY": str(cluster["merge_memory_mb"]),
        "REQUIREMENTS": requirements, "OS_ATTRIBUTE": '+SJTU_JOB_OS = "EL9"' if target_os == "EL9" else "",
    }
    for source, output in [("simulation.sub.in", "simulation.sub"), ("merge.sub.in", "merge.sub")]:
        text = (PROJECT / "cluster" / source).read_text(encoding="utf-8")
        for key, value in replacements.items():
            text = text.replace("@@" + key + "@@", value)
        (directory / output).write_text(text, encoding="utf-8")
    (directory / "submission_info.json").write_text(json.dumps({"target_os": target_os, "cluster_config": cluster}, indent=2), encoding="utf-8")
    message = "Prepared {} events in {} chunks / {} jobs, {} threads/job.\nManifest: {}\n".format(
        proposed["total_events"], len(proposed["chunks"]), run["jobs"], run["threads"], manifest_path)
    with (directory / "logs" / "prepare.log").open("a", encoding="utf-8") as stream:
        stream.write(message)
    print(message, end="")
    return manifest_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sim", default="config/sim_config.json")
    parser.add_argument("--run", default="config/run_config.json")
    parser.add_argument("--cluster", default="config/cluster_config.json")
    args = parser.parse_args()
    try:
        prepare(args.sim, args.run, args.cluster)
    except (ValueError, KeyError, OSError) as error:
        parser.exit(1, "Preparation error: {}\n".format(error))
