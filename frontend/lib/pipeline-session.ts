const SESSION_KEY = "clinsynth_pipeline_session";

interface PipelineSession {
  train?: {
    synthType?: string;
    mode?: string;
    epochs?: number;
    batchSize?: number;
  };
  cohort?: {
    numPatients?: number;
    timelineDays?: number;
    elderlyPct?: number;
    diabetesPct?: number;
    hypertensionPct?: number;
    htnAmongDiabeticPct?: number | null;
    diabetesAmongElderlyPct?: number | null;
    privacyMode?: string;
    seed?: number;
    stable?: number;
    improving?: number;
    worsening?: number;
    fluctuating?: number;
    selectedPreset?: string;
  };
  researchReadiness?: {
    utilityTarget?: string;
    utilityModel?: string;
  };
}

function read(): PipelineSession {
  try {
    const raw = sessionStorage.getItem(SESSION_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

function write(data: PipelineSession): void {
  try {
    sessionStorage.setItem(SESSION_KEY, JSON.stringify(data));
  } catch {
    // quota exceeded or storage unavailable — silently ignore
  }
}

export function getSection<K extends keyof PipelineSession>(
  key: K
): PipelineSession[K] | undefined {
  return read()[key];
}

export function setSection<K extends keyof PipelineSession>(
  key: K,
  value: PipelineSession[K]
): void {
  const data = read();
  data[key] = value;
  write(data);
}

export function clearDownstream(): void {
  const data = read();
  delete data.cohort;
  delete data.researchReadiness;
  write(data);
}

export function clearAll(): void {
  try {
    sessionStorage.removeItem(SESSION_KEY);
  } catch {
    // ignore
  }
}
