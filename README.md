# ClinSynth

**Privacy-Preserving Synthetic Patient Data Platform**

*Realistic Data. Zero Patient Exposure.*

---

## Overview

ClinSynth is an advanced privacy-aware clinical cohort simulation and validation platform that generates realistic synthetic patient cohorts for healthcare research and digital-health testing without exposing real patient records. Built for the **SH-405 — Synthetic Patient Data Generation for Clinical Research** problem statement.

A researcher can:
1. Load or upload a patient dataset
2. Inspect data quality and distributions
3. Train a synthetic data generator (CTGAN or Gaussian Copula)
4. Compare synthesizer models in the Model Comparison Lab
5. Define a custom cohort with demographic and conditional constraints
6. Apply research scenario presets (7 built-in clinical scenarios)
7. Generate synthetic patient profiles with trajectory archetypes
8. Explore individual patient journeys with cohort comparison
9. Validate fidelity per-column, per-subgroup, and overall
10. Run privacy screening with real-to-real baseline context
11. Explore the privacy-vs-fidelity tradeoff across privacy modes
12. Save and compare experiments with full reproducibility
13. Export comprehensive ZIP bundles with quality reports

## Architecture

```
Dataset
  -> Data Ingestion + Schema Mapping
  -> Data Quality Validation + Guardrails
  -> Preprocessing
  -> Profile Dataset + Longitudinal Dataset
  -> CTGAN / Gaussian Copula Synthesizer (via SDV)
  -> Model Comparison Lab (optional)
  -> Synthetic Patient Profiles
  -> Cohort Builder (nested/conditional constraints)
  -> Privacy Mode Filtering (low/balanced/high)
  -> Plausibility Guardrails
  -> Temporal Patient Journey Generator (trajectory archetypes)
  -> Longitudinal Guardrails
  -> Statistical Validation Engine (per-column, subgroup, pairwise)
  -> Privacy Evaluation (real-to-real baseline, synth-to-synth)
  -> Experiment History (JSON-based)
  -> Next.js Frontend (12 pages) / FastAPI Backend
  -> CSV / JSON / ZIP Export with Quality Report
```

### Module Structure

```
src/                  # Core ML/data modules (shared by all frontends)
  data/               # Dataset loading, demo generation, schema mapping
  preprocessing/      # Data quality validation, type detection, bounds enforcement
    guardrails.py     # Clinical plausibility checks and repairs
  synthesis/          # SDV synthesizer training, saving, loading, sampling
    comparison.py     # Model comparison lab
  cohort/             # Cohort conditioning with nested/conditional constraints
  temporal/           # Longitudinal journey generation with trajectory archetypes
  validation/         # Statistical comparison (KS, Wasserstein, TVD, correlation,
                      #   per-column quality cards, subgroup fidelity)
  privacy/            # Duplicate detection, NN analysis, real-to-real baseline,
                      #   synth-to-synth distances, privacy mode filtering
  visualization/      # Plotly charts (legacy Streamlit)
  utils/              # Configuration, export, experiment history
backend/              # FastAPI REST API
  app/
    api/routes.py     # All API endpoints
    schemas/models.py # Pydantic request/response models
    services/state.py # In-memory application state
frontend/             # Next.js 16 + TypeScript + Tailwind CSS + Recharts
  app/                # App Router pages (12 routes)
  lib/api.ts          # API client with full TypeScript interfaces
  components/         # Shared UI components (sidebar nav)
tests/                # pytest test suite (57 core + 27 API tests)
app.py                # Legacy Streamlit UI (optional)
artifacts/            # Model artifacts and reports (gitignored)
```

## Features

### Core Synthesis
- **Dual Synthesizers**: CTGAN and Gaussian Copula (via SDV library)
- **Model Comparison Lab**: Side-by-side comparison of synthesizer models with measured metrics
- **Automatic Fallback**: CTGAN failure falls back to Gaussian Copula

### Cohort Building
- **Nested Constraints**: HTN-among-diabetic, diabetes-among-elderly conditional targeting
- **Research Presets**: 7 built-in scenarios (general population, older adult, older diabetic, hypertension-heavy, low adherence, high-pain-low-activity, recovery monitoring)
- **Constraint Satisfaction Reporting**: Requested vs actual percentages with error tracking

