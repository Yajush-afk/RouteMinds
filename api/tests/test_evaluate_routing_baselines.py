from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from api.training.evaluate_routing_baselines import evaluate_baselines


class EvaluateRoutingBaselinesTests(unittest.TestCase):
    def test_evaluation_writes_expected_metric_sections(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "baseline_eval.json"

            payload = evaluate_baselines(
                "api/training/config/default_config.toml",
                output_path,
            )

            self.assertTrue(output_path.exists())
            self.assertIn("segment_metrics", payload)
            self.assertIn("trip_metrics", payload)
            self.assertIn("reliability_metrics", payload)
            self.assertIn("static_schedule", payload["segment_metrics"])
            self.assertIn("current_mean_eta_ml", payload["segment_metrics"])
            self.assertIn("reliability_adjusted_ml", payload["trip_metrics"])


if __name__ == "__main__":
    unittest.main()
