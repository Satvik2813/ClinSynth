"""FastAPI backend tests using TestClient."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.state import state, AppState


@pytest.fixture(autouse=True)
def reset_state():
    """Reset application state before each test."""
    import backend.app.services.state as state_mod
    state_mod.state = AppState()
    import backend.app.api.routes as routes_mod
    routes_mod.state = state_mod.state
    yield


client = TestClient(app)


class TestHealth:
    def test_health(self):
        r = client.get("/api/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert data["project"] == "ClinSynth"


class TestData:
    def test_load_demo(self):
        r = client.post("/api/data/demo")
        assert r.status_code == 200
        data = r.json()
        assert data["n_patients"] > 0
        assert data["n_longitudinal_records"] > 0
        assert "profile_columns" in data

    def test_summary_before_load(self):
        r = client.get("/api/data/summary")
        assert r.status_code == 404

    def test_summary_after_load(self):
        client.post("/api/data/demo")
        r = client.get("/api/data/summary")
        assert r.status_code == 200

    def test_upload_invalid(self):
        r = client.post(
            "/api/data/upload",
            files={"file": ("test.txt", b"not csv", "text/plain")},
        )
        assert r.status_code == 400


class TestTrain:
    def test_train_without_data(self):
        r = client.post("/api/train", json={"synth_type": "GaussianCopulaSynthesizer"})
        assert r.status_code == 400

    def test_train_gaussian_copula(self):
        client.post("/api/data/demo")
        r = client.post("/api/train", json={
            "synth_type": "GaussianCopulaSynthesizer",
            "mode": "Demo (fast)",
        })
        assert r.status_code == 200
        data = r.json()
        assert data["synth_type"] == "GaussianCopulaSynthesizer"
        assert data["duration_seconds"] > 0

    def test_train_status(self):
        r = client.get("/api/train/status")
        assert r.status_code == 200
        assert r.json()["trained"] is False


class TestCohort:
    def _setup_trained(self):
        client.post("/api/data/demo")
        client.post("/api/train", json={"synth_type": "GaussianCopulaSynthesizer"})

    def test_generate_without_model(self):
        r = client.post("/api/cohort/generate", json={"num_patients": 100})
        assert r.status_code == 400

    def test_generate_cohort(self):
        self._setup_trained()
        r = client.post("/api/cohort/generate", json={
            "num_patients": 100,
            "timeline_days": 10,
            "seed": 42,
            "privacy_mode": "low",
        })
        assert r.status_code == 200
        data = r.json()
        assert data["total_patients"] == 100
        assert data["longitudinal_records"] == 1000
        assert len(data["constraints"]) >= 3

    def test_nested_constraints(self):
        self._setup_trained()
        r = client.post("/api/cohort/generate", json={
            "num_patients": 200,
            "timeline_days": 10,
            "elderly_pct": 0.40,
            "diabetes_pct": 0.30,
            "hypertension_pct": 0.25,
            "htn_among_diabetic_pct": 0.60,
            "diabetes_among_elderly_pct": 0.40,
            "seed": 42,
            "privacy_mode": "low",
        })
        assert r.status_code == 200
        data = r.json()
        for c in data["constraints"]:
            if c["error"] is not None:
                assert c["error"] < 0.15

    def test_current_cohort(self):
        self._setup_trained()
        client.post("/api/cohort/generate", json={
            "num_patients": 50, "timeline_days": 5, "privacy_mode": "low",
        })
        r = client.get("/api/cohort/current")
        assert r.status_code == 200


class TestJourneys:
    def test_journey_not_found(self):
        r = client.get("/api/journeys/SYN-999999")
        assert r.status_code == 404

    def test_journey_after_generation(self):
        client.post("/api/data/demo")
        client.post("/api/train", json={"synth_type": "GaussianCopulaSynthesizer"})
        client.post("/api/cohort/generate", json={
            "num_patients": 50, "timeline_days": 5, "privacy_mode": "low",
        })
        r = client.get("/api/journeys/SYN-000001")
        assert r.status_code == 200
        data = r.json()
        assert data["demographics"]["patient_id"] == "SYN-000001"
        assert len(data["journey"]) == 5
        assert len(data["stats"]) > 0

    def test_list_patients(self):
        client.post("/api/data/demo")
        client.post("/api/train", json={"synth_type": "GaussianCopulaSynthesizer"})
        client.post("/api/cohort/generate", json={
            "num_patients": 50, "timeline_days": 5, "privacy_mode": "low",
        })
        r = client.get("/api/journeys")
        assert r.status_code == 200
        assert len(r.json()["patient_ids"]) == 50


class TestValidation:
    def test_validation(self):
        client.post("/api/data/demo")
        client.post("/api/train", json={"synth_type": "GaussianCopulaSynthesizer"})
        client.post("/api/cohort/generate", json={
            "num_patients": 100, "timeline_days": 10, "privacy_mode": "low",
        })
        r = client.get("/api/validation")
        assert r.status_code == 200
        data = r.json()
        assert "fidelity_summary" in data
        assert 0 <= data["fidelity_summary"]["overall_fidelity"] <= 1


class TestPrivacy:
    def test_privacy(self):
        client.post("/api/data/demo")
        client.post("/api/train", json={"synth_type": "GaussianCopulaSynthesizer"})
        client.post("/api/cohort/generate", json={
            "num_patients": 100, "timeline_days": 10, "privacy_mode": "low",
        })
        r = client.get("/api/privacy")
        assert r.status_code == 200
        data = r.json()
        assert "overall_status" in data
        assert "checks" in data

    def test_privacy_compare(self):
        client.post("/api/data/demo")
        client.post("/api/train", json={"synth_type": "GaussianCopulaSynthesizer"})
        client.post("/api/cohort/generate", json={
            "num_patients": 100, "timeline_days": 10, "privacy_mode": "low",
        })
        r = client.post("/api/privacy/compare")
        assert r.status_code == 200
        data = r.json()
        assert len(data["results"]) == 3


class TestExperiments:
    def test_list_empty(self):
        r = client.get("/api/experiments")
        assert r.status_code == 200

    def test_save_experiment(self):
        client.post("/api/data/demo")
        client.post("/api/train", json={"synth_type": "GaussianCopulaSynthesizer"})
        client.post("/api/cohort/generate", json={
            "num_patients": 50, "timeline_days": 5, "privacy_mode": "low",
        })
        client.get("/api/validation")
        r = client.post("/api/experiments/save")
        assert r.status_code == 200
        assert "experiment_id" in r.json()


class TestExport:
    def _setup(self):
        client.post("/api/data/demo")
        client.post("/api/train", json={"synth_type": "GaussianCopulaSynthesizer"})
        client.post("/api/cohort/generate", json={
            "num_patients": 50, "timeline_days": 5, "privacy_mode": "low",
        })

    def test_export_profiles_csv(self):
        self._setup()
        r = client.get("/api/export/profiles_csv")
        assert r.status_code == 200
        assert "text/csv" in r.headers["content-type"]

    def test_export_zip(self):
        self._setup()
        r = client.get("/api/export/zip")
        assert r.status_code == 200
        assert "application/zip" in r.headers["content-type"]

    def test_export_unknown(self):
        self._setup()
        r = client.get("/api/export/unknown")
        assert r.status_code == 400


class TestOverview:
    def test_overview_empty(self):
        r = client.get("/api/overview")
        assert r.status_code == 200
        data = r.json()
        assert data["data_loaded"] is False

    def test_overview_after_data(self):
        client.post("/api/data/demo")
        r = client.get("/api/overview")
        assert r.status_code == 200
        data = r.json()
        assert data["data_loaded"] is True
        assert data["source_patients"] > 0

    def test_pipeline_state_consistency(self):
        # 1. Load data
        client.post("/api/data/demo")
        r = client.get("/api/overview")
        assert r.json()["data_loaded"] is True
        assert r.json()["model_trained"] is False
        assert r.json()["cohort_generated"] is False

        # 2. Train model
        r = client.post("/api/train", json={"synth_type": "GaussianCopulaSynthesizer", "mode": "Demo (fast)"})
        assert r.status_code == 200
        r_train_status = client.get("/api/train/status")
        assert r_train_status.json()["trained"] is True
        
        r_overview = client.get("/api/overview")
        assert r_overview.json()["model_trained"] is True
        assert r_overview.json()["data_loaded"] is True

        # 3. Generate cohort
        r = client.post("/api/cohort/generate", json={"num_patients": 100, "timeline_days": 10})
        assert r.status_code == 200
        
        r_overview = client.get("/api/overview")
        assert r_overview.json()["cohort_generated"] is True

        # 4. Load new dataset (should reset downstream state)
        client.post("/api/data/demo")
        r_overview = client.get("/api/overview")
        assert r_overview.json()["data_loaded"] is True
        assert r_overview.json()["model_trained"] is False
        assert r_overview.json()["cohort_generated"] is False
        
        r_train_status = client.get("/api/train/status")
        assert r_train_status.json()["trained"] is False


class TestCORS:
    def test_preflight_production_origin(self):
        r = client.options(
            "/api/data/summary",
            headers={
                "Origin": "https://clin-synth.vercel.app",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        assert r.status_code == 200
        assert r.headers["access-control-allow-origin"] == "https://clin-synth.vercel.app"

    def test_cors_header_on_get(self):
        r = client.get("/api/health", headers={"Origin": "https://clin-synth.vercel.app"})
        assert r.status_code == 200
        assert r.headers["access-control-allow-origin"] == "https://clin-synth.vercel.app"


class TestConfig:
    def test_presets(self):
        r = client.get("/api/config/presets")
        assert r.status_code == 200
        assert len(r.json()["presets"]) >= 7

    def test_privacy_modes(self):
        r = client.get("/api/config/privacy_modes")
        assert r.status_code == 200
        modes = r.json()["modes"]
        assert "low" in modes
        assert "balanced" in modes
        assert "high" in modes


class TestSourceSubgroups:
    def test_no_data(self):
        r = client.get("/api/cohort/source-subgroups")
        assert r.status_code == 404

    def test_subgroups_after_demo(self):
        client.post("/api/data/demo")
        r = client.get("/api/cohort/source-subgroups")
        assert r.status_code == 200
        data = r.json()
        assert data["total_patients"] > 0
        assert len(data["subgroups"]) == 7
        for sg in data["subgroups"]:
            assert "label" in sg
            assert "count" in sg
            assert "percentage" in sg
            assert sg["count"] >= 0


class TestRareAmplification:
    def _setup_cohort(self):
        client.post("/api/data/demo")
        client.post("/api/train", json={"synth_type": "GaussianCopulaSynthesizer"})
        client.post("/api/cohort/generate", json={
            "num_patients": 50, "timeline_days": 5, "privacy_mode": "low",
        })

    def test_no_data(self):
        r = client.get("/api/cohort/rare-amplification")
        assert r.status_code == 404

    def test_no_cohort(self):
        client.post("/api/data/demo")
        r = client.get("/api/cohort/rare-amplification")
        assert r.status_code == 404

    def test_amplification(self):
        self._setup_cohort()
        r = client.get("/api/cohort/rare-amplification")
        assert r.status_code == 200
        data = r.json()
        assert "amplification" in data
        assert len(data["amplification"]) == 7
        for entry in data["amplification"]:
            assert "subgroup" in entry
            assert "source_count" in entry
            assert "synthetic_count" in entry
            assert "amplification_factor" in entry


class TestResearchUtility:
    def _setup_cohort(self):
        client.post("/api/data/demo")
        client.post("/api/train", json={"synth_type": "GaussianCopulaSynthesizer"})
        client.post("/api/cohort/generate", json={
            "num_patients": 100, "timeline_days": 5, "privacy_mode": "low",
        })

    def test_no_data(self):
        r = client.post("/api/research/utility", json={"target": "hypertension"})
        assert r.status_code == 400

    def test_no_cohort(self):
        client.post("/api/data/demo")
        r = client.post("/api/research/utility", json={"target": "hypertension"})
        assert r.status_code == 400

    def test_utility_default_target(self):
        self._setup_cohort()
        r = client.post("/api/research/utility", json={"target": "hypertension"})
        assert r.status_code == 200
        data = r.json()
        assert "utility_retention" in data
        assert "real_trained_metrics" in data
        assert "synthetic_trained_metrics" in data
        assert data["target"] == "hypertension"
        assert 0 <= data["utility_retention"] <= 2.0

    def test_utility_invalid_target(self):
        self._setup_cohort()
        r = client.post("/api/research/utility", json={"target": "nonexistent_column"})
        assert r.status_code == 400


class TestResearchReadiness:
    def _setup_cohort(self):
        client.post("/api/data/demo")
        client.post("/api/train", json={"synth_type": "GaussianCopulaSynthesizer"})
        client.post("/api/cohort/generate", json={
            "num_patients": 100, "timeline_days": 5, "privacy_mode": "low",
        })

    def test_no_cohort(self):
        r = client.get("/api/research/readiness")
        assert r.status_code == 404

    def test_readiness_after_cohort(self):
        self._setup_cohort()
        r = client.get("/api/research/readiness")
        assert r.status_code == 200
        data = r.json()
        for key in ["statistical_fidelity", "research_utility", "subgroup_preservation",
                     "clinical_validity", "privacy_screening"]:
            assert key in data
            assert "status" in data[key]
        assert "rare_cohort_coverage" in data

    def test_readiness_with_validation(self):
        self._setup_cohort()
        client.get("/api/validation")
        client.get("/api/privacy")
        r = client.get("/api/research/readiness")
        assert r.status_code == 200
        data = r.json()
        assert data["statistical_fidelity"]["status"] == "evaluated"
        assert data["statistical_fidelity"]["value"] is not None
        assert data["privacy_screening"]["status"] == "evaluated"


class TestGuardrails:
    def _setup_cohort(self):
        client.post("/api/data/demo")
        client.post("/api/train", json={"synth_type": "GaussianCopulaSynthesizer"})
        client.post("/api/cohort/generate", json={
            "num_patients": 50, "timeline_days": 5, "privacy_mode": "low",
        })

    def test_no_cohort(self):
        r = client.get("/api/cohort/guardrails")
        assert r.status_code == 404

    def test_guardrails_after_cohort(self):
        self._setup_cohort()
        r = client.get("/api/cohort/guardrails")
        assert r.status_code == 200
        data = r.json()
        assert "total_records_checked" in data
        assert "violations_found" in data
        assert "records_repaired" in data
        assert "all_passed" in data
        assert "accepted_patients" in data
        assert data["accepted_patients"] > 0
