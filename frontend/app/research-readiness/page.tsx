"use client";

import { useState, useCallback } from "react";
import { ResearchReadiness, ReadinessMetric, api } from "@/lib/api";
import { useApi } from "@/lib/swr";
import { friendlyError } from "@/lib/errors";
import { SkeletonCard } from "@/components/skeleton";
import { StatusBadge } from "@/components/status-badge";
import { toast } from "sonner";
import { useSWRConfig } from "swr";
import { getSection, setSection } from "@/lib/pipeline-session";

function getInitialReadinessForm() {
  const saved = getSection("researchReadiness");
  return {
    utilityTarget: saved?.utilityTarget ?? "diabetes",
    utilityModel: saved?.utilityModel ?? "logistic_regression",
  };
}

function ReadinessBadge({ status }: { status: string }) {
  const s = status.toLowerCase();
  let cls = "badge badge-warning";
  if (s.includes("pass") || s.includes("good") || s.includes("high") || s.includes("ready")) {
    cls = "badge badge-success";
  } else if (s.includes("fail") || s.includes("low") || s.includes("poor")) {
    cls = "badge badge-danger";
  } else if (s.includes("not") || s.includes("pending") || s.includes("unavailable")) {
    cls = "badge";
  }
  return <span className={cls}>{status}</span>;
}

