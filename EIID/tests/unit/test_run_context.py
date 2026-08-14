from datetime import datetime, timezone
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

from eiid.application import RunContext, RunIdFactory


class FakeConfig:
    def __init__(self, root):
        root = Path(root).resolve()
        self.paths = SimpleNamespace(
            project_root=root,
            output_root=root / "runs",
            log_root=root / "logs",
        )

    def as_dict(self):
        return {"schema_version": "test", "value": 1}


class RunContextTests(unittest.TestCase):
    def test_run_id_contains_kind_and_stable_configuration_hash(self):
        moment = datetime(2026, 1, 2, 3, 4, 5, 6789, tzinfo=timezone.utc)
        first = RunIdFactory.generate(
            "stage4_lmmlem",
            {"b": 2, "a": 1},
            timestamp_utc=moment,
            entropy="abc123",
        )
        second = RunIdFactory.generate(
            "stage4_lmmlem",
            {"a": 1, "b": 2},
            timestamp_utc=moment,
            entropy="abc123",
        )
        self.assertEqual(first, second)
        self.assertIn("stage4_lmmlem", first)

    def test_success_writes_snapshot_manifest_and_marker_without_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            config = FakeConfig(directory)
            context = RunContext.start(config, "unit", run_id="unit_success")
            context.mark_success({"answer": 42}, stop_reason="unit_complete")
            self.assertTrue(context.paths.configuration_snapshot_path.is_file())
            self.assertTrue(context.paths.success_marker_path.is_file())
            self.assertTrue(context.paths.log_path.is_file())
            manifest = json.loads(
                context.paths.manifest_path.read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["status"], "success")
            self.assertEqual(manifest["stop_reason"], "unit_complete")
            with self.assertRaises(FileExistsError):
                RunContext.start(config, "unit", run_id="unit_success")

    def test_failure_writes_failure_marker(self):
        with tempfile.TemporaryDirectory() as directory:
            context = RunContext.start(
                FakeConfig(directory), "unit", run_id="unit_failure"
            )
            error = RuntimeError("expected")
            context.mark_failure(error)
            payload = json.loads(
                context.paths.failure_marker_path.read_text(encoding="utf-8")
            )
            self.assertEqual(payload["error_type"], "RuntimeError")
            self.assertEqual(payload["status"], "failure")


if __name__ == "__main__":
    unittest.main()
