# ClinSynth

**Privacy-Preserving Synthetic Patient Data Platform**

*Realistic Data. Zero Patient Exposure.*

---

## Overview

ClinSynth is a research/demo platform that generates realistic synthetic patient cohorts for healthcare research and digital-health testing without exposing real patient records. Built for the **SH-405 — Synthetic Patient Data Generation for Clinical Research** problem statement.

A researcher can:
1. Load or upload a patient dataset
2. Inspect data quality and distributions
3. Train a synthetic data generator (CTGAN or Gaussian Copula)
4. Define a custom cohort with demographic constraints
5. Generate synthetic patient profiles and longitudinal health journeys
6. Compare synthetic vs original data statistically
7. Run privacy screening checks
8. Export synthetic data as CSV, JSON, or ZIP

## Architecture

```
Dataset
  -> Data Ingestion + Schema Mapping
  -> Data Quality Validation
  -> Preprocessing
  -> Profile Dataset + Longitudinal Dataset
  -> CTGAN / Gaussian Copula Synthesizer (via SDV)
  -> Synthetic Patient Profiles
  -> Cohort Conditioning Engine (stratified resampling)
  -> Temporal Patient Journey Generator
  -> Statistical Validation Engine
  -> Privacy Evaluation
  -> Dashboard (Streamlit)
  -> CSV / JSON / ZIP Export
```

### Module Structure

```
src/
  data/           # Dataset loading, demo generation, schema mapping
  preprocessing/  # Data quality validation, type detection, bounds enforcement
  synthesis/      # SDV synthesizer training, saving, loading, sampling
  cohort/         # Cohort conditioning with demographic constraints
  temporal/       # Longitudinal health journey generation
  validation/     # Statistical comparison (KS, Wasserstein, TVD, correlation)
  privacy/        # Duplicate detection, nearest-neighbor analysis, screening
  visualization/  # Plotly charts for the dashboard
  utils/          # Configuration, export utilities
tests/            # pytest test suite
artifacts/        # Model artifacts and reports (gitignored)
data/             # Demo and uploaded datasets
```

## Features

- **Dual Synthesizers**: CTGAN and Gaussian Copula (via SDV library)
- **Cohort Builder**: Configurable constraints for age, diabetes, hypertension proportions
- **Longitudinal Generation**: Realistic daily health journeys (BP, steps, adherence, pain)
- **Statistical Validation**: KS test, Wasserstein distance, TVD, correlation comparison
- **Privacy Screening**: Exact duplicate detection, nearest-neighbor analysis, near-copy flagging
- **Patient Journey Explorer**: Interactive per-patient health timeline visualization
- **Multiple Export Formats**: CSV, JSON, ZIP bundles with reports
- **Polished Dashboard**: 8-page Streamlit app with clinical/research aesthetic

## Tech Stack

- Python 3.11+
- Streamlit (UI)
- Pandas, NumPy (data processing)
- SDV / CTGAN (synthetic data generation)
- scikit-learn (privacy analysis)
- SciPy (statistical tests)
- Plotly (visualization)
- pytest (testing)

## Installation

```bash
pip install -r requirements.txt
```

## Run

```bash
streamlit run app.py
```

The app will open at `http://localhost:8501`.

## Demo Walkthrough

1. **Launch**: `streamlit run app.py`
2. **Data page**: Click "Load Demo Dataset" (500 sample patients, 30-day longitudinal)
3. **Train page**: Select "GaussianCopulaSynthesizer" + "Demo (fast)" mode, click "Train Model"
4. **Cohort Builder**: Set 5000 patients, 40% elderly, 30% diabetes, 25% hypertension, 30 days
5. **Generate**: Click "Generate Synthetic Cohort"
6. **Synthetic Cohort**: Verify requested vs actual percentages, explore patient journeys
7. **Validation**: Compare distributions, correlations, longitudinal trends
8. **Privacy**: Review duplicate detection, nearest-neighbor distances, screening status
9. **Export**: Download CSV, JSON, or complete ZIP

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
- Medication adherence may trend upward slightly (treatment effect simulation)
- Hypertensive patients may show slight BP downward trends

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

## Privacy Metrics

| Check | Description |
|-------|-------------|
| Exact Duplicate Detection | Counts synthetic rows matching real rows after normalization |
| Nearest-Neighbor Distance | Euclidean distance to closest real record (standardized) |
| Near-Copy Flagging | Records below distance threshold 0.1 |

**These are screening metrics, not formal privacy guarantees.** Synthetic data can reduce exposure of original records but is not automatically equivalent to formal differential privacy.

## Limitations

- This is a research/demo platform, not a clinically validated tool
- No HIPAA or GDPR compliance evaluation has been performed
- No formal differential privacy guarantees are provided
- Medical relationships in demo data are simulation assumptions, not evidence-based clinical models
- Performance may degrade with very large datasets (>50K patients) on standard hardware
- CTGAN quality depends heavily on the size and diversity of training data

## Testing

```bash
pytest tests/ -v
```

31 tests covering data generation, preprocessing, cohort building, temporal generation, validation, privacy, and export.