### Temporal Generation
- **Trajectory Archetypes**: Stable, Improving, Worsening, Fluctuating patterns
- **Configurable Distribution**: Control the mix of trajectory types per cohort
- **Clinical Plausibility**: Systolic > diastolic BP invariant enforced

### Privacy
- **Three Privacy Modes**: Low (no filtering), Balanced (moderate rejection), High (strict rejection + noise)
- **Real-to-Real Baseline**: Contextualizes synthetic distances against real-record separation
- **Synth-to-Synth Distances**: Diversity check within synthetic data
- **Privacy vs Fidelity Explorer**: Compare tradeoffs across all three modes

### Validation
- **Per-Column Quality Cards**: Individual column quality grades (Excellent/Good/Fair/Poor)
- **Subgroup Fidelity**: Fidelity analysis across demographic splits (diabetic, hypertensive, elderly)
- **Pairwise Relationship Preservation**: Correlation matrix comparison

### Experiment Management
- **Experiment History**: JSON-based experiment saving and comparison
- **Full Reproducibility**: Seeded random state across all pipeline stages

### Export
- **Comprehensive ZIP**: Profiles, longitudinal, combined, validation report, privacy report, cohort config, experiment metadata, quality report, README
- **Quality Report**: JSON report with generation metadata, constraints, fidelity, privacy, limitations

## Dashboard Pages

1. **Overview** — Pipeline visualization, executive metrics, current experiment summary
2. **Data** — Load demo dataset or upload CSV, data quality summary
3. **Train** — Train CTGAN or Gaussian Copula with configurable epochs
4. **Cohort Builder** — Research presets, demographic constraints, conditional constraints, trajectory distribution, privacy mode, seed
5. **Synthetic Cohort** — Constraint satisfaction gauges, trajectory distribution, plausibility checks
6. **Patient Journeys** — Individual patient timeline explorer with cohort average overlay
7. **Validation** — Fidelity summary, per-column quality cards, distribution comparisons, correlations, longitudinal trends, subgroup fidelity
8. **Privacy** — Exact duplicates, nearest-neighbor analysis, real-to-real baseline, synth-to-synth distances
9. **Privacy vs Fidelity** — Compare low/balanced/high privacy modes on fidelity and distance metrics
10. **Model Comparison** — Train and compare multiple synthesizers on fidelity, privacy, speed, size
11. **Experiments** — Save, list, and inspect past experiments
12. **Export** — Individual CSV/JSON downloads, quality report, comprehensive ZIP

## Tech Stack

### Backend
- Python 3.11+
- FastAPI + Uvicorn (REST API)
- Pandas, NumPy (data processing)
- SDV / CTGAN (synthetic data generation)
- scikit-learn (privacy analysis)
- SciPy (statistical tests)
- pytest (testing)

### Frontend
- Next.js 16 (App Router)
- TypeScript
- Tailwind CSS 4
- Recharts 3 (charts and visualizations)

### Legacy
- Streamlit (optional, `app.py`)
- Plotly (Streamlit visualization)

## Installation

```bash
# Backend dependencies
pip install -r backend/requirements.txt

# Frontend dependencies
cd frontend && npm install
```

## Run

### Production-style (FastAPI + Next.js)

```bash
# Terminal 1: Start backend
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2: Start frontend
cd frontend && npm run dev
```

Frontend: `http://localhost:3000` | Backend API: `http://localhost:8000/api`

### Legacy Streamlit

```bash
pip install -r requirements.txt
streamlit run app.py
```

Legacy Streamlit app: `http://localhost:8501`

## Demo Walkthrough

1. **Launch**: Start both backend and frontend (see Run section above)
2. **Data page**: Click "Load Demo Dataset" (500 sample patients, 30-day longitudinal)
3. **Train page**: Select "GaussianCopulaSynthesizer" + "Demo (fast)" mode, click "Train Model"
4. **Cohort Builder**: Select "Older Diabetic Cohort" preset (or customize), set 5000 patients
5. **Configure**: Adjust conditional constraints (HTN among diabetic, DM among elderly)
6. **Set trajectory**: E.g., 40% Stable, 25% Improving, 20% Worsening, 15% Fluctuating
7. **Privacy mode**: Select "Balanced"
8. **Generate**: Click "Generate Synthetic Cohort"
9. **Synthetic Cohort**: Verify constraint satisfaction gauges and trajectory distribution
10. **Patient Journeys**: Select a patient, compare with cohort average
11. **Validation**: Check fidelity score, per-column quality, subgroup fidelity
12. **Privacy**: Review nearest-neighbor distances with real-to-real baseline context
13. **Model Comparison**: (Optional) Compare CTGAN vs Gaussian Copula
14. **Experiments**: Save experiment for future comparison
15. **Export**: Download complete ZIP with quality report

