"use client";

import { useState, useCallback } from "react";
import { api, Preset, CohortResult, Constraint } from "@/lib/api";
import { useApi } from "@/lib/swr";
import { friendlyError } from "@/lib/errors";
import { SkeletonCard } from "@/components/skeleton";
import { StatusBadge } from "@/components/status-badge";
import { toast } from "sonner";
import { useSWRConfig } from "swr";
import { getSection, setSection } from "@/lib/pipeline-session";

function getInitialCohortForm() {
  const saved = getSection("cohort");
  return {
    numPatients: saved?.numPatients ?? 500,
    timelineDays: saved?.timelineDays ?? 30,
    elderlyPct: saved?.elderlyPct ?? 0.3,
    diabetesPct: saved?.diabetesPct ?? 0.25,
    hypertensionPct: saved?.hypertensionPct ?? 0.35,
    htnAmongDiabeticPct: saved?.htnAmongDiabeticPct ?? null,
    diabetesAmongElderlyPct: saved?.diabetesAmongElderlyPct ?? null,
    privacyMode: saved?.privacyMode ?? "balanced",
    seed: saved?.seed ?? 42,
    stable: saved?.stable ?? 0.4,
    improving: saved?.improving ?? 0.25,
    worsening: saved?.worsening ?? 0.2,
    fluctuating: saved?.fluctuating ?? 0.15,
    selectedPreset: saved?.selectedPreset ?? "",
  };
}

