from __future__ import annotations

import unittest
from pathlib import Path

from cpuoptctl.cpuopt_discovery import discover

FIXTURES = Path(__file__).parent / "fixtures"


class DiscoveryTests(unittest.TestCase):
    def test_discovery_finds_intel_epp(self) -> None:
        data = discover(sysfs_root=str(FIXTURES / "intel_hwp"))
        self.assertEqual(data["vendor"], "GenuineIntel")
        self.assertEqual(data["policies"][0]["energy_performance_preference"], "balance_performance")
        self.assertIn("performance", data["policies"][0]["energy_performance_available_preferences"])

    def test_missing_paths_do_not_crash(self) -> None:
        data = discover(sysfs_root=str(FIXTURES / "basic_cpufreq"))
        self.assertEqual(data["vendor"], "GenuineIntel")
        self.assertEqual(len(data["thermal"]["thermal_zones"]), 0)

    def test_amd_discovery_detects_vendor(self) -> None:
        data = discover(sysfs_root=str(FIXTURES / "amd_pstate"))
        self.assertEqual(data["vendor"], "AuthenticAMD")
        self.assertIn("AMD", " ".join(data.get("vendor_notes", [])))


if __name__ == "__main__":
    unittest.main()