## Dataset

The bundled demo dataset contains **500 deterministically generated sample patients** with 30-day longitudinal health records. This data is purely synthetic and does not represent real patients.

The demo generator creates realistic clinical relationships:
- Older patients tend to have higher blood pressure and BMI
- Diabetic and hypertensive subgroups show distinct vital-sign distributions
- Activity (steps) decreases with age and comorbidities
- Medication adherence varies across the cohort

Users can also upload their own CSV datasets; the system will attempt schema detection and mapping.

## Model

**CTGAN is not a pretrained healthcare model.** It is fitted on the selected source dataset and learns statistical relationships from that data. The Gaussian Copula synthesizer provides a faster, more stable alternative for small datasets.

Generated records are synthetic approximations of the source data's statistical properties.

## Temporal Generation

The temporal engine generates daily health measurements for each synthetic patient:
- Baseline vitals are influenced by age, BMI, diabetes, and hypertension status
- Day-to-day variation follows distributions learned from source longitudinal data
- **Trajectory archetypes** shape trends: Stable (flat), Improving (downward BP/pain, upward steps), Worsening (opposite), Fluctuating (sinusoidal oscillation)
- Systolic > diastolic BP invariant is enforced during and after generation

These are **simulation assumptions** for demonstration purposes, not validated clinical models.

## Validation Metrics

| Metric | Type | Description |
|--------|------|-------------|
| KS Statistic | Numerical | Kolmogorov-Smirnov two-sample test |
| Wasserstein Distance | Numerical | Earth mover's distance between distributions |
| Total Variation Distance | Categorical | Half the L1 distance between category proportions |
| Correlation Difference | Relationship | Mean absolute difference between correlation matrices |
| Trend Correlation | Longitudinal | Pearson correlation between daily mean trends |
| Fidelity Score | Overall | mean(1 - KS for numerical, 1 - TVD for categorical, 1 - corr_diff) |
| Per-Column Quality | Per-column | Grade (Excellent/Good/Fair/Poor) based on KS or TVD thresholds |
| Subgroup Fidelity | Per-subgroup | Fidelity within demographic subgroups |

## Privacy Metrics

| Check | Description |
|-------|-------------|
| Exact Duplicate Detection | Counts synthetic rows matching real rows after normalization |
| Nearest-Neighbor Distance | Euclidean distance to closest real record (standardized) |
| Near-Copy Flagging | Records below configurable distance threshold |
| Real-to-Real Baseline | 2nd-nearest-neighbor distances among real records (context) |
| Synth-to-Synth Distances | NN distances within synthetic data (diversity check) |
| Privacy Mode Filtering | Near-copy rejection + noise injection (low/balanced/high) |

**These are screening metrics, not formal privacy guarantees.** Synthetic data can reduce exposure of original records but is not automatically equivalent to formal differential privacy.

## Limitations

- This is a research/demo platform, not a clinically validated tool
- No HIPAA or GDPR compliance evaluation has been performed
- No formal differential privacy guarantees are provided
- Medical relationships in demo data are simulation assumptions, not evidence-based clinical models
- Trajectory archetypes are simulation patterns, not clinically validated disease progression
- Performance may degrade with very large datasets (>50K patients) on standard hardware
- CTGAN quality depends heavily on the size and diversity of training data
- Privacy modes provide screening-level protection, not certified anonymization

## Testing

```bash
pytest tests/ -v
```

```bash
# Core tests (57 tests)
pytest tests/ -v

# API tests (27 tests)
pytest backend/tests/ -v

# All tests
pytest tests/ backend/tests/ -v
```

84 tests total covering: data generation, preprocessing, cohort building (including nested constraints), trajectory types, temporal generation, validation (including per-column quality and subgroup fidelity), privacy (including modes, real-to-real baseline, synth-to-synth), guardrails, experiment history, research presets, reproducibility, quality reports, export, and all FastAPI endpoints.