export default function CohortBuilderPage() {
  const { data: presetsData, error: loadError, isLoading: loadingPresets } = useApi<{ presets: Record<string, Preset> }>("/config/presets");
  const { data: currentCohort } = useApi<CohortResult>("/cohort/current", { errorRetryCount: 0 });
  const { data: dataSummary } = useApi<unknown>("/data/summary", { errorRetryCount: 0 });
  const { data: trainStatus } = useApi<{ trained: boolean }>("/train/status", { errorRetryCount: 0 });
  const { mutate: globalMutate } = useSWRConfig();
  const presets = presetsData?.presets ?? {};

  const initial = getInitialCohortForm();
  const [selectedPreset, setSelectedPreset] = useState<string>(initial.selectedPreset);
  const [numPatients, setNumPatients] = useState(initial.numPatients);
  const [timelineDays, setTimelineDays] = useState(initial.timelineDays);
  const [elderlyPct, setElderlyPct] = useState(initial.elderlyPct);
  const [diabetesPct, setDiabetesPct] = useState(initial.diabetesPct);
  const [hypertensionPct, setHypertensionPct] = useState(initial.hypertensionPct);
  const [htnAmongDiabeticPct, setHtnAmongDiabeticPct] = useState<number | null>(initial.htnAmongDiabeticPct);
  const [diabetesAmongElderlyPct, setDiabetesAmongElderlyPct] = useState<number | null>(initial.diabetesAmongElderlyPct);
  const [privacyMode, setPrivacyMode] = useState(initial.privacyMode);
  const [seed, setSeed] = useState(initial.seed);

  const [stable, setStable] = useState(initial.stable);
  const [improving, setImproving] = useState(initial.improving);
  const [worsening, setWorsening] = useState(initial.worsening);
  const [fluctuating, setFluctuating] = useState(initial.fluctuating);

  const persistCohort = useCallback((patch: Record<string, unknown>) => {
    const current = getSection("cohort") ?? {};
    setSection("cohort", { ...current, ...patch });
  }, []);

  const [generating, setGenerating] = useState(false);
  const [result, setResult] = useState<CohortResult | null>(null);

  const trajectorySum = +(stable + improving + worsening + fluctuating).toFixed(2);

  const applyPreset = (key: string) => {
    setSelectedPreset(key);
    if (!key) { persistCohort({ selectedPreset: "" }); return; }
    const p = presets[key];
    if (!p) return;
    setElderlyPct(p.elderly_pct);
    setDiabetesPct(p.diabetes_pct);
    setHypertensionPct(p.hypertension_pct);
    setHtnAmongDiabeticPct(p.htn_among_diabetic_pct);
    setDiabetesAmongElderlyPct(p.diabetes_among_elderly_pct);
    const s = p.trajectory_dist?.stable ?? 0.4;
    const im = p.trajectory_dist?.improving ?? 0.25;
    const w = p.trajectory_dist?.worsening ?? 0.2;
    const f = p.trajectory_dist?.fluctuating ?? 0.15;
    setStable(s); setImproving(im); setWorsening(w); setFluctuating(f);
    persistCohort({
      selectedPreset: key,
      elderlyPct: p.elderly_pct, diabetesPct: p.diabetes_pct,
      hypertensionPct: p.hypertension_pct,
      htnAmongDiabeticPct: p.htn_among_diabetic_pct,
      diabetesAmongElderlyPct: p.diabetes_among_elderly_pct,
      stable: s, improving: im, worsening: w, fluctuating: f,
    });
  };

  const adjustTrajectory = (
    setter: (v: number) => void,
    newVal: number,
    others: { val: number; set: (v: number) => void; key: string }[]
  ) => {
    const clamped = Math.min(1, Math.max(0, newVal));
    setter(+clamped.toFixed(2));
    const remaining = +(1 - clamped).toFixed(2);
    const othersSum = others.reduce((s, o) => s + o.val, 0);
    const patch: Record<string, number> = {};
    if (othersSum === 0) {
      const each = +(remaining / others.length).toFixed(2);
      others.forEach((o) => { o.set(each); patch[o.key] = each; });
    } else {
      others.forEach((o) => {
        const v = +((o.val / othersSum) * remaining).toFixed(2);
        o.set(v); patch[o.key] = v;
      });
    }
    persistCohort(patch);
  };

  const handleGenerate = async () => {
    if (!dataSummary) {
      toast.error("Generation unavailable", {
        id: "cohort-generate",
        description: "Load a dataset before generating a cohort.",
      });
      return;
    }
    if (!trainStatus || !trainStatus.trained) {
      toast.error("Generation unavailable", {
        id: "cohort-generate",
        description: "Train a model before generating a cohort.",
      });
      return;
    }
    if (trajectorySum !== 1.0) {
      toast.error(`Trajectory distribution must sum to 1.0 (currently ${trajectorySum})`, { id: "cohort-generate" });
      return;
    }
    const toastId = "cohort-generate";
    toast.loading("Generating synthetic cohort...", { id: toastId });
    setGenerating(true);
    setResult(null);
    try {
      const body = {
        num_patients: numPatients,
        timeline_days: timelineDays,
        elderly_pct: elderlyPct,
        diabetes_pct: diabetesPct,
        hypertension_pct: hypertensionPct,
        htn_among_diabetic_pct: htnAmongDiabeticPct,
        diabetes_among_elderly_pct: diabetesAmongElderlyPct,
        privacy_mode: privacyMode,
        seed,
        trajectory_dist: { stable, improving, worsening, fluctuating },
        preset: selectedPreset || null,
      };
      const res = await api.generateCohort(body);
      setResult(res);
      toast.success("Synthetic cohort generated", {
        id: toastId,
        description: `${res.total_patients.toLocaleString()} patients · ${res.longitudinal_records.toLocaleString()} longitudinal records`,
      });
      globalMutate("/overview");
      globalMutate("/cohort/current");
      globalMutate("/validation");
      globalMutate("/privacy");
      globalMutate("/research/readiness");
    } catch (err: unknown) {
      toast.error("Cohort generation failed", {
        id: toastId,
        description: friendlyError(err),
      });
    } finally {
      setGenerating(false);
    }
  };

  const pctLabel = (v: number) => `${(v * 100).toFixed(0)}%`;

  if (loadingPresets) {
    return (
      <div>
        <h1 className="page-title">Cohort Builder</h1>
        <p className="page-subtitle">Configure and generate a synthetic patient cohort</p>
        <div style={{ marginTop: "1.5rem" }}><SkeletonCard lines={8} /></div>
      </div>
    );
  }

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
        <div>
          <h1 className="page-title">Cohort Builder</h1>
          <p className="page-subtitle">Configure and generate a synthetic patient cohort</p>
        </div>
        <StatusBadge label="Cohort" status={result || currentCohort ? "generated" : "not_generated"} />
      </div>

      {loadError && (
        <div className="card" style={{ borderLeft: "4px solid var(--warning)", marginBottom: "1.5rem" }}>
          <strong>Warning:</strong> Could not load presets: {friendlyError(loadError)}
        </div>
      )}

      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <h2 style={{ fontSize: "1.1rem", fontWeight: 600, marginBottom: "1rem" }}>Cohort Configuration</h2>

        <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "1rem" }}>
            <div>
              <label className="metric-label" style={{ display: "block", marginBottom: "0.25rem" }}>Number of Patients</label>
              <input className="input-field" type="number" min={50} max={10000} value={numPatients} onChange={(e) => { const v = Number(e.target.value); setNumPatients(v); persistCohort({ numPatients: v }); }} disabled={generating} />
            </div>
            <div>
              <label className="metric-label" style={{ display: "block", marginBottom: "0.25rem" }}>Timeline (days)</label>
              <input className="input-field" type="number" min={5} max={365} value={timelineDays} onChange={(e) => { const v = Number(e.target.value); setTimelineDays(v); persistCohort({ timelineDays: v }); }} disabled={generating} />
            </div>
            <div>
              <label className="metric-label" style={{ display: "block", marginBottom: "0.25rem" }}>Research Preset</label>
              <select className="select-field" value={selectedPreset} onChange={(e) => applyPreset(e.target.value)} disabled={generating}>
                <option value="">Custom</option>
                {Object.entries(presets).map(([key, p]) => (
                  <option key={key} value={key}>{p.name}</option>
                ))}
              </select>
            </div>
          </div>

          <fieldset style={{ border: "1px solid var(--muted)", borderRadius: 8, padding: "1rem" }}>
            <legend style={{ fontWeight: 600, fontSize: "0.95rem", padding: "0 0.5rem" }}>Demographics</legend>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
              <SliderField label={`Elderly %: ${pctLabel(elderlyPct)}`} value={elderlyPct} onChange={(v) => { setElderlyPct(v); persistCohort({ elderlyPct: v }); }} disabled={generating} />
              <SliderField label={`Diabetes %: ${pctLabel(diabetesPct)}`} value={diabetesPct} onChange={(v) => { setDiabetesPct(v); persistCohort({ diabetesPct: v }); }} disabled={generating} />
              <SliderField label={`Hypertension %: ${pctLabel(hypertensionPct)}`} value={hypertensionPct} onChange={(v) => { setHypertensionPct(v); persistCohort({ hypertensionPct: v }); }} disabled={generating} />
            </div>
          </fieldset>

          <fieldset style={{ border: "1px solid var(--muted)", borderRadius: 8, padding: "1rem" }}>
            <legend style={{ fontWeight: 600, fontSize: "0.95rem", padding: "0 0.5rem" }}>Conditional Constraints (optional)</legend>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
              <NullableSlider label="HTN among Diabetic %" value={htnAmongDiabeticPct} onChange={(v) => { setHtnAmongDiabeticPct(v); persistCohort({ htnAmongDiabeticPct: v }); }} disabled={generating} />
              <NullableSlider label="Diabetes among Elderly %" value={diabetesAmongElderlyPct} onChange={(v) => { setDiabetesAmongElderlyPct(v); persistCohort({ diabetesAmongElderlyPct: v }); }} disabled={generating} />
            </div>
          </fieldset>

          <fieldset style={{ border: "1px solid var(--muted)", borderRadius: 8, padding: "1rem" }}>
            <legend style={{ fontWeight: 600, fontSize: "0.95rem", padding: "0 0.5rem" }}>
              Trajectory Distribution{" "}
              <span style={{ color: trajectorySum === 1.0 ? "var(--success)" : "var(--danger)", fontWeight: 400, fontSize: "0.85rem" }}>
                (sum: {trajectorySum})
              </span>
            </legend>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
              <SliderField label={`Stable: ${pctLabel(stable)}`} value={stable} onChange={(v) => adjustTrajectory(setStable, v, [{ val: improving, set: setImproving, key: "improving" }, { val: worsening, set: setWorsening, key: "worsening" }, { val: fluctuating, set: setFluctuating, key: "fluctuating" }])} disabled={generating} />
              <SliderField label={`Improving: ${pctLabel(improving)}`} value={improving} onChange={(v) => adjustTrajectory(setImproving, v, [{ val: stable, set: setStable, key: "stable" }, { val: worsening, set: setWorsening, key: "worsening" }, { val: fluctuating, set: setFluctuating, key: "fluctuating" }])} disabled={generating} />
              <SliderField label={`Worsening: ${pctLabel(worsening)}`} value={worsening} onChange={(v) => adjustTrajectory(setWorsening, v, [{ val: stable, set: setStable, key: "stable" }, { val: improving, set: setImproving, key: "improving" }, { val: fluctuating, set: setFluctuating, key: "fluctuating" }])} disabled={generating} />
              <SliderField label={`Fluctuating: ${pctLabel(fluctuating)}`} value={fluctuating} onChange={(v) => adjustTrajectory(setFluctuating, v, [{ val: stable, set: setStable, key: "stable" }, { val: improving, set: setImproving, key: "improving" }, { val: worsening, set: setWorsening, key: "worsening" }])} disabled={generating} />
            </div>
          </fieldset>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
            <div>
              <label className="metric-label" style={{ display: "block", marginBottom: "0.25rem" }}>Privacy Mode</label>
              <select className="select-field" value={privacyMode} onChange={(e) => { setPrivacyMode(e.target.value); persistCohort({ privacyMode: e.target.value }); }} disabled={generating}>
                <option value="low">Low</option>
                <option value="balanced">Balanced</option>
                <option value="high">High</option>
              </select>
            </div>
            <div>
              <label className="metric-label" style={{ display: "block", marginBottom: "0.25rem" }}>Seed</label>
              <input className="input-field" type="number" value={seed} onChange={(e) => { const v = Number(e.target.value); setSeed(v); persistCohort({ seed: v }); }} disabled={generating} />
            </div>
          </div>

          <button className="btn-primary" onClick={handleGenerate} disabled={generating} style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "0.5rem", marginTop: "0.5rem" }}>
            {generating && <span className="spinner" />}
            {generating ? "Generating..." : "Generate Cohort"}
          </button>
        </div>
      </div>

      {result && (
        <div className="card" style={{ borderLeft: "4px solid var(--success)" }}>
          <h2 style={{ fontSize: "1.1rem", fontWeight: 600, marginBottom: "1rem" }}>Generation Results</h2>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "1rem", marginBottom: "1.5rem" }}>
            <div><div className="metric-label">Total Patients</div><div className="metric-value">{result.total_patients.toLocaleString()}</div></div>
            <div><div className="metric-label">Longitudinal Records</div><div className="metric-value">{result.longitudinal_records.toLocaleString()}</div></div>
            <div><div className="metric-label">Timeline</div><div className="metric-value">{result.timeline_days} days</div></div>
          </div>

          {result.constraints && result.constraints.length > 0 && (
            <div style={{ marginBottom: "1.5rem" }}>
              <h3 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "0.5rem" }}>Constraints</h3>
              <div className="table-container">
                <table style={{ width: "100%", borderCollapse: "collapse" }}>
                  <thead>
                    <tr><th style={thStyle}>Constraint</th><th style={thStyle}>Requested</th><th style={thStyle}>Actual</th><th style={thStyle}>Error</th></tr>
                  </thead>
                  <tbody>
                    {result.constraints.map((c: Constraint, i: number) => (
                      <tr key={i}>
                        <td style={tdStyle}>{c.constraint}</td>
                        <td style={tdStyle}>{c.requested != null ? `${(c.requested * 100).toFixed(1)}%` : "--"}</td>
                        <td style={tdStyle}>{c.actual != null ? `${(c.actual * 100).toFixed(1)}%` : "--"}</td>
                        <td style={tdStyle}>
                          {c.error != null ? (
                            <span className={Math.abs(c.error) < 0.05 ? "badge-success" : Math.abs(c.error) < 0.1 ? "badge-warning" : "badge-info"}>
                              {(c.error * 100).toFixed(2)}%
                            </span>
                          ) : "--"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {result.trajectory_distribution && (
            <div>
              <h3 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "0.5rem" }}>Trajectory Distribution</h3>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: "0.75rem" }}>
                {Object.entries(result.trajectory_distribution).map(([key, val]) => (
                  <div key={key} style={{ textAlign: "center", padding: "0.75rem", borderRadius: 8, background: "var(--primary)", color: "#fff", opacity: 0.85 }}>
                    <div style={{ fontSize: "0.8rem", textTransform: "capitalize" }}>{key}</div>
                    <div style={{ fontSize: "1.25rem", fontWeight: 700 }}>{val as number}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function SliderField({ label, value, onChange, disabled }: { label: string; value: number; onChange: (v: number) => void; disabled: boolean }) {
  return (
    <div>
      <label className="metric-label" style={{ display: "block", marginBottom: "0.25rem" }}>{label}</label>
      <input type="range" min={0} max={1} step={0.01} value={value} onChange={(e) => onChange(Number(e.target.value))} disabled={disabled} style={{ width: "100%" }} />
    </div>
  );
}

function NullableSlider({ label, value, onChange, disabled }: { label: string; value: number | null; onChange: (v: number | null) => void; disabled: boolean }) {
  const enabled = value !== null;
  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.25rem" }}>
        <input type="checkbox" checked={enabled} onChange={(e) => onChange(e.target.checked ? 0.5 : null)} disabled={disabled} />
        <label className="metric-label">{label}{enabled ? `: ${(value! * 100).toFixed(0)}%` : " (disabled)"}</label>
      </div>
      {enabled && <input type="range" min={0} max={1} step={0.01} value={value!} onChange={(e) => onChange(Number(e.target.value))} disabled={disabled} style={{ width: "100%" }} />}
    </div>
  );
}

const thStyle: React.CSSProperties = { textAlign: "left", padding: "0.75rem 1rem", borderBottom: "2px solid var(--border)", fontSize: "0.75rem", fontWeight: 600, color: "var(--muted)", textTransform: "uppercase", letterSpacing: "0.05em" };
const tdStyle: React.CSSProperties = { padding: "0.75rem 1rem", borderBottom: "1px solid var(--border)", fontSize: "0.875rem" };
