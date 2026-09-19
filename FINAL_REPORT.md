# ClinSynth Workflow Final Verification Report

| Page / Stage | Action Evaluated | Navigation Persistence | Refresh (F5) Persistence | Expected Result | Pass/Fail |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Data** | Load Demo Dataset | N/A | YES | Dataset loads successfully | PASS |
| **Train Model** | Train Gaussian Copula | YES | YES | Status changes from *Not trained* to *Trained* | PASS |
| **Cohort Builder** | View status | YES | YES | Status displays *Model: Trained* | PASS |
| **Cohort Builder** | Generate Cohort | YES | YES | Status changes to *Cohort: Generated* | PASS |
| **Validation** | View Report | YES | YES | Displays fidelity metrics for generated cohort | PASS |
| **Privacy** | View Privacy Checks | YES | YES | Displays privacy checks for generated cohort | PASS |
| **Research Readiness** | View Status | YES | YES | Displays evaluated readiness for cohort | PASS |
| **Data** | Load new dataset | N/A | N/A | New dataset loaded; downstream state wiped | PASS |
| **Train Model** | View status after reload | YES | YES | Resets to *Not trained* | PASS |
| **Cohort Builder** | View status after reload | YES | YES | Resets to *not_generated* | PASS |

---

## Technical Findings

1. **Backend State Consistency**: The reported issue (`/api/train/status` yielding `trained = true` while `/api/overview` reported `model_trained = false`) was caused by inconsistent Python module initialization paths. The backend loaded distinct `AppState` singletons depending on whether it was accessed as `backend.app.services.state` or `app.services.state`.
   - *Fix applied*: Replaced the basic instantiation with a strictly bounded `sys.modules` singleton to ensure only a single instance exists per process.
2. **Frontend Validation Block**: The React frontend checked for an outdated `status === "completed"` string on the train status response, which no longer existed (`{ trained: boolean }`).
   - *Fix applied*: Updated the frontend TypeScript interface and condition check to correctly use `!trainStatus.trained`.
3. **Downstream State Clearing**: The `/api/data/upload` endpoint failed to clear synthetic cohorts and models from memory when new datasets were uploaded.
   - *Fix applied*: Forced state resets (`state.synthesizer = None`, `state.clear_cohort_results()`, etc.) within `upload_csv`.
4. **Infrastructure Limitations**: The application relies on in-memory state. While the fixes resolve single-session state consistency and page refresh issues, restarting the backend service (e.g., Render restart) will wipe the memory. If true distributed robustness is required, moving `AppState` to Redis or an SQL database is highly recommended.
