import unittest

from eiid.batch import GIB, MemoryGuardPolicy, SystemMemoryMonitor


class MemoryTests(unittest.TestCase):
    def test_safe_worker_capacity_respects_memory_and_upper_bound(self):
        policy = MemoryGuardPolicy(
            enabled=True,
            minimum_available_gib=5.0,
            estimated_worker_peak_gib=4.0,
        )
        self.assertEqual(policy.safe_worker_capacity(25 * GIB, 5), 5)
        self.assertEqual(policy.safe_worker_capacity(17 * GIB, 5), 3)
        self.assertEqual(policy.safe_worker_capacity(8 * GIB, 5), 0)

    def test_proc_meminfo_is_converted_to_bytes(self):
        values = SystemMemoryMonitor.parse_proc_meminfo(
            "MemTotal: 1000 kB\nMemAvailable: 250 kB\n"
        )
        self.assertEqual(values["MemTotal"], 1000 * 1024)
        self.assertEqual(values["MemAvailable"], 250 * 1024)


if __name__ == "__main__":
    unittest.main()