function MetricPanel({
  title,
  metric,
  children,
}: {
  title: string;
  metric: ReadinessMetric;
  children?: React.ReactNode;
}) {
  return (
    <div className="card" style={{ marginBottom: "1rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "0.5rem", marginBottom: "0.75rem" }}>
        <h3 style={{ fontSize: "0.9375rem", fontWeight: 600, color: "var(--foreground)", margin: 0 }}>{title}</h3>
        <ReadinessBadge status={metric.status} />
      </div>
      {metric.value != null && (
        <p className="metric-value" style={{ marginBottom: "0.25rem" }}>
          {typeof metric.value === "number" ? `${(metric.value * 100).toFixed(1)}%` : String(metric.value)}
        </p>
      )}
      {metric.detail && (
        <p style={{ fontSize: "0.8125rem", color: "var(--muted)", marginBottom: "0.5rem" }}>{metric.detail}</p>
      )}
      {children}
    </div>
  );
}

export default function ResearchReadinessPage() {
  const { data, error, isLoading, mutate } = useApi<ResearchReadiness>("/research/readiness", { errorRetryCount: 0 });
  const { mutate: globalMutate } = useSWRConfig();
  
  const initial = getInitialReadinessForm();
  const [utilityTarget, setUtilityTarget] = useState(initial.utilityTarget);
  const [utilityModel, setUtilityModel] = useState(initial.utilityModel);

  const persistForm = useCallback((patch: Partial<{ utilityTarget: string; utilityModel: string }>) => {
    const current = getSection("researchReadiness") ?? {};
    setSection("researchReadiness", { ...current, ...patch });
  }, []);

  const [runningUtility, setRunningUtility] = useState(false);

  const handleRunUtility = async () => {
    const toastId = toast.loading("Running research utility validation...");
    setRunningUtility(true);
    try {
      const result = await api.getResearchUtility({ target: utilityTarget, model_type: utilityModel });
      const retention = result.utility_retention;
      toast.success("Research utility analysis completed", {
        id: toastId,
        description: retention != null ? `Utility retention: ${(retention * 100).toFixed(1)}%` : undefined,
      });
      mutate();
      globalMutate("/overview");
    } catch (err: unknown) {
      toast.error("Research utility analysis failed", {
        id: toastId,
        description: friendlyError(err),
      });
    } finally {
      setRunningUtility(false);
    }
  };

  if (isLoading) {
    return (
      <div>
        <h1 className="page-title">Research Readiness</h1>
        <p className="page-subtitle">Aggregate assessment of synthetic cohort quality</p>
        <div style={{ marginTop: "1.5rem" }}><SkeletonCard lines={2} /></div>
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i} style={{ marginTop: "1rem" }}><SkeletonCard lines={4} /></div>
        ))}
      </div>
    );
  }

  if (error || !data) {
    return (
      <div>
        <h1 className="page-title">Research Readiness</h1>
        <p className="page-subtitle">Aggregate assessment of synthetic cohort quality</p>
        <div className="card" style={{ marginTop: "1rem", display: "flex", alignItems: "center", gap: "0.75rem" }}>
          <StatusBadge label="Readiness" status="not_evaluated" />
        </div>
        <div className="card" style={{ marginTop: "1rem", textAlign: "center", padding: "2rem" }}>
          <p style={{ color: "var(--muted)", marginBottom: "1rem" }}>{error ? friendlyError(error) : "No data available. Generate a cohort first."}</p>
          <button className="btn-primary" onClick={() => mutate()}>Retry</button>
        </div>
      </div>
    );
  }

  const metrics = [
    { key: "statistical_fidelity", title: "Statistical Fidelity" },
    { key: "research_utility", title: "Research Utility (TSTR)" },
    { key: "subgroup_preservation", title: "Subgroup Preservation" },
    { key: "clinical_validity", title: "Clinical Validity" },
    { key: "privacy_screening", title: "Privacy Screening" },
  ] as const;

  const passCount = metrics.filter((m) => {
    const val = data[m.key];
    return val && val.status.toLowerCase().includes("pass");
  }).length;

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
        <div>
          <h1 className="page-title">Research Readiness</h1>
          <p className="page-subtitle">Five independent assessments determine whether a synthetic cohort is suitable for downstream research.</p>
        </div>
        <StatusBadge label="Readiness" status={passCount >= 4 ? "ready" : "not_ready"} />
      </div>

      <div className="mint-card" style={{ marginBottom: "1.5rem" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "1rem", flexWrap: "wrap" }}>
          <p style={{ fontSize: "1.5rem", fontWeight: 700, color: "var(--primary-dark)", margin: 0 }}>
            {passCount} / {metrics.length}
          </p>
          <p style={{ fontSize: "0.875rem", color: "var(--primary)", margin: 0 }}>
            dimensions passing — each metric is evaluated independently; there is no combined score.
          </p>
        </div>
      </div>

      <MetricPanel title="Statistical Fidelity" metric={data.statistical_fidelity}>
        <p style={{ fontSize: "0.75rem", color: "var(--muted)" }}>
          Measures KS similarity, total variation distance, and correlation preservation between real and synthetic distributions.
        </p>
      </MetricPanel>

      <MetricPanel title="Research Utility (TSTR)" metric={data.research_utility}>
        {data.research_utility.real_metrics && data.research_utility.synthetic_metrics && (
          <div className="table-container" style={{ marginTop: "0.5rem" }}>
            <table>
              <thead>
                <tr>
                  <th>Metric</th>
                  <th>Real-Trained</th>
                  <th>Synthetic-Trained</th>
                </tr>
              </thead>
              <tbody>
                {(["accuracy", "f1", "precision", "recall", "roc_auc"] as const).map((k) => (
                  <tr key={k}>
                    <td style={{ textTransform: "uppercase", fontSize: "0.75rem", fontWeight: 500 }}>{k.replace("_", " ")}</td>
                    <td>{data.research_utility.real_metrics?.[k] != null ? data.research_utility.real_metrics[k]!.toFixed(3) : "—"}</td>
                    <td>{data.research_utility.synthetic_metrics?.[k] != null ? data.research_utility.synthetic_metrics[k]!.toFixed(3) : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {data.research_utility.target && (
          <p style={{ fontSize: "0.75rem", color: "var(--muted)", marginTop: "0.25rem" }}>
            Target: {data.research_utility.target}
          </p>
        )}
        <div style={{ marginTop: "0.75rem", padding: "0.75rem", background: "var(--mint)", borderRadius: "0.5rem" }}>
          <div style={{ display: "flex", alignItems: "flex-end", gap: "0.75rem", flexWrap: "wrap" }}>
            <div>
              <label className="metric-label" style={{ display: "block", marginBottom: "0.25rem" }}>Target Variable</label>
              <select className="select-field" value={utilityTarget} onChange={(e) => { setUtilityTarget(e.target.value); persistForm({ utilityTarget: e.target.value }); }} disabled={runningUtility} style={{ minWidth: 140 }}>
                <option value="diabetes">Diabetes</option>
                <option value="hypertension">Hypertension</option>
                <option value="gender">Gender</option>
              </select>
            </div>
            <div>
              <label className="metric-label" style={{ display: "block", marginBottom: "0.25rem" }}>Model Type</label>
              <select className="select-field" value={utilityModel} onChange={(e) => { setUtilityModel(e.target.value); persistForm({ utilityModel: e.target.value }); }} disabled={runningUtility} style={{ minWidth: 160 }}>
                <option value="logistic_regression">Logistic Regression</option>
                <option value="random_forest">Random Forest</option>
                <option value="gradient_boosting">Gradient Boosting</option>
              </select>
            </div>
            <button className="btn-primary" onClick={handleRunUtility} disabled={runningUtility} style={{ display: "inline-flex", alignItems: "center", gap: "0.5rem" }}>
              {runningUtility && <span className="spinner" />}
              {runningUtility ? "Running..." : "Run Utility Analysis"}
            </button>
          </div>
        </div>
      </MetricPanel>

      <MetricPanel title="Subgroup Preservation" metric={data.subgroup_preservation}>
        {data.subgroup_preservation.subgroup_count != null && (
          <p style={{ fontSize: "0.75rem", color: "var(--muted)" }}>
            {data.subgroup_preservation.subgroup_count} subgroups evaluated for distributional fidelity.
          </p>
        )}
      </MetricPanel>

      <MetricPanel title="Clinical Validity" metric={data.clinical_validity}>
        {data.clinical_validity.total_checked != null && (
          <p style={{ fontSize: "0.75rem", color: "var(--muted)" }}>
            {data.clinical_validity.total_checked} records checked, {data.clinical_validity.violations_found ?? 0} violations found
            {data.clinical_validity.repairs && Object.keys(data.clinical_validity.repairs).length > 0 && (
              <> — repairs: {Object.entries(data.clinical_validity.repairs).map(([k, v]) => `${k}: ${v}`).join(", ")}</>
            )}
          </p>
        )}
      </MetricPanel>

      <MetricPanel title="Privacy Screening" metric={data.privacy_screening}>
        {data.privacy_screening.checks && data.privacy_screening.checks.length > 0 && (
          <div style={{ marginTop: "0.5rem" }}>
            {data.privacy_screening.checks.map((c, i) => (
              <div key={i} style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.25rem" }}>
                <span style={{ color: c.passed ? "var(--accent)" : "var(--danger)", fontWeight: 600, fontSize: "0.8125rem" }}>
                  {c.passed ? "PASS" : "FAIL"}
                </span>
                <span style={{ fontSize: "0.8125rem", color: "var(--foreground)" }}>{c.check}</span>
                <span style={{ fontSize: "0.75rem", color: "var(--muted)" }}>— {c.detail}</span>
              </div>
            ))}
          </div>
        )}
      </MetricPanel>

      {data.rare_cohort_coverage && data.rare_cohort_coverage.length > 0 && (
        <div className="card">
          <h2 className="section-title">Rare Cohort Amplification</h2>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Subgroup</th>
                  <th>Source</th>
                  <th>Synthetic</th>
                  <th>Factor</th>
                </tr>
              </thead>
              <tbody>
                {data.rare_cohort_coverage.map((r, i) => (
                  <tr key={i}>
                    <td style={{ fontWeight: 500 }}>{r.subgroup}</td>
                    <td>{r.source_count} ({(r.source_pct * 100).toFixed(1)}%)</td>
                    <td>{r.synthetic_count} ({(r.synthetic_pct * 100).toFixed(1)}%)</td>
                    <td>
                      {r.amplification_factor != null ? (
                        <span style={{ color: r.amplification_factor >= 1 ? "var(--accent)" : "var(--danger)" }}>
                          {r.amplification_factor.toFixed(2)}x
                        </span>
                      ) : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <p style={{ fontSize: "0.75rem", color: "var(--muted)", marginTop: "1rem", fontStyle: "italic" }}>
        These metrics are computed independently. A passing cohort is not guaranteed to be suitable for any specific
        research protocol — researchers should evaluate fitness for purpose in context.
      </p>
    </div>
  );
}
