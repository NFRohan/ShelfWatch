"""ShelfWatch — Tests for the inference API."""

import io
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from PIL import Image


@pytest.fixture
def mock_model_manager():
    """Patch ModelManager so tests don't need actual weights."""
    with patch("inference.app.model_manager") as mock_mm:
        mock_mm.is_loaded = True
        mock_mm.runtime = "onnx-cpu"
        mock_mm.predict.return_value = [
            {
                "class": "objects",
                "confidence": 0.92,
                "bbox": [100.0, 200.0, 300.0, 400.0],
            }
        ]
        yield mock_mm


@pytest.fixture
def client(mock_model_manager):
    """TestClient with mocked model."""
    from inference.app import app
    return TestClient(app)


def _make_test_image() -> bytes:
    """Create a small JPEG in memory."""
    img = Image.new("RGB", (100, 100), color="red")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


class TestHealthEndpoint:
    def test_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["model_loaded"] is True
        assert data["runtime"] == "onnx-cpu"

    def test_includes_model_name(self, client):
        response = client.get("/health")
        data = response.json()
        assert "model" in data


class TestMetricsEndpoint:
    def test_returns_prometheus_format(self, client):
        response = client.get("/metrics")
        assert response.status_code == 200
        assert "shelfwatch_requests_total" in response.text


class TestPredictEndpoint:
    def test_successful_prediction(self, client, mock_model_manager):
        image_data = _make_test_image()
        response = client.post(
            "/predict",
            files={"image": ("test.jpg", image_data, "image/jpeg")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["detections"][0]["class"] == "objects"
        assert "inference_ms" in data
        assert "runtime" in data

    def test_rejects_unsupported_format(self, client):
        response = client.post(
            "/predict",
            files={"image": ("test.gif", b"fake", "image/gif")},
        )
        assert response.status_code == 400

    def test_rejects_oversized_image(self, client):
        # 11MB of zeros exceeds the 10MB limit
        huge_data = b"\xff\xd8\xff\xe0" + b"\x00" * (11 * 1024 * 1024)
        response = client.post(
            "/predict",
            files={"image": ("huge.jpg", huge_data, "image/jpeg")},
        )
        assert response.status_code == 400

    def test_custom_confidence(self, client, mock_model_manager):
        image_data = _make_test_image()
        response = client.post(
            "/predict?confidence=0.5",
            files={"image": ("test.jpg", image_data, "image/jpeg")},
        )
        assert response.status_code == 200
        # Verify predict was called with custom confidence
        call_kwargs = mock_model_manager.predict.call_args
        assert call_kwargs.kwargs.get("conf") == 0.5 or call_kwargs[1].get("conf") == 0.5
