from __future__ import annotations

import io
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from dataclasses import replace
from pathlib import Path

from cpuoptctl.cpuopt_apply import apply_writes, state_path, write_log_path
from cpuoptctl.cpuopt_discovery import discover
from cpuoptctl.cpuopt_profiles import propose_profile
from cpuoptctl.cpuoptctl import cmd_profile, cmd_restore


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
            self.assertFalse(state_path(temp_dir).exists())
            self.assertFalse(write_log_path(temp_dir).exists())
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

    def test_apply_revalidates_allowed_values(self) -> None:
        root = FIXTURES / "intel_hwp"
        data = discover(sysfs_root=str(root))
        proposal = propose_profile(data, "performance", sysfs_root=str(root))
        epp_write = next(item for item in proposal["writes"] if item.path.endswith("energy_performance_preference"))
        invalid_write = replace(epp_write, valid_values=("balance_power",))
        with tempfile.TemporaryDirectory() as temp_dir:
            results = apply_writes([invalid_write], temp_dir, dry_run=False)
            self.assertEqual(results[0].get("error"), "invalid-value")
            target = Path(invalid_write.path)
            self.assertEqual(target.read_text(encoding="utf-8").strip(), "balance_performance")

    def test_restore_creates_pre_restore_snapshot(self) -> None:
        root = FIXTURES / "intel_hwp"
        with tempfile.TemporaryDirectory() as temp_dir:
            sysfs_root = Path(temp_dir) / "sysfs"
            shutil.copytree(root, sysfs_root)
            profile_args = type(
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
                    "diff": False,
                },
            )()
            cmd_profile(profile_args)
            restore_args = type(
                "Args",
                (),
                {
                    "sysfs_root": str(sysfs_root),
                    "state_dir": temp_dir,
                    "sysfs_root_local": None,
                    "state_dir_local": None,
                },
            )()
            buf = io.StringIO()
            with redirect_stdout(buf):
                ret = cmd_restore(restore_args)
            self.assertEqual(ret, 0)
            pre_restore = Path(temp_dir) / "last_state.pre-restore.json"
            self.assertTrue(pre_restore.exists())
            output = buf.getvalue()
            self.assertIn("Restored", output)


if __name__ == "__main__":
    unittest.main()
