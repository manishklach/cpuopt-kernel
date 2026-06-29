from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from cpuoptctl.cpuopt_discovery import discover
from cpuoptctl.cpuopt_recommend import recommend_profile
from cpuoptctl.cpuoptctl import cmd_recommend


FIXTURES = Path(__file__).parent / "fixtures"
WORKLOADS = Path(__file__).resolve().parents[1] / "examples" / "workloads"


class RecommendTests(unittest.TestCase):
    def test_intel_latency_recommendation(self) -> None:
        data = discover(sysfs_root=str(FIXTURES / "intel_hwp"))
        report = recommend_profile(data, workload="latency", workload_dir=str(WORKLOADS))
        self.assertEqual(report["recommended_profile"], "latency")
        self.assertEqual(report["confidence"], "high")

    def test_llama_inference_maps_to_ai_inference(self) -> None:
        data = discover(sysfs_root=str(FIXTURES / "intel_hwp"))
        report = recommend_profile(data, workload="llama-inference", workload_dir=str(WORKLOADS))
        self.assertEqual(report["recommended_profile"], "ai-inference")

    def test_missing_thermal_lowers_confidence(self) -> None:
        data = discover(sysfs_root=str(FIXTURES / "basic_cpufreq"))
        report = recommend_profile(data, workload="kernel-build", workload_dir=str(WORKLOADS))
        self.assertEqual(report["confidence"], "medium")
        self.assertTrue(any("Thermal zones are missing" in item for item in report["warnings"]))

    def test_amd_avoids_intel_specific_guidance(self) -> None:
        data = discover(sysfs_root=str(FIXTURES / "amd_pstate"))
        report = recommend_profile(data, workload="kernel-build", workload_dir=str(WORKLOADS))
        self.assertTrue(any("Intel-specific" in item for item in report["unsupported_features"]))

    def test_recommend_command_json(self) -> None:
        args = type(
            "Args",
            (),
            {
                "sysfs_root": str(FIXTURES / "intel_hwp"),
                "sysfs_root_local": None,
                "workload": "llama-inference",
                "workload_dir": str(WORKLOADS),
                "json": True,
            },
        )()
        buf = io.StringIO()
        with redirect_stdout(buf):
            cmd_recommend(args)
        output = buf.getvalue()
        self.assertIn('"recommended_profile": "ai-inference"', output)
        self.assertIn('"suggested_dry_run_command"', output)

    def test_epp_already_optimal_reason(self) -> None:
        data = discover(sysfs_root=str(FIXTURES / "intel_hwp"))
        report = recommend_profile(data, workload="balanced", workload_dir=str(WORKLOADS))
        self.assertTrue(any("Current EPP already matches" in item for item in report["reasons"]))


if __name__ == "__main__":
    unittest.main()
