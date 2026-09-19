"""构建入口回归测试；测试替身仅模拟 cmake 的退出状态，不冒充 ROOT/Geant4。"""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
BASH = shutil.which("bash")
MAKE = shutil.which("make")
CMAKE = os.environ.get("EFF_TEST_CMAKE") or shutil.which("cmake")
CXX = shutil.which("g++")


def shell_path(path):
    # Windows 下让 MSYS Bash 使用 /d/... 形式；Linux 原样返回。
    path = Path(path).resolve()
    if os.name == "nt":
        return "/" + path.drive[0].lower() + path.as_posix()[2:]
    return str(path)


class BuildConfigTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scratch = PROJECT / "build-config-tests"
        cls.scratch.mkdir(exist_ok=True)

    def test_tree_reader_link_is_public(self):
        root = (PROJECT / "CMakeLists.txt").read_text(encoding="utf-8")
        common = (PROJECT / "common/CMakeLists.txt").read_text(encoding="utf-8")
        self.assertIn("COMPONENTS Core RIO Tree TreePlayer", root)
        self.assertIn("PUBLIC eff_common ROOT::Core ROOT::RIO ROOT::Tree ROOT::TreePlayer eff_runtime", common)

    def test_probe_has_flushed_stages_and_checks_libraries_first(self):
        probe = (PROJECT / "cmake/dependency_probe.cpp").read_text(encoding="utf-8")
        self.assertIn("std::fflush(stderr)", probe)
        self.assertLess(probe.index('stage("01'), probe.index("gROOT->SetBatch"))
        self.assertIn('stage("16 leaving main', probe)
        source = (PROJECT / "cmake/CheckDependencies.cmake").read_text(encoding="utf-8")
        self.assertLess(source.index('"${EFF_LDD}" -r'), source.index('eff_run_probe("${PROBE}"'))
        self.assertNotIn("Use a compatible compiler/runtime (CXX", source)

    def test_geant4_probe_does_not_create_orphan_run(self):
        # 源码约束回归：没有 RunManager 时不得孤立创建 G4Run。
        # 这不是 Geant4 运行测试；真实库调用仍由服务器 make configure 验证。
        probe = (PROJECT / "cmake/dependency_probe.cpp").read_text(encoding="utf-8")
        self.assertIn("#include <G4RunManager.hh>", probe)
        self.assertIn("G4RunManager::GetRunManager() != nullptr", probe)
        self.assertNotIn("#include <G4Run.hh>", probe)
        self.assertNotRegex(probe, r"\bG4Run\s+[a-zA-Z_]\w*\s*[;{(]")
        self.assertNotRegex(probe, r"\bnew\s+G4Run\b")
        self.assertNotIn("std::_Exit", probe)
        self.assertNotIn("std::quick_exit", probe)

    @unittest.skipUnless(CMAKE and CXX, "CMake and g++ required")
    def test_probe_failure_classification_and_timeout_output(self):
        # 真正编译、运行一个只用标准库的小程序，检查退出码/超时/日志。
        # 它不是 ROOT/Geant4 的替代实现，不能证明物理依赖栈可用。
        source = (PROJECT / "cmake/CheckDependencies.cmake").read_text(encoding="utf-8")
        helper = "function(eff_run_probe" + source.split("function(eff_run_probe", 1)[1].split("endfunction()", 1)[0] + "endfunction()\n"
        with tempfile.TemporaryDirectory(prefix="eff-probe-", dir=self.scratch) as temp:
            directory = Path(temp)
            (directory / "dependency-check").mkdir()
            cpp = directory / "probe.cpp"
            cpp.write_text('''#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <thread>
#include <chrono>
int main()
{
    const char* mode = std::getenv("EFF_TEST_PROBE_MODE");
    if (std::strcmp(mode, "silent") != 0)
    {
        std::fputs("[dependency-probe] test reached main; starting next step\\n", stderr);
        std::fflush(stderr);
    }
    if (std::strcmp(mode, "timeout") == 0 || std::strcmp(mode, "silent") == 0)
    {
        std::this_thread::sleep_for(std::chrono::seconds(10));
    }
    return std::strcmp(mode, "failure") == 0 ? 3 : 0;
}
''', encoding="utf-8")
            executable = directory / ("probe.exe" if os.name == "nt" else "probe")
            compiled = subprocess.run([CXX, "-std=c++17", str(cpp), "-o", str(executable)], capture_output=True, text=True)
            self.assertEqual(compiled.returncode, 0, compiled.stdout + compiled.stderr)
            script = helper + '\nset(CMAKE_BINARY_DIR "' + directory.as_posix() + '")\n'
            script += 'set(EFF_LOG "' + (directory / "check.log").as_posix() + '")\n'
            script += 'set(EFF_PROBE_TIMEOUT_SECONDS 1)\n'
            script += 'eff_run_probe("' + executable.as_posix() + '" "" OK WHY)\n'
            script += 'file(WRITE "' + (directory / "status.txt").as_posix() + '" "${OK}\\n${WHY}")\n'
            (directory / "check.cmake").write_text(script, encoding="utf-8")
            for mode in ("success", "failure", "timeout", "silent"):
                with self.subTest(mode=mode):
                    env = os.environ.copy()
                    env["EFF_TEST_PROBE_MODE"] = mode
                    result = subprocess.run([CMAKE, "-P", str(directory / "check.cmake")], env=env,
                                            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    status = (directory / "status.txt").read_text(encoding="utf-8")
                    self.assertEqual(status.startswith("TRUE"), mode == "success")
                    if mode == "failure":
                        self.assertIn("status: 3", status)
                    if mode in ("timeout", "silent"):
                        self.assertIn("timed out", status)
                        self.assertIn("AFTER successful linking", status)
                        expected = "test reached main" if mode == "timeout" else "main entry is not confirmed"
                        self.assertIn(expected, status)
                    if mode != "silent":
                        self.assertIn("test reached main", (directory / "dependency-check/probe.stderr.log").read_text())

    @unittest.skipUnless(CMAKE, "CMake required")
    def test_loaded_library_path_checks(self):
        # 用人工 ldd 文本测试路径比较函数；这不是运行 ROOT/Geant4 集成测试。
        source = (PROJECT / "cmake/CheckDependencies.cmake").read_text(encoding="utf-8")
        helper = "function(eff_loaded_matches" + source.split("function(eff_loaded_matches", 1)[1].split("endfunction()", 1)[0] + "endfunction()\n"
        with tempfile.TemporaryDirectory(prefix="eff-ldd-", dir=self.scratch) as temp:
            directory = Path(temp)
            library = directory / "libCore.so.6.40.02"
            library.touch()
            path = library.as_posix()
            script = helper + '\nset(EFF_LOG "' + (directory / "check.log").as_posix() + '")\n'
            script += 'eff_loaded_matches("libCore.so.6.40.02 => ' + path + ' (0x1234)" "libCore\\\\.so" "' + path + '" OK)\n'
            script += 'if(NOT OK)\nmessage(FATAL_ERROR "Matching runtime was rejected")\nendif()\n'
            script += 'eff_loaded_matches("libCore.so => /wrong/libCore.so (0x1234)" "libCore\\\\.so" "' + path + '" OK)\n'
            script += 'if(OK)\nmessage(FATAL_ERROR "Wrong runtime was accepted")\nendif()\n'
            script += 'eff_loaded_matches("libCore.so => not found" "libCore\\\\.so" "' + path + '" OK)\n'
            script += 'if(OK)\nmessage(FATAL_ERROR "Missing runtime was accepted")\nendif()\n'
            (directory / "check.cmake").write_text(script, encoding="utf-8")
            result = subprocess.run([CMAKE, "-P", str(directory / "check.cmake")], capture_output=True, text=True, encoding="utf-8", errors="replace")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(BASH, "Bash required")
    def test_failed_configure_invalidates_success_marker(self):
        with tempfile.TemporaryDirectory(prefix="eff-build-", dir=self.scratch) as temp:
            project = Path(temp)
            shutil.copyfile(PROJECT / "configure.sh", project / "configure.sh")
            (project / "config").mkdir()
            # 模拟 CMake 在失败前留下缓存、Makefile 甚至旧成功标记。
            (project / "config/environment.sh").write_text(
                "cmake() { printf 'simulated linker failure\\n'; touch build/CMakeCache.txt build/Makefile build/configure.ok; return 9; }\n",
                encoding="utf-8")
            result = subprocess.run([BASH, shell_path(project / "configure.sh")], capture_output=True, text=True, encoding="utf-8", errors="replace")
            self.assertEqual(result.returncode, 9, result.stdout + result.stderr)
            self.assertTrue((project / "build/CMakeCache.txt").is_file())
            self.assertFalse((project / "build/configure.ok").exists())
            logs = list((project / "build").glob("configure_*.log"))
            self.assertEqual(len(logs), 1)
            self.assertIn("simulated linker failure", logs[0].read_text())

    @unittest.skipUnless(MAKE, "make required")
    def test_make_refuses_cache_without_success(self):
        with tempfile.TemporaryDirectory(prefix="eff-make-", dir=self.scratch) as temp:
            project = Path(temp)
            shutil.copyfile(PROJECT / "Makefile", project / "Makefile")
            (project / "build").mkdir()
            (project / "build/CMakeCache.txt").touch()
            for target in ("all", "run-local"):
                result = subprocess.run([MAKE, target], cwd=project, capture_output=True, text=True, encoding="utf-8", errors="replace")
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Configuration is incomplete", result.stdout + result.stderr)
                self.assertNotIn("prepare_jobs.py", result.stdout)
            self.assertFalse((project / "runs").exists())

    @unittest.skipUnless(BASH, "Bash required")
    def test_runtime_path_and_no_current_directory_entry(self):
        with tempfile.TemporaryDirectory(prefix="eff-env-", dir=self.scratch) as temp:
            project = Path(temp)
            (project / "cluster").mkdir()
            (project / "build").mkdir()
            shutil.copyfile(PROJECT / "cluster/setup_env.sh", project / "cluster/setup_env.sh")
            (project / "build/configure.ok").touch()
            (project / "build/runtime_paths.sh").write_text(
                "export EFF_GEANT4_SH=''\nexport EFF_LIBRARY_PATH='/chosen/g4:/chosen/root'\n", encoding="utf-8")
            env = os.environ.copy()
            env.pop("LD_LIBRARY_PATH", None)
            env["G4FORCENUMBEROFTHREADS"] = "100"
            result = subprocess.run([BASH, shell_path(project / "cluster/setup_env.sh"),
                                     "bash", "-c", 'printf "%s|%s|%s" "$LD_LIBRARY_PATH" "$LD_BIND_NOW" "${G4FORCENUMBEROFTHREADS-unset}"'],
                                    env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, "/chosen/g4:/chosen/root|1|unset")
            (project / "build/configure.ok").unlink()
            result = subprocess.run([BASH, shell_path(project / "cluster/setup_env.sh"), "true"],
                                    capture_output=True, text=True, encoding="utf-8", errors="replace")
            self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
