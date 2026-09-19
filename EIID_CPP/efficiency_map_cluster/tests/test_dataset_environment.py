"""测试启动脚本的数据路径恢复；只使用临时目录和元数据脚本，不模拟物理库。"""
import contextlib
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import unittest

PROJECT = Path(__file__).resolve().parents[1]
BASH = shutil.which("bash")


def shell_path(path):
    path = Path(path).resolve()
    if os.name == "nt":
        return "/" + path.drive[0].lower() + path.as_posix()[2:]
    return str(path)


@unittest.skipUnless(BASH, "Bash required")
class DatasetEnvironmentTests(unittest.TestCase):
    @contextlib.contextmanager
    def fixture(self):
        scratch = PROJECT / "build-config-tests"
        scratch.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="eff-data-", dir=scratch) as temp:
            root = Path(temp)
            for name in ("cluster", "build", "selected/bin", "data with spaces/G4EMLOW8.5",
                         "data with spaces/G4ENSDFSTATE2.3", "old_data", "wrong_bin"):
                (root / name).mkdir(parents=True, exist_ok=True)
            shutil.copyfile(PROJECT / "cluster/setup_env.sh", root / "cluster/setup_env.sh")
            (root / "build/configure.ok").touch()
            setup = root / "selected/bin/geant4.sh"
            setup.write_text("#!/usr/bin/env bash\ntrue\n", encoding="utf-8")
            tool = root / "selected/bin/geant4-config"
            rows = ["G4EMLOW G4LEDATA " + shell_path(root / "data with spaces/G4EMLOW8.5"),
                    "G4ENSDFSTATE G4ENSDFSTATEDATA " + shell_path(root / "data with spaces/G4ENSDFSTATE2.3")]

            def write_tool(lines=None, fail=False):
                text = '#!/usr/bin/env bash\n[[ "$#" == 1 && "$1" == --datasets ]] || exit 64\n'
                text += "exit 5\n" if fail else "printf '%s\\n' " + " ".join(shlex.quote(row) for row in (rows if lines is None else lines)) + "\n"
                tool.write_text(text, encoding="utf-8")
                tool.chmod(0o755)

            write_tool()
            wrong = root / "wrong_bin/geant4-config"
            wrong.write_text("#!/usr/bin/env bash\necho WRONG_VERSION >&2\nexit 42\n", encoding="utf-8")
            wrong.chmod(0o755)
            (root / "build/runtime_paths.sh").write_text(
                "export EFF_GEANT4_SH=" + shlex.quote(shell_path(setup)) + "\nexport EFF_LIBRARY_PATH=''\n",
                encoding="utf-8")

            def run(command='printf "%s|%s" "${G4LEDATA-unset}" "${G4ENSDFSTATEDATA-unset}"'):
                env = os.environ.copy()
                env["G4LEDATA"] = shell_path(root / "old_data")
                env["G4ENSDFSTATEDATA"] = shell_path(root / "old_data")
                return subprocess.run([BASH, shell_path(root / "cluster/setup_env.sh"), BASH, "-c", command],
                                      env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20)

            # 让“错误版本”从包装器开始执行时就在 PATH 首位。
            setup.write_text("#!/usr/bin/env bash\nexport PATH=" + shlex.quote(shell_path(root / "wrong_bin")) + ':"$PATH"\n', encoding="utf-8")
            yield root, rows, setup, tool, write_tool, run

    def test_restore_installed_data_when_setup_exports_no_dataset(self):
        with self.fixture() as (root, rows, setup, tool, write_tool, run):
            result = run()
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, shell_path(root / "data with spaces/G4EMLOW8.5") + "|" +
                             shell_path(root / "data with spaces/G4ENSDFSTATE2.3"))
            self.assertNotIn("WRONG_VERSION", result.stderr)

    def test_keep_valid_path_provided_by_selected_setup(self):
        with self.fixture() as (root, rows, setup, tool, write_tool, run):
            setup.write_text("export G4LEDATA=" + shlex.quote(shell_path(root / "old_data")) + "\n", encoding="utf-8")
            result = run()
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.split("|")[0], shell_path(root / "old_data"))

    def test_missing_directory_is_not_exported_and_does_not_block_root_tools(self):
        with self.fixture() as (root, rows, setup, tool, write_tool, run):
            write_tool(["G4EMLOW G4LEDATA " + shell_path(root / "missing"), rows[1]])
            result = run()
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(result.stdout.startswith("unset|"))
            self.assertIn("not found:", result.stderr)
            self.assertFalse((root / "missing").exists())

    def test_failed_query_stops_before_child_command(self):
        with self.fixture() as (root, rows, setup, tool, write_tool, run):
            write_tool(fail=True)
            result = run("echo CHILD_RAN")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Cannot read dataset list", result.stderr)
            self.assertNotIn("CHILD_RAN", result.stdout)

    def test_invalid_environment_variable_is_rejected(self):
        with self.fixture() as (root, rows, setup, tool, write_tool, run):
            write_tool(["bad PATH /tmp"])
            result = run("echo CHILD_RAN")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Invalid Geant4 dataset entry", result.stderr)
            self.assertNotIn("CHILD_RAN", result.stdout)

    def test_missing_selected_config_does_not_use_other_installation(self):
        with self.fixture() as (root, rows, setup, tool, write_tool, run):
            tool.unlink()
            result = run("echo CHILD_RAN")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("is not executable", result.stderr)
            self.assertNotIn("CHILD_RAN", result.stdout)
            self.assertNotIn("WRONG_VERSION", result.stderr)


if __name__ == "__main__":
    unittest.main()
