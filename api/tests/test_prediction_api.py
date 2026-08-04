from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

import httpx

from api.app.core.config import settings
from api.app.main import app
from api.app.ml.model_bundle_v2 import QuantilePrediction
from api.app.services.prediction_service import PredictionService, _normalize_edge_identifier


def make_segment_payload() -> dict:
    return {
        "route_id": "10001",
        "from_stop_id": "3928",
        "to_stop_id": "3929",
        "stop_sequence": 1,
        "normalized_stop_position": 0.013514,
        "distance_to_prev_stop_km": 0.3528,
        "segment_start_scheduled_unix": 1742803800,
        "scheduled_segment_minutes": 1.4,
        "prev_segment_delay": 0.0,
        "rolling_segment_delay_3": 0.0,
    }


class PredictionServiceTests(unittest.TestCase):
    def test_normalize_edge_identifier_handles_common_serialization_artifacts(self) -> None:
        self.assertEqual(_normalize_edge_identifier(" 3928 "), "3928")
        self.assertEqual(_normalize_edge_identifier("3928.0"), "3928")
        self.assertEqual(_normalize_edge_identifier("R1"), "R1")

    def test_supports_segment_record_normalizes_identifier_format(self) -> None:
        service = PredictionService(
            model_path="artifacts/models/xgboost_segment_travel_time_model.joblib",
            schema_path="artifacts/models/xgboost_segment_travel_time_schema.json",
        )
        record = make_segment_payload()
        record["route_id"] = "10001.0"
        record["from_stop_id"] = " 3928"
        record["to_stop_id"] = "3929 "

        with patch(
            "api.app.services.prediction_service.load_supported_route_edges",
            return_value=frozenset({("10001", "3928", "3929")}),
        ):
            self.assertTrue(service.supports_segment_record(record))

    def test_service_returns_travel_time_and_delay_predictions(self) -> None:
        service = PredictionService(
            model_path="artifacts/models/xgboost_segment_travel_time_model.joblib",
            schema_path="artifacts/models/xgboost_segment_travel_time_schema.json",
        )
        records = [make_segment_payload(), make_segment_payload()]

        with patch.object(
            service.predictor,
            "predict_batch",
            return_value=[10.5, 8.0],
        ) as mock_predict_batch:
            predictions = service.predict_segments(records)

        mock_predict_batch.assert_called_once_with(records)
        self.assertEqual(
            [prediction["predicted_actual_segment_minutes"] for prediction in predictions],
            [10.5, 8.0],
        )
        self.assertEqual(
            [prediction["predicted_segment_delay_minutes"] for prediction in predictions],
            [9.1, 6.6],
        )
        self.assertTrue(all(prediction["prediction_source"] == "ml" for prediction in predictions))
        self.assertTrue(all(prediction["model_supported"] for prediction in predictions))
        self.assertTrue(all(prediction["model_version"] == "legacy-v1" for prediction in predictions))
        self.assertTrue(
            all(prediction["prediction_interval_method"] == "fallback" for prediction in predictions)
        )
        self.assertGreater(predictions[0]["segment_uncertainty"], 0.0)
        self.assertGreaterEqual(predictions[0]["segment_reliability_score"], 0.0)
        self.assertLessEqual(predictions[0]["segment_reliability_score"], 1.0)
        self.assertLessEqual(
            predictions[0]["predicted_eta_lower_minutes"],
            predictions[0]["predicted_actual_segment_minutes"],
        )
        self.assertGreaterEqual(
            predictions[0]["predicted_eta_upper_minutes"],
            predictions[0]["predicted_actual_segment_minutes"],
        )
        self.assertGreater(predictions[0]["congestion_proxy_ratio"], 1.0)

    def test_service_guardrails_clip_extreme_supported_prediction(self) -> None:
        service = PredictionService(
            model_path="artifacts/models/xgboost_segment_travel_time_model.joblib",
            schema_path="artifacts/models/xgboost_segment_travel_time_schema.json",
        )
        record = make_segment_payload()
        record["scheduled_segment_minutes"] = 5.0

        with patch.object(
            service.predictor,
            "predict_batch",
            return_value=[107.0],
        ):
            predictions = service.predict_segments([record])

        self.assertLess(predictions[0]["predicted_actual_segment_minutes"], 30.0)
        self.assertGreater(predictions[0]["predicted_actual_segment_minutes"], 5.0)
        self.assertEqual(predictions[0]["prediction_source"], "ml")
        self.assertTrue(predictions[0]["model_supported"])

    def test_unsupported_prediction_uses_guarded_ml_blend(self) -> None:
        service = PredictionService(
            model_path="artifacts/models/xgboost_segment_travel_time_model.joblib",
            schema_path="artifacts/models/xgboost_segment_travel_time_schema.json",
        )
        record = make_segment_payload()
        record["scheduled_segment_minutes"] = 5.0

        with patch.object(
            service.predictor,
            "predict_batch",
            return_value=[107.0],
        ):
            predictions = service.predict_segments_for_unsupported_edges([record])

        self.assertLess(predictions[0]["predicted_actual_segment_minutes"], 20.0)
        self.assertGreater(predictions[0]["predicted_actual_segment_minutes"], 5.0)
        self.assertEqual(predictions[0]["prediction_source"], "scheduled_fallback")
        self.assertFalse(predictions[0]["model_supported"])

    def test_service_clamps_negative_predicted_segment_minutes(self) -> None:
        service = PredictionService(
            model_path="artifacts/models/xgboost_segment_travel_time_model.joblib",
            schema_path="artifacts/models/xgboost_segment_travel_time_schema.json",
        )
        records = [make_segment_payload()]

        with patch.object(
            service.predictor,
            "predict_batch",
            return_value=[-3.0],
        ):
            predictions = service.predict_segments(records)

        self.assertGreaterEqual(predictions[0]["predicted_actual_segment_minutes"], 0.01)
        self.assertLess(
            predictions[0]["predicted_actual_segment_minutes"],
            records[0]["scheduled_segment_minutes"],
        )
        self.assertGreaterEqual(predictions[0]["predicted_eta_lower_minutes"], 0.01)
        self.assertEqual(predictions[0]["prediction_source"], "ml")

    def test_missing_configured_v2_bundle_falls_back_to_schedule(self) -> None:
        service = PredictionService(
            model_path="artifacts/models/xgboost_segment_travel_time_model.joblib",
            schema_path="artifacts/models/xgboost_segment_travel_time_schema.json",
            v2_manifest_path="/tmp/route-minds-missing-v2/manifest.json",
        )
        record = make_segment_payload()

        prediction = service.predict_segments([record])[0]

        self.assertEqual(
            prediction["predicted_actual_segment_minutes"],
            record["scheduled_segment_minutes"],
        )
        self.assertEqual(prediction["prediction_source"], "scheduled_fallback")
        self.assertEqual(prediction["model_version"], "schedule-fallback")

    def test_unpromoted_v2_bundle_falls_back_to_schedule(self) -> None:
        experimental_bundle = SimpleNamespace(
            manifest={
                "promotion_eligible": False,
                "promotion_blockers": ["realtime gate"],
            }
        )
        with patch(
            "api.app.services.prediction_service.MLV2ModelBundle",
            return_value=experimental_bundle,
        ):
            service = PredictionService(
                model_path="artifacts/models/xgboost_segment_travel_time_model.joblib",
                schema_path="artifacts/models/xgboost_segment_travel_time_schema.json",
                v2_manifest_path="experimental/manifest.json",
            )
            record = make_segment_payload()

            prediction = service.predict_segments([record])[0]

        self.assertEqual(
            prediction["predicted_actual_segment_minutes"],
            record["scheduled_segment_minutes"],
        )
        self.assertEqual(prediction["prediction_source"], "scheduled_fallback")

    def test_promoted_v2_bundle_returns_native_quantiles(self) -> None:
        promoted_bundle = SimpleNamespace(
            manifest={"promotion_eligible": True},
            model_version="test-v2",
            predict_batch=lambda records: [
                QuantilePrediction(
                    p10_minutes=1.2,
                    p50_minutes=1.8,
                    p90_minutes=2.6,
                    feature_quality_score=0.8,
                    live_context_used=False,
                )
                for _ in records
            ],
        )
        with patch(
            "api.app.services.prediction_service.MLV2ModelBundle",
            return_value=promoted_bundle,
        ):
            service = PredictionService(
                model_path="artifacts/models/xgboost_segment_travel_time_model.joblib",
                schema_path="artifacts/models/xgboost_segment_travel_time_schema.json",
                v2_manifest_path="promoted/manifest.json",
            )

        prediction = service.predict_segments([make_segment_payload()])[0]

        self.assertEqual(prediction["predicted_actual_segment_minutes"], 1.8)
        self.assertEqual(prediction["predicted_eta_lower_minutes"], 1.2)
        self.assertEqual(prediction["predicted_eta_upper_minutes"], 2.6)
        self.assertEqual(prediction["model_version"], "test-v2")
        self.assertEqual(prediction["prediction_interval_method"], "xgboost_quantile")


class PredictionApiTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.original_model_path = settings.MODEL_PATH
        self.original_schema_path = settings.SCHEMA_PATH
        self.original_v2_manifest_path = settings.MODEL_V2_MANIFEST_PATH
        settings.MODEL_V2_MANIFEST_PATH = ""

    def tearDown(self) -> None:
        settings.MODEL_PATH = self.original_model_path
        settings.SCHEMA_PATH = self.original_schema_path
        settings.MODEL_V2_MANIFEST_PATH = self.original_v2_manifest_path

    async def _post_segments(self, payload: dict) -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.post("/api/v1/predictions/segments", json=payload)

    async def test_valid_batch_request_returns_predictions(self) -> None:
        response = await self._post_segments({"segments": [make_segment_payload()]})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload["predictions"]), 1)
        self.assertIn("predicted_actual_segment_minutes", payload["predictions"][0])
        self.assertIn("predicted_segment_delay_minutes", payload["predictions"][0])
        self.assertIn("segment_uncertainty", payload["predictions"][0])
        self.assertIn("segment_reliability_score", payload["predictions"][0])
        self.assertIn("congestion_proxy_ratio", payload["predictions"][0])
        self.assertIn("congestion_proxy_percent", payload["predictions"][0])
        self.assertIn("predicted_eta_lower_minutes", payload["predictions"][0])
        self.assertIn("predicted_eta_upper_minutes", payload["predictions"][0])

    async def test_missing_required_field_returns_422(self) -> None:
        payload = make_segment_payload()
        payload.pop("from_stop_id")

        response = await self._post_segments({"segments": [payload]})

        self.assertEqual(response.status_code, 422)

    async def test_empty_segments_list_returns_422(self) -> None:
        response = await self._post_segments({"segments": []})

        self.assertEqual(response.status_code, 422)

    async def test_missing_model_artifact_returns_service_error(self) -> None:
        settings.MODEL_PATH = "artifacts/models/does_not_exist.joblib"
        settings.SCHEMA_PATH = "artifacts/models/xgboost_segment_travel_time_schema.json"

        response = await self._post_segments({"segments": [make_segment_payload()]})

        self.assertEqual(response.status_code, 503)
        self.assertIn("model artifact", response.json()["detail"].lower())

    async def test_missing_schema_artifact_returns_service_error(self) -> None:
        settings.MODEL_PATH = "artifacts/models/xgboost_segment_travel_time_model.joblib"
        settings.SCHEMA_PATH = "artifacts/models/does_not_exist_schema.json"

        response = await self._post_segments({"segments": [make_segment_payload()]})

        self.assertEqual(response.status_code, 503)
        self.assertIn("schema artifact", response.json()["detail"].lower())


if __name__ == "__main__":
    unittest.main()
