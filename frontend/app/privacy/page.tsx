"use client";

import { useState } from "react";
import { PrivacyResult } from "@/lib/api";
import { useApi } from "@/lib/swr";
import { friendlyError } from "@/lib/errors";
import { SkeletonCard } from "@/components/skeleton";
import { StatusBadge } from "@/components/status-badge";
import { toast } from "sonner";
import { useSWRConfig } from "swr";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from "recharts";

const normalizeStatus = (status: string | undefined): string => {
  if (!status) return "UNKNOWN";
  const s = status.toUpperCase().trim();
  if (s === "PASS" || s === "PASSED") return "PASSED";
  if (s === "REVIEW_NEEDED" || s === "REVIEW NEEDED") return "REVIEW NEEDED";
  return s;
};

export default function PrivacyPage() {
  const { data, error, isLoading, mutate } = useApi<PrivacyResult>("/privacy", { errorRetryCount: 0 });
  const { data: currentCohort } = useApi<unknown>("/cohort/current", { errorRetryCount: 0 });
  const { mutate: globalMutate } = useSWRConfig();
  const [running, setRunning] = useState(false);

  const handleRunPrivacy = async () => {
    if (!currentCohort) {
      toast.error("Privacy analysis unavailable", {
        id: "privacy-run",
        description: "Generate a synthetic cohort before running privacy screening.",
      });
      return;
    }
    const toastId = "privacy-run";
    toast.loading("Running privacy screening...", { id: toastId });
    setRunning(true);
    try {
      const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
      const res = await fetch(`${API_BASE}/privacy?recompute=true`);
      if (!res.ok) {
        const body = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(body.detail || `Privacy screening failed: ${res.status}`);
      }
      const freshData: PrivacyResult = await res.json();
      freshData.overall_status = normalizeStatus(freshData.overall_status);
      mutate(freshData, false);
      
      const status = freshData.overall_status;
      if (status === "PASSED") {
        toast.success("Privacy screening completed", {
          id: toastId,
          description: "Status: PASSED",
        });
      } else {
        toast.warning("Privacy screening completed", {
          id: toastId,
          description: `Status: ${status}`,
        });
      }
      globalMutate("/overview");
      globalMutate("/research/readiness");
    } catch (err: unknown) {
      toast.error("Privacy screening failed", {
        id: toastId,
        description: friendlyError(err),
      });
    } finally {
      setRunning(false);
    }
  };

  if (isLoading) {
    return (
      <div>
        <h1 className="page-title">Privacy Analysis</h1>
        <p className="page-subtitle">Evaluate privacy protection of synthetic data</p>
        <div style={{ marginTop: "1.5rem" }}><SkeletonCard lines={3} /></div>
        <div style={{ marginTop: "1rem", display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
          <SkeletonCard lines={5} />
          <SkeletonCard lines={5} />
        </div>
        <div style={{ marginTop: "1rem" }}><SkeletonCard lines={8} /></div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div>
        <h1 className="page-title">Privacy Analysis</h1>
        <p className="page-subtitle">Evaluate privacy protection of synthetic data</p>
        <div className="card" style={{ marginTop: "1rem", display: "flex", alignItems: "center", gap: "0.75rem" }}>
          <StatusBadge label="Privacy" status="not_evaluated" />
        </div>
        <div className="card" style={{ textAlign: "center", color: "var(--muted)", padding: "3rem", marginTop: "1rem" }}>
          <p style={{ marginBottom: "1rem" }}>{error ? friendlyError(error) : "Privacy analysis not available. Generate a cohort first."}</p>
          <button className="btn-primary" onClick={handleRunPrivacy} disabled={running} style={{ display: "inline-flex", alignItems: "center", gap: "0.5rem" }}>
            {running && <span className="spinner" />}
            {running ? "Running..." : "Run Privacy Screening"}
          </button>
        </div>
      </div>
    );
  }

  const distanceData = [
    {
      name: "Real-to-Real",
      mean: data.real_to_real_baseline?.mean_distance ?? 0,
      median: data.real_to_real_baseline?.median_distance ?? 0,
    },
    {
      name: "Synth-to-Real",
      mean: data.nearest_neighbor.mean_distance,
      median: data.nearest_neighbor.median_distance,
    },
    {
      name: "Synth-to-Synth",
      mean: data.synth_to_synth?.mean_distance ?? 0,
      median: data.synth_to_synth?.median_distance ?? 0,
    },
  ];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
        <div>
          <h1 className="page-title">Privacy Analysis</h1>
          <p className="page-subtitle">Evaluate privacy protection of synthetic data</p>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
          <button className="btn-secondary" onClick={handleRunPrivacy} disabled={running} style={{ display: "inline-flex", alignItems: "center", gap: "0.5rem" }}>
            {running && <span className="spinner" />}
            {running ? "Running..." : "Re-run Privacy Screening"}
          </button>
          <StatusBadge label="Privacy" status="evaluated" />
        </div>
      </div>

      <div className="card" style={{ marginBottom: "1rem", display: "flex", alignItems: "center", gap: "1rem" }}>
        <span style={{ fontSize: "0.875rem", fontWeight: 500, color: "var(--foreground)" }}>Overall Status:</span>
        <span className={`badge ${normalizeStatus(data.overall_status) === "PASSED" ? "badge-success" : "badge-danger"}`}>
          {normalizeStatus(data.overall_status)}
        </span>
      </div>

      <div className="card" style={{ marginBottom: "1rem" }}>
        <h2 className="section-title">Privacy Checks</h2>
        <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
          {data.checks.map((c, i) => (
            <div key={i} style={{ display: "flex", alignItems: "flex-start", gap: "0.75rem", padding: "0.75rem", borderRadius: "0.5rem", background: "var(--mint)" }}>
              <span className={`status-dot ${c.passed ? "status-dot-success" : "status-dot-danger"}`} style={{ marginTop: "0.375rem" }} />
              <div>
                <div style={{ fontWeight: 500, fontSize: "0.875rem" }}>{c.check}</div>
                <div style={{ fontSize: "0.75rem", color: "var(--muted)", marginTop: "0.125rem" }}>{c.detail}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "1rem", marginBottom: "1rem" }}>
        <div className="card">
          <h2 className="section-title">Exact Duplicates</h2>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ fontSize: "0.875rem", color: "var(--muted)" }}>Duplicates Found</span>
              <span style={{ fontWeight: 600 }}>{data.exact_duplicates.exact_duplicates}</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ fontSize: "0.875rem", color: "var(--muted)" }}>Duplicate Rate</span>
              <span style={{ fontWeight: 600 }}>{(data.exact_duplicates.duplicate_rate * 100).toFixed(2)}%</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ fontSize: "0.875rem", color: "var(--muted)" }}>Total Synthetic Records</span>
              <span style={{ fontWeight: 600 }}>{data.exact_duplicates.total_synthetic_records}</span>
            </div>
            <div style={{ fontSize: "0.75rem", color: "var(--muted)", marginTop: "0.25rem" }}>
              Columns compared: {data.exact_duplicates.columns_compared.join(", ")}
            </div>
          </div>
        </div>

        <div className="card">
          <h2 className="section-title">Nearest Neighbor Analysis</h2>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ fontSize: "0.875rem", color: "var(--muted)" }}>Mean Distance</span>
              <span style={{ fontWeight: 600 }}>{data.nearest_neighbor.mean_distance.toFixed(4)}</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ fontSize: "0.875rem", color: "var(--muted)" }}>Median Distance</span>
              <span style={{ fontWeight: 600 }}>{data.nearest_neighbor.median_distance.toFixed(4)}</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ fontSize: "0.875rem", color: "var(--muted)" }}>Min Distance</span>
              <span style={{ fontWeight: 600 }}>{data.nearest_neighbor.min_distance.toFixed(4)}</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ fontSize: "0.875rem", color: "var(--muted)" }}>Near Copies</span>
              <span style={{ fontWeight: 600, color: data.nearest_neighbor.near_copy_count > 0 ? "var(--warning)" : "var(--accent)" }}>
                {data.nearest_neighbor.near_copy_count}
              </span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ fontSize: "0.875rem", color: "var(--muted)" }}>Threshold</span>
              <span style={{ fontWeight: 600 }}>{data.nearest_neighbor.near_copy_threshold}</span>
            </div>
          </div>
        </div>
      </div>

      <div className="card" style={{ marginBottom: "1rem" }}>
        <h2 className="section-title">Distance Comparison</h2>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={distanceData}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis dataKey="name" tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip />
            <Legend />
            <Bar dataKey="mean" fill="#2F6B5F" name="Mean Distance" />
            <Bar dataKey="median" fill="#4FAE8A" name="Median Distance" />
          </BarChart>
        </ResponsiveContainer>
        <p style={{ fontSize: "0.75rem", color: "var(--muted)", marginTop: "0.5rem" }}>
          Higher synth-to-real distances indicate better privacy. Synth-to-real should be comparable to or higher than real-to-real baseline.
        </p>
      </div>

      <div className="card">
        <h2 className="section-title">Disclaimer</h2>
        <p style={{ fontSize: "0.875rem", color: "var(--muted)" }}>{data.disclaimer}</p>
      </div>
    </div>
  );
}
