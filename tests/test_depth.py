from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from cpuoptctl.cpuopt_discovery import discover
from cpuoptctl.cpuopt_doctor import build_doctor_report, format_doctor_report
from cpuoptctl.cpuopt_explain import format_profile_explanation
from cpuoptctl.cpuopt_msr import decode_intel_msrs
from cpuoptctl.cpuopt_profiles import propose_profile
from cpuoptctl.cpuoptctl import _format_diff, cmd_compare, cmd_intel_hwp


FIXTURES = Path(__file__).parent / "fixtures"


class DepthFeatureTests(unittest.TestCase):
    def test_doctor_finds_intel_signals(self) -> None:
        data = discover(sysfs_root=str(FIXTURES / "intel_hwp"))
        findings = build_doctor_report(data, state_dir=str(FIXTURES / "missing-state"), dev_root=str(FIXTURES / "missing-dev"), is_root=False)
        rendered = format_doctor_report(findings)
        self.assertIn("[OK] intel_pstate active", rendered)
        self.assertIn("[WARN] turbo disabled", rendered)

    def test_explain_output_contains_intent_and_limits(self) -> None:
        rendered = format_profile_explanation("performance")
        self.assertIn("Intent:", rendered)
        self.assertIn("Safety limits:", rendered)
        self.assertIn("Do not write raw MSRs", rendered)

    def test_dry_run_diff_output(self) -> None:
        root = FIXTURES / "intel_hwp"
        data = discover(sysfs_root=str(root))
        proposal = propose_profile(data, "performance", sysfs_root=str(root))
        rendered = _format_diff(proposal["writes"])
        self.assertIn("Planned CPUOpt changes", rendered)
        self.assertIn("current:", rendered)
        self.assertIn("new:", rendered)

    def test_msr_decoder_refuses_without_safe_or_device(self) -> None:
        unsafe = decode_intel_msrs(dev_root=str(FIXTURES / "missing-dev"), safe=False, is_root=True)
        self.assertFalse(unsafe["available"])
        self.assertIn("--safe", unsafe["reason"])
        missing = decode_intel_msrs(dev_root=str(FIXTURES / "missing-dev"), safe=True, is_root=True)
        self.assertFalse(missing["available"])
        self.assertIn("MSR device not present", missing["reason"])

    def test_intel_hwp_report_handles_missing_msr(self) -> None:
        args = type(
            "Args",
            (),
            {
                "sysfs_root": str(FIXTURES / "intel_hwp"),
                "sysfs_root_local": None,
                "dev_root": str(FIXTURES / "missing-dev"),
                "safe_msr": True,
            },
        )()
        buf = io.StringIO()
        with redirect_stdout(buf):
            cmd_intel_hwp(args)
        output = buf.getvalue()
        self.assertIn("Intel HWP Report", output)
        self.assertIn("HWP MSR read available: no", output)

    def test_compare_handles_missing_benchmark(self) -> None:
        args = type(
            "Args",
            (),
            {
                "profile_a": "balanced",
                "profile_b": "performance",
                "benchmark": "missing-bench",
                "duration": 30,
                "json": False,
                "sysfs_root": str(FIXTURES / "intel_hwp"),
                "sysfs_root_local": None,
            },
        )()
        buf = io.StringIO()
        with redirect_stdout(buf):
            cmd_compare(args)
        output = buf.getvalue()
        self.assertIn("Profile comparison unavailable", output)


if __name__ == "__main__":
    unittest.main()
