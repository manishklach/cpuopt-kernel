from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cpuoptctl.cpuopt_discovery import discover
from cpuoptctl.cpuopt_profiles import propose_profile
from cpuoptctl.cpuoptctl import cmd_profile


FIXTURES = Path(__file__).parent / "fixtures"


class SafetyTests(unittest.TestCase):
    def test_dry_run_does_not_write(self) -> None:
        root = FIXTURES / "intel_hwp"
        target = root / "devices" / "system" / "cpu" / "cpufreq" / "policy0" / "scaling_governor"
        before = target.read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as temp_dir:
            args = type(
                "Args",
                (),
                {
                    "sysfs_root": str(root),
                    "state_dir": temp_dir,
                    "profile_name": "performance",
                    "allow_idle_tuning": False,
                    "allow_fan_control": False,
                    "experimental_fan_write": False,
                    "allow_turbo_disable": False,
                    "dry_run": True,
                    "json": False,
                },
            )()
            cmd_profile(args)
        after = target.read_text(encoding="utf-8")
        self.assertEqual(before, after)

    def test_quiet_mode_does_not_fan_control_without_flag(self) -> None:
        data = discover(sysfs_root=str(FIXTURES / "intel_hwp"))
        proposal = propose_profile(data, "quiet", sysfs_root=str(FIXTURES / "intel_hwp"))
        joined = " ".join(item.reason for item in proposal["writes"])
        self.assertNotIn("fan", joined.lower())

    def test_latency_idle_tuning_is_opt_in(self) -> None:
        data = discover(sysfs_root=str(FIXTURES / "intel_hwp"))
        proposal = propose_profile(data, "latency", sysfs_root=str(FIXTURES / "intel_hwp"))
        paths = [item.path for item in proposal["writes"]]
        self.assertFalse(any(path.endswith("/disable") for path in paths))


if __name__ == "__main__":
    unittest.main()
