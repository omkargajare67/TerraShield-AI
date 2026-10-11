"""Unit tests for the demonstration analysis service."""

import pytest
from backend.app.core.analysis_service import (
    calculate_leverage_score,
    evaluate_parcel_eligibility,
    run_demonstration_analysis,
)
from backend.app.schemas.analysis import AnalysisRequest


class TestLeverageScoreCalculation:
    """Test suite for the deterministic leverage formula L = ΔR / N."""

    def test_standard_calculation(self):
        # 0.35 risk reduction / 500 trees = 0.0007
        score = calculate_leverage_score(0.35, 500)
        assert score == 0.0007

    def test_high_leverage_calculation(self):
        # 0.28 risk reduction / 350 trees = 0.0008
        score = calculate_leverage_score(0.28, 350)
        assert score == 0.0008

    def test_zero_tree_count_returns_none(self):
        # Division by zero must be gracefully handled without exception
        score = calculate_leverage_score(0.20, 0)
        assert score is None

    def test_negative_tree_count_returns_none(self):
        score = calculate_leverage_score(0.20, -100)
        assert score is None

    def test_negative_risk_reduction_returns_none(self):
        score = calculate_leverage_score(-0.15, 500)
        assert score is None

    def test_none_inputs_return_none(self):
        assert calculate_leverage_score(None, 500) is None
        assert calculate_leverage_score(0.35, None) is None
        assert calculate_leverage_score(None, None) is None

    def test_invalid_type_inputs_return_none(self):
        assert calculate_leverage_score("not_a_number", 500) is None  # type: ignore
        assert calculate_leverage_score(0.35, "invalid") is None  # type: ignore


class TestParcelEligibility:
    """Test suite for parcel exclusion handling."""

    def test_eligible_parcel(self):
        props = {
            "is_excluded": False,
            "demo_tree_count": 400,
            "demo_baseline_risk": 0.70,
        }
        is_eligible, reason = evaluate_parcel_eligibility(props, min_risk_threshold=0.0)
        assert is_eligible is True
        assert reason is None

    def test_pre_excluded_reserve_parcel(self):
        props = {
            "is_excluded": True,
            "exclusion_reason": "Statutory Wilderness Reserve",
            "demo_tree_count": 800,
            "demo_baseline_risk": 0.85,
        }
        is_eligible, reason = evaluate_parcel_eligibility(props, min_risk_threshold=0.0)
        assert is_eligible is False
        assert "Wilderness Reserve" in (reason or "")

    def test_zero_tree_capacity_exclusion(self):
        props = {
            "is_excluded": False,
            "demo_tree_count": 0,
            "demo_baseline_risk": 0.60,
        }
        is_eligible, reason = evaluate_parcel_eligibility(props, min_risk_threshold=0.0)
        assert is_eligible is False
        assert "Non-positive" in (reason or "")

    def test_baseline_risk_below_threshold(self):
        props = {
            "is_excluded": False,
            "demo_tree_count": 300,
            "demo_baseline_risk": 0.40,
        }
        is_eligible, reason = evaluate_parcel_eligibility(props, min_risk_threshold=0.50)
        assert is_eligible is False
        assert "below specified threshold" in (reason or "")


class TestRunDemonstrationAnalysis:
    """Test suite for full demonstration analysis execution."""

    def test_analysis_execution_success(self):
        request = AnalysisRequest(scenario="landslide_mitigation", min_risk_threshold=0.0)
        response = run_demonstration_analysis(request)

        assert response.status == "completed"
        assert response.app_mode == "demo"
        assert response.scenario == "landslide_mitigation"
        assert response.total_candidate_parcels == 5
        assert response.eligible_parcels_count == 3
        assert response.excluded_parcels_count == 2
        assert response.highest_leverage_score is not None
        assert response.highest_leverage_parcel_id == "PARCEL-004"
        assert response.highest_leverage_score == 0.0008

        # Verify ranking
        eligible_parcels = [p for p in response.parcels if not p.is_excluded]
        assert len(eligible_parcels) == 3
        # Rank 1 should be PARCEL-004 (score 0.0008)
        assert eligible_parcels[0].parcel_id == "PARCEL-004"
        assert eligible_parcels[0].rank == 1
        # Rank 2 should be PARCEL-001 (score 0.0007)
        assert eligible_parcels[1].parcel_id == "PARCEL-001"
        assert eligible_parcels[1].rank == 2

        # Verify excluded parcels are retained with explanation
        excluded_parcels = [p for p in response.parcels if p.is_excluded]
        assert len(excluded_parcels) == 2
        for exc in excluded_parcels:
            assert exc.exclusion_reason is not None
            assert exc.demo_leverage_score is None

        # Verify provenance and warnings
        assert "Phase 1 demonstration" in response.warning
        assert "Synthetic sample dataset" in response.provenance
        assert response.study_area.is_synthetic is True

    def test_unsupported_scenario_raises_value_error(self):
        request = AnalysisRequest(scenario="unsupported_quantum_scenario")
        with pytest.raises(ValueError) as excinfo:
            run_demonstration_analysis(request)
        assert "Unsupported scenario" in str(excinfo.value)

    def test_threshold_filtering(self):
        # Filtering with high threshold should exclude lower baseline risk parcels
        request = AnalysisRequest(scenario="landslide_mitigation", min_risk_threshold=0.80)
        response = run_demonstration_analysis(request)

        # Baseline risks: PARCEL-001: 0.82 (eligible), PARCEL-002: 0.65 (<0.80),
        # PARCEL-003: 0.90 (pre-excluded), PARCEL-004: 0.74 (<0.80), PARCEL-005: 0.45 (pre-excluded)
        assert response.eligible_parcels_count == 1
        eligible = [p for p in response.parcels if not p.is_excluded]
        assert len(eligible) == 1
        assert eligible[0].parcel_id == "PARCEL-001"
