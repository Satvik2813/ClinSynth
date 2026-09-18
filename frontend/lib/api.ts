const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...options?.headers },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

export const api = {
  health: () => request<{ status: string; version: string }>("/health"),

  getOverview: () => request<Overview>("/overview"),

  loadDemo: () => request<DataSummary>("/data/demo", { method: "POST" }),
  uploadCsv: async (file: File) => {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${API_BASE}/data/upload`, { method: "POST", body: form });
    if (!res.ok) {
      const body = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(body.detail || "Upload failed");
    }
    return res.json() as Promise<DataSummary>;
  },
  getDataSummary: () => request<DataSummary>("/data/summary"),

  train: (body: TrainRequest) =>
    request<TrainResult>("/train", { method: "POST", body: JSON.stringify(body) }),
  getTrainStatus: () => request<{ trained: boolean; info: TrainInfo | null }>("/train/status"),

  compareModels: (body: CompareRequest) =>
    request<CompareResult>("/models/compare", { method: "POST", body: JSON.stringify(body) }),
  selectModel: (name: string) =>
    request<{ status: string }>(`/models/select/${name}`, { method: "POST" }),

  generateCohort: (body: CohortRequest) =>
    request<CohortResult>("/cohort/generate", { method: "POST", body: JSON.stringify(body) }),
  getCurrentCohort: () => request<CohortResult>("/cohort/current"),

  listPatients: () => request<{ patient_ids: string[] }>("/journeys"),
  getJourney: (id: string) => request<JourneyResult>(`/journeys/${id}`),

  getValidation: () => request<ValidationResult>("/validation"),

  getPrivacy: () => request<PrivacyResult>("/privacy"),
  comparePrivacy: () =>
    request<{ results: PrivacyFidelityEntry[] }>("/privacy/compare", { method: "POST" }),

  getExperiments: () => request<{ experiments: Experiment[] }>("/experiments"),
  getExperiment: (id: string) => request<Experiment>(`/experiments/${id}`),
  saveExperiment: () => request<Experiment>("/experiments/save", { method: "POST" }),

  getExportUrl: (fmt: string) => `${API_BASE}/export/${fmt}`,

  getPresets: () => request<{ presets: Record<string, Preset> }>("/config/presets"),
  getPrivacyModes: () => request<{ modes: Record<string, PrivacyMode> }>("/config/privacy_modes"),
};

// Types
export interface Overview {
  data_loaded: boolean;
  model_trained: boolean;
  cohort_generated: boolean;
  source_patients: number;
  source_records: number;
  active_model: string | null;
  generated_patients: number;
  generated_records: number;
  fidelity_score: number | null;
  privacy_status: string | null;
  seed: number;
  constraints: Constraint[];
}

export interface DataSummary {
  n_patients: number;
  n_longitudinal_records: number;
  profile_columns: string[];
  longitudinal_columns: string[];
  profile_missing: Record<string, number>;
  longitudinal_missing: Record<string, number>;
  profile_dtypes: Record<string, string>;
  longitudinal_dtypes: Record<string, string>;
  column_types?: Record<string, string>;
  profile_stats?: Record<string, Record<string, number>>;
  profile_preview?: Record<string, unknown>[];
  longitudinal_preview?: Record<string, unknown>[];
  warning?: string;
}

export interface TrainRequest {
  synth_type: string;
  mode: string;
  epochs?: number;
  batch_size?: number;
}

export interface TrainResult {
  status: string;
  synth_type: string;
  training_rows: number;
  epochs: number | null;
  duration_seconds: number;
  message?: string;
}

export interface TrainInfo {
  synth_type: string;
  training_rows: number;
  epochs: number | null;
  duration_seconds: number;
}

export interface CompareRequest {
  epochs: number;
  n_eval_samples: number;
}

export interface CompareResult {
  comparison: Record<string, ModelEntry>;
  table: Record<string, unknown>[];
}

export interface ModelEntry {
  synth_type: string;
  training_success: boolean;
  train_time_seconds?: number;
  generation_time_seconds?: number;
  model_size_kb?: number;
  fidelity_score?: number;
  correlation_preservation?: number;
  ks_similarity?: number;
  exact_duplicates?: number;
  near_copy_count?: number;
  median_nn_distance?: number;
  error?: string;
}

export interface CohortRequest {
  num_patients: number;
  timeline_days: number;
  elderly_pct: number;
  diabetes_pct: number;
  hypertension_pct: number;
  htn_among_diabetic_pct: number | null;
  diabetes_among_elderly_pct: number | null;
  privacy_mode: string;
  seed: number;
  trajectory_dist: Record<string, number>;
  preset?: string | null;
}

export interface Constraint {
  constraint: string;
  requested: number | null;
  actual: number | null;
  error: number | null;
}

export interface CohortResult {
  total_patients: number;
  timeline_days: number;
  longitudinal_records: number;
  constraints: Constraint[];
  trajectory_distribution: Record<string, number>;
  plausibility_stats: Record<string, unknown>;
  cohort_config: Record<string, unknown>;
  profile_preview: Record<string, unknown>[];
}

export interface JourneyResult {
  demographics: {
    patient_id: string;
    age: number;
    gender: string;
    bmi: number;
    diabetes: boolean;
    hypertension: boolean;
    trajectory_type: string | null;
  };
  journey: Record<string, unknown>[];
  stats: JourneyStat[];
  cohort_average: Record<string, unknown>[];
}

export interface JourneyStat {
  metric: string;
  baseline: number | null;
  final: number | null;
  change: number | null;
  mean: number;
  min: number;
  max: number;
}

export interface ValidationResult {
  fidelity_summary: {
    overall_fidelity: number;
    component_count: number;
    formula: string;
    interpretation: string;
  };
  profile_results: Record<string, unknown>;
  longitudinal_results: Record<string, unknown>;
  per_column_quality: ColumnQuality[];
  subgroup_fidelity: SubgroupFidelity[];
}

export interface ColumnQuality {
  column: string;
  type: string;
  mean_diff?: number;
  std_diff?: number;
  ks_statistic?: number;
  tvd?: number;
  quality: string;
}

export interface SubgroupFidelity {
  subgroup: string;
  label: string;
  original_n: number;
  synthetic_n: number;
  fidelity: number | null;
  warning?: string;
}

export interface PrivacyResult {
  overall_status: string;
  checks: { check: string; passed: boolean; detail: string }[];
  exact_duplicates: {
    exact_duplicates: number;
    duplicate_rate: number;
    columns_compared: string[];
    total_synthetic_records: number;
  };
  nearest_neighbor: {
    mean_distance: number;
    median_distance: number;
    min_distance: number;
    near_copy_count: number;
    near_copy_threshold: number;
    sample_size: number;
  };
  real_to_real_baseline: Record<string, number>;
  synth_to_synth: Record<string, number>;
  disclaimer: string;
}

export interface PrivacyFidelityEntry {
  mode: string;
  fidelity_score: number;
  median_nn_distance: number;
  exact_duplicates: number;
  near_copy_count: number;
  correlation_diff: number | null;
  records_after_filter: number;
  records_rejected: number;
}

export interface Experiment {
  experiment_id: string;
  timestamp: string;
  model: string;
  num_patients: number;
  timeline_days: number;
  constraints: Record<string, unknown>;
  privacy_mode: string;
  seed: number;
  trajectory_dist: Record<string, number>;
  fidelity_summary?: { overall_fidelity: number };
  privacy_summary?: { status: string; exact_duplicates: number; median_nn_distance: number | null };
}

export interface Preset {
  name: string;
  description: string;
  elderly_pct: number;
  diabetes_pct: number;
  hypertension_pct: number;
  htn_among_diabetic_pct: number;
  diabetes_among_elderly_pct: number;
  trajectory_dist: Record<string, number>;
}

export interface PrivacyMode {
  label: string;
  description: string;
  near_copy_threshold: number;
  noise_scale: number;
  rejection_threshold: number;
}
