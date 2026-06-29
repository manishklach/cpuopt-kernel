from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from cpuoptctl.cpuopt_apply import state_path
from cpuoptctl.cpuopt_discovery import discover
from cpuoptctl.cpuopt_profiles import propose_profile
from cpuoptctl.cpuoptctl import cmd_profile

FIXTURES = Path(__file__).parent / "fixtures"


class ProfileTests(unittest.TestCase):
    def test_performance_profile_proposes_expected_writes(self) -> None:
        root = FIXTURES / "intel_hwp"
        data = discover(sysfs_root=str(root))
        proposal = propose_profile(data, "performance", sysfs_root=str(root))
        values = {Path(item.path).name: item.value for item in proposal["writes"]}
        self.assertEqual(values["energy_performance_preference"], "performance")
        self.assertEqual(values["scaling_governor"], "performance")
        self.assertEqual(values["no_turbo"], "0")

    def test_invalid_epp_value_is_never_written(self) -> None:
        root = FIXTURES / "basic_cpufreq"
        data = discover(sysfs_root=str(root))
        proposal = propose_profile(data, "performance", sysfs_root=str(root))
        names = [Path(item.path).name for item in proposal["writes"]]
        self.assertNotIn("energy_performance_preference", names)

    def test_restore_snapshot_is_created(self) -> None:
        root = FIXTURES / "intel_hwp"
        with tempfile.TemporaryDirectory() as temp_dir:
            sysfs_root = Path(temp_dir) / "sysfs"
            shutil.copytree(root, sysfs_root)
            args = type(
                "Args",
                (),
                {
                    "sysfs_root": str(sysfs_root),
                    "state_dir": temp_dir,
                    "profile_name": "performance",
                    "allow_idle_tuning": False,
                    "allow_fan_control": False,
                    "experimental_fan_write": False,
                    "allow_turbo_disable": False,
                    "dry_run": False,
                    "json": False,
                },
            )()
            cmd_profile(args)
            snapshot = state_path(temp_dir)
            self.assertTrue(snapshot.exists())
            data = json.loads(snapshot.read_text(encoding="utf-8"))
            self.assertGreater(len(data["entries"]), 0)


if __name__ == "__main__":
    unittest.main()
