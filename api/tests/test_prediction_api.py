from __future__ import annotations

import unittest
from unittest.mock import patch

import httpx

from api.app.core.config import settings
from api.app.main import app
from api.app.services.prediction_service import PredictionService


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
            predictions,
            [
                {
                    "predicted_actual_segment_minutes": 10.5,
                    "predicted_segment_delay_minutes": 9.1,
                    "segment_uncertainty": predictions[0]["segment_uncertainty"],
                    "segment_reliability_score": predictions[0]["segment_reliability_score"],
                    "congestion_proxy_ratio": predictions[0]["congestion_proxy_ratio"],
                    "congestion_proxy_percent": predictions[0]["congestion_proxy_percent"],
                    "predicted_eta_lower_minutes": predictions[0]["predicted_eta_lower_minutes"],
                    "predicted_eta_upper_minutes": predictions[0]["predicted_eta_upper_minutes"],
                },
                {
                    "predicted_actual_segment_minutes": 8.0,
                    "predicted_segment_delay_minutes": 6.6,
                    "segment_uncertainty": predictions[1]["segment_uncertainty"],
                    "segment_reliability_score": predictions[1]["segment_reliability_score"],
                    "congestion_proxy_ratio": predictions[1]["congestion_proxy_ratio"],
                    "congestion_proxy_percent": predictions[1]["congestion_proxy_percent"],
                    "predicted_eta_lower_minutes": predictions[1]["predicted_eta_lower_minutes"],
                    "predicted_eta_upper_minutes": predictions[1]["predicted_eta_upper_minutes"],
                },
            ],
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

        self.assertEqual(predictions[0]["predicted_actual_segment_minutes"], 0.01)
        self.assertEqual(predictions[0]["predicted_eta_lower_minutes"], 0.01)


class PredictionApiTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.original_model_path = settings.MODEL_PATH
        self.original_schema_path = settings.SCHEMA_PATH

    def tearDown(self) -> None:
        settings.MODEL_PATH = self.original_model_path
        settings.SCHEMA_PATH = self.original_schema_path

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
