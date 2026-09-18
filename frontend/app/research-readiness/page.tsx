"use client";

import { useEffect, useState } from "react";
import { api, ResearchReadiness, ReadinessMetric } from "@/lib/api";

function StatusBadge({ status }: { status: string }) {
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
        <StatusBadge status={metric.status} />
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
  const [data, setData] = useState<ResearchReadiness | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const result = await api.getResearchReadiness();
        setData(result);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to load readiness data");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  if (loading) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "40vh" }}>
        <p style={{ color: "var(--muted)" }}>Loading research readiness...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div>
        <h1 className="page-title">Research Readiness</h1>
        <p className="page-subtitle">Aggregate assessment of synthetic cohort quality</p>
        <div className="card" style={{ marginTop: "1.5rem", textAlign: "center", padding: "2rem" }}>
          <p style={{ color: "var(--danger)" }}>{error || "No data available. Generate a cohort first."}</p>
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
      <h1 className="page-title">Research Readiness</h1>
      <p className="page-subtitle">
        Five independent assessments determine whether a synthetic cohort is suitable for downstream research.
      </p>

      {/* Summary bar */}
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

      {/* Metric panels */}
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

      {/* Rare cohort amplification */}
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
