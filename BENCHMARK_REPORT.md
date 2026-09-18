# ClinSynth Benchmark Report

**Project:** ClinSynth — SH-405 Synthetic Patient Data Generation for Clinical Research

This file is intentionally evidence-based. No benchmark value is recorded unless it was produced by an actual benchmark run.

## Target Environment

Required target:

- Windows laptop
- 16 GB RAM
- CPU-only
- Python 3.11+ recommended

## Benchmark Command

From the repository root:

```bash
python scripts/run_benchmarks.py
```

Raw results are written to:

```text
artifacts/reports/benchmark_results.json
```

## Required Measurements

| Benchmark | Wall time | Peak memory | Status |
|---|---:|---:|---|
| Gaussian Copula training | — | — | Not yet executed on target environment |
| Gaussian Copula generation — 1,000 | — | — | Not yet executed on target environment |
| Gaussian Copula generation — 5,000 | — | — | Not yet executed on target environment |
| CTGAN Demo training — 50 epochs | — | — | Not yet executed on target environment |
| CTGAN generation — 1,000 | — | — | Not yet executed on target environment |
| Temporal generation — 1,000 × 30 | — | — | Not yet executed on target environment |
| Temporal generation — 5,000 × 30 | — | — | Not yet executed on target environment |
| Profile validation — 1,000 | — | — | Not yet executed on target environment |
| Profile validation — 5,000 | — | — | Not yet executed on target environment |
| Privacy analysis — 1,000 | — | — | Not yet executed on target environment |
| Privacy analysis — 5,000 | — | — | Not yet executed on target environment |

## Methodology

The benchmark runner uses:

- `time.perf_counter()` for wall-clock timing
- `tracemalloc` for Python peak allocated memory
- deterministic seed 42 where the underlying operation supports deterministic behavior
- the bundled ClinSynth demo dataset
- Gaussian Copula and CTGAN through the existing SDV-based core
- the existing cohort, temporal, validation, and privacy modules rather than benchmark-only substitutes

## Interpretation Notes

- `tracemalloc` tracks Python allocations and may not capture all native-library memory used by NumPy, PyTorch, SDV, or BLAS.
- CTGAN runtime can vary materially by CPU, Python/PyTorch build, and thread settings.
- Privacy analysis samples nearest-neighbor queries rather than constructing a full synthetic-to-real pairwise matrix for all records.
- These are engineering performance measurements, not clinical-quality or privacy guarantees.

## Acceptance Target

The important demo acceptance case is:

```text
5,000 synthetic patients × 30 days = 150,000 longitudinal records
```

It should complete without process failure or impractical memory growth on the target 16 GB CPU-only machine.

## Verification State

As of the latest repository audit, the benchmark harness is present but the measured target-machine values have not yet been executed from this environment. Populate this report only after running the benchmark command above.
