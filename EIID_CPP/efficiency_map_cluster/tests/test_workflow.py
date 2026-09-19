"""不依赖 Geant4 的自检；临时数据只写入系统临时目录。"""
import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "cluster"))
import prepare_jobs as planner
import workflow


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.sim = planner.read_json(PROJECT / "tests/fixtures/sim_config.json")
        self.run = {"threads": 4, "jobs": 2, "events_per_chunk": 70000, "master_seed": 20260913, "output_directory": "../runs/smoke_001"}

    def test_exact_partition(self):
        self.run["events_per_chunk"] = 100001
        manifest = planner.build_manifest(self.sim, self.run)
        self.assertEqual([x["event_count"] for x in manifest["chunks"]], [100001, 100001, 79998])
        self.assertEqual(sum(x["event_count"] for x in manifest["chunks"]), 280000)
        self.assertEqual([x["job_id"] for x in manifest["chunks"]], [0, 1, 0])

    def test_large_integer(self):
        self.sim["grid"]["particles_per_cell"] = 10_000_000_000
        self.run["events_per_chunk"] = 1000000000
        self.assertEqual(planner.build_manifest(self.sim, self.run)["total_events"], 280000000000)

    def test_reject_invalid_parameters(self):
        for value in (-1, 0, 1.5, True, 1 << 64):
            self.sim["grid"]["particles_per_cell"] = value
            with self.assertRaises(ValueError):
                planner.build_manifest(self.sim, self.run)

    def test_snapshot_and_condor(self):
        with tempfile.TemporaryDirectory(prefix="eff-plan-") as temp:
            directory = Path(temp)
            cluster = planner.read_json(PROJECT / "config/cluster_config.json")
            cluster["target_os"] = "EL9"
            self.run["output_directory"] = "result"
            for name, data in [("sim", self.sim), ("run", self.run), ("cluster", cluster)]:
                (directory / (name + ".json")).write_text(json.dumps(data), encoding="utf-8")
            args = [directory / (name + ".json") for name in ("sim", "run", "cluster")]
            path = planner.prepare(*args)
            campaign_id = planner.read_json(path)["campaign_id"]
            self.assertEqual(planner.prepare(*args), path)
            self.assertEqual(planner.read_json(path)["campaign_id"], campaign_id)
            sub = (path.parent / "simulation.sub").read_text()
            self.assertIn("should_transfer_files = NO", sub)
            self.assertIn("request_cpus = 4", sub)
            self.assertIn('+SJTU_JOB_OS = "EL9"', sub)
            self.assertNotIn("@@", sub)
            cluster["target_os"] = "EL7"
            args[2].write_text(json.dumps(cluster), encoding="utf-8")
            planner.prepare(*args)
            old_os = (path.parent / "simulation.sub").read_text()
            self.assertIn('OpSysAndVer =?= "CentOS7"', old_os)
            self.assertNotIn('+SJTU_JOB_OS = "EL9"', old_os)
            self.run["threads"] = 8
            args[1].write_text(json.dumps(self.run), encoding="utf-8")
            with self.assertRaises(ValueError):
                planner.prepare(*args)

    def test_stdout_stderr_and_exit_status(self):
        with tempfile.TemporaryDirectory(prefix="eff-log-") as temp:
            command = [sys.executable, "-u", "-c", "import sys; print('stdout-marker'); print('stderr-marker',file=sys.stderr); sys.exit(7)"]
            for attempt in range(2):
                self.assertEqual(workflow.run_logged(command, temp, "job_0001"), 7)
            logs = list((Path(temp) / "logs").glob("*.log"))
            self.assertEqual(len(logs), 2)
            for log in logs:
                text = log.read_text()
                for marker in ("stdout-marker", "stderr-marker", "exit_status=7"):
                    self.assertIn(marker, text)

    @unittest.skipUnless(os.name == "posix", "POSIX flock test")
    def test_duplicate_job_lock(self):
        with tempfile.TemporaryDirectory(prefix="eff-lock-") as temp:
            path = Path(temp) / "job.lock"
            with workflow.job_lock(path):
                with self.assertRaises(OSError):
                    with workflow.job_lock(path):
                        pass

    def test_job_argument_parser(self):
        result = subprocess.run([sys.executable, str(PROJECT / "cluster/workflow.py"), "job", "--manifest", "missing.json", "0"], capture_output=True, text=True)
        self.assertNotIn("unrecognized arguments", result.stderr)


if __name__ == "__main__":
    unittest.main()
