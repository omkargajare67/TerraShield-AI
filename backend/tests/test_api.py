"""Integration tests for FastAPI endpoints."""

from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


class TestHealthEndpoint:
    """Test suite for GET /health."""

    def test_health_check_returns_200_and_expected_fields(self):
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert data["app_name"] == "TerraShield AI"
        assert data["version"] == "0.1.0"
        assert data["mode"] == "demo"
        assert "timestamp" in data
        assert "message" in data


class TestParcelsEndpoint:
    """Test suite for GET /api/v1/parcels."""

    def test_get_parcels_returns_geojson_feature_collection(self):
        response = client.get("/api/v1/parcels")
        assert response.status_code == 200

        data = response.json()
        assert data["type"] == "FeatureCollection"
        assert "metadata" in data
        assert data["metadata"]["is_synthetic"] is True
        assert "features" in data
        assert len(data["features"]) >= 3

        # Check first feature properties
        feature = data["features"][0]
        assert feature["type"] == "Feature"
        props = feature["properties"]
        assert "parcel_id" in props
        assert "demo_baseline_risk" in props
        assert "demo_delta_risk" in props
        assert "demo_tree_count" in props
        assert "is_excluded" in props
        assert props["is_synthetic"] is True


class TestAnalysisEndpoint:
    """Test suite for POST /api/v1/analysis."""

    def test_valid_analysis_request(self):
        payload = {"scenario": "landslide_mitigation", "min_risk_threshold": 0.0}
        response = client.post("/api/v1/analysis", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["app_mode"] == "demo"
        assert data["scenario"] == "landslide_mitigation"
        assert data["status"] == "completed"
        assert data["total_candidate_parcels"] == 5
        assert data["eligible_parcels_count"] == 3
        assert data["excluded_parcels_count"] == 2
        assert data["highest_leverage_score"] == 0.0008
        assert data["highest_leverage_parcel_id"] == "PARCEL-004"
        assert "provenance" in data
        assert "warning" in data
        assert len(data["parcels"]) == 5

    def test_unsupported_scenario_returns_400(self):
        payload = {"scenario": "unsupported_coastal_buffer"}
        response = client.post("/api/v1/analysis", json=payload)
        assert response.status_code == 400

        data = response.json()
        assert "Unsupported scenario" in data["detail"]

    def test_invalid_threshold_returns_422(self):
        # min_risk_threshold must be between 0.0 and 1.0
        payload = {"scenario": "landslide_mitigation", "min_risk_threshold": 2.5}
        response = client.post("/api/v1/analysis", json=payload)
        assert response.status_code == 422
