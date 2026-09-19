#!/usr/bin/env python3
"""统一启动和日志入口。运行中实时 tee stdout+stderr；每次尝试保留独立日志。"""
import argparse
import contextlib
import datetime
import json
import os
import signal
import socket
import subprocess
import sys
import uuid
from pathlib import Path

from prepare_jobs import PROJECT, read_json, run_directory


@contextlib.contextmanager
def job_lock(path):
    # 使用 OS 文件锁，而不是“锁文件是否存在”。进程死亡后内核会释放锁，
    # 不会留下必须手动删除的过期锁目录。Linux/Lustre 需要支持 flock。
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as stream:
        if os.name == "posix":
            import fcntl
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        else:
            import msvcrt
            stream.seek(0)
            if not stream.read(1):
                stream.write(b"0")
                stream.flush()
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        yield stream.fileno()


def run_logged(command, directory, label):
    directory = Path(directory)
    (directory / "logs").mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S")
    log_path = directory / "logs" / (label + "_attempt_" + stamp + "_" + uuid.uuid4().hex[:8] + ".log")
    print("Log: " + str(log_path), flush=True)
    with log_path.open("xb", buffering=0) as log:
        def emit(data):
            log.write(data)
            try:
                sys.stdout.buffer.write(data)
                sys.stdout.buffer.flush()
            except BrokenPipeError:
                pass  # 终端断开不能导致日志丢失。

        header = {"start_utc": stamp, "host": socket.gethostname(), "command": command, "cwd": str(PROJECT)}
        emit((json.dumps(header) + "\n").encode())
        previous = {}
        try:
            with job_lock(directory / ".locks" / (label + ".lock")) as lock_fd:
                options = {"cwd": str(PROJECT), "stdout": subprocess.PIPE, "stderr": subprocess.STDOUT, "bufsize": 0}
                if os.name == "posix":
                    options.update(start_new_session=True, pass_fds=(lock_fd,))
                process = subprocess.Popen(command, **options)

                def forward(signum, frame):
                    del frame
                    emit(("Received signal {}; forwarding to child\n".format(signum)).encode())
                    try:
                        if os.name == "posix":
                            os.killpg(process.pid, signum)
                        else:
                            process.terminate()
                    except ProcessLookupError:
                        pass

                for name in ("SIGTERM", "SIGINT", "SIGHUP"):
                    if hasattr(signal, name):
                        signum = getattr(signal, name)
                        previous[signum] = signal.signal(signum, forward)
                # 不按行等待：即使末尾没换行或某条 Geant4 输出很长，也能实时保留。
                while True:
                    block = process.stdout.read(4096)
                    if not block:
                        break
                    emit(block)
                process.stdout.close()
                code = process.wait()
                code = code if code >= 0 else 128 - code
        except (OSError, ValueError) as error:
            emit(("Launcher error: {}\n".format(error)).encode())
            code = 1
        finally:
            for signum, handler in previous.items():
                signal.signal(signum, handler)
        emit(("\nexit_status={} end_utc={}\n".format(code, datetime.datetime.now(datetime.timezone.utc).isoformat())).encode())
        return code


def execute(action, manifest_path, job_id=None):
    manifest_path = Path(manifest_path).resolve()
    manifest = read_json(manifest_path)
    directory = manifest_path.parent
    setup = str(PROJECT / "cluster" / "setup_env.sh")
    if action == "job":
        if job_id is None or not 0 <= job_id < manifest["run_config"]["jobs"]:
            raise ValueError("Invalid job ID")
        binary = str(PROJECT / "build" / "bin" / "efficiency_simulator")
        return run_logged(["bash", setup, binary, str(manifest_path), str(job_id)], directory, "job_{:04d}".format(job_id))
    if action == "local":
        for job in range(manifest["run_config"]["jobs"]):
            code = execute("job", manifest_path, job)
            if code:
                return code
        return execute("merge", manifest_path)
    if action in ("merge", "check"):
        binary = str(PROJECT / "build" / "bin" / "efficiency_merge")
        command = ["bash", setup, binary, str(manifest_path)]
        # 合并器会复核已有最终文件的每行数据，不覆盖；check 不创建新最终文件。
        if action == "check":
            command.append("--check-only")
        return run_logged(command, directory, "merge")
    if action in ("submit", "submit-merge"):
        info = read_json(directory / "submission_info.json")
        if info["target_os"] not in ("EL7", "EL9"):
            raise ValueError("Submission OS is unverified. Build/prepare on the cluster with matching target_os.")
        if action == "submit-merge":
            missing = [t["id"] for t in manifest["chunks"] if not (directory / "chunks" / ("chunk_{:08d}.root".format(t["id"]))).is_file()]
            if missing:
                raise ValueError("Simulation not finished; missing chunks: {}".format(missing[:20]))
        filename = "simulation.sub" if action == "submit" else "merge.sub"
        return run_logged(["condor_submit", str(directory / filename)], directory, action)
    raise ValueError("Unknown workflow action")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("job", "local", "merge", "check", "submit", "submit-merge"))
    parser.add_argument("--manifest")
    parser.add_argument("--run-config", default=str(PROJECT / "config" / "run_config.json"))
    parser.add_argument("job_id", type=int, nargs="?")
    args = parser.parse_args()
    try:
        manifest = Path(args.manifest) if args.manifest else run_directory(args.run_config) / "manifest.json"
        sys.exit(execute(args.action, manifest, args.job_id))
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, "Workflow error: {}\n".format(error))
