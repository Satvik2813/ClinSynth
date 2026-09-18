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
