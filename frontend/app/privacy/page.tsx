"use client";

import { useEffect, useState } from "react";
import { api, PrivacyResult } from "@/lib/api";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from "recharts";

export default function PrivacyPage() {
  const [data, setData] = useState<PrivacyResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api.getPrivacy()
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="p-8 text-center text-slate-500">Loading privacy analysis...</div>;

  if (error) {
    return (
      <div className="max-w-4xl space-y-6">
        <h1 className="page-title">Privacy Analysis</h1>
        <div className="card text-center text-slate-500 py-12">
          Privacy analysis not available. Generate a cohort first.
        </div>
      </div>
    );
  }

  if (!data) return null;

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
    <div className="max-w-6xl space-y-6">
      <div>
        <h1 className="page-title">Privacy Analysis</h1>
        <p className="page-subtitle">Evaluate privacy protection of synthetic data</p>
      </div>

      <div className="card flex items-center gap-4">
        <span className="text-sm font-medium text-slate-600">Overall Status:</span>
        <span className={`badge text-base px-4 py-1 ${data.overall_status === "PASS" ? "badge-success" : "badge-danger"}`}>
          {data.overall_status}
        </span>
      </div>

      <div className="card">
        <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-3">Privacy Checks</h2>
        <div className="space-y-2">
          {data.checks.map((c, i) => (
            <div key={i} className="flex items-start gap-3 p-3 rounded-lg bg-slate-50">
              <span className={`status-dot mt-1.5 ${c.passed ? "status-dot-success" : "status-dot-danger"}`} />
              <div>
                <div className="font-medium text-sm">{c.check}</div>
                <div className="text-xs text-slate-500 mt-0.5">{c.detail}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <div className="card">
          <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-3">Exact Duplicates</h2>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-sm text-slate-600">Duplicates Found</span>
              <span className="font-semibold">{data.exact_duplicates.exact_duplicates}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-slate-600">Duplicate Rate</span>
              <span className="font-semibold">{(data.exact_duplicates.duplicate_rate * 100).toFixed(2)}%</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-slate-600">Total Synthetic Records</span>
              <span className="font-semibold">{data.exact_duplicates.total_synthetic_records}</span>
            </div>
            <div className="text-xs text-slate-400 mt-2">
              Columns compared: {data.exact_duplicates.columns_compared.join(", ")}
            </div>
          </div>
        </div>

        <div className="card">
          <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-3">Nearest Neighbor Analysis</h2>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-sm text-slate-600">Mean Distance</span>
              <span className="font-semibold">{data.nearest_neighbor.mean_distance.toFixed(4)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-slate-600">Median Distance</span>
              <span className="font-semibold">{data.nearest_neighbor.median_distance.toFixed(4)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-slate-600">Min Distance</span>
              <span className="font-semibold">{data.nearest_neighbor.min_distance.toFixed(4)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-slate-600">Near Copies</span>
              <span className={`font-semibold ${data.nearest_neighbor.near_copy_count > 0 ? "text-yellow-600" : "text-green-600"}`}>
                {data.nearest_neighbor.near_copy_count}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-slate-600">Threshold</span>
              <span className="font-semibold">{data.nearest_neighbor.near_copy_threshold}</span>
            </div>
          </div>
        </div>
      </div>

      <div className="card">
        <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-3">Distance Comparison</h2>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={distanceData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey="name" tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip />
            <Legend />
            <Bar dataKey="mean" fill="#0d9488" name="Mean Distance" />
            <Bar dataKey="median" fill="#0ea5e9" name="Median Distance" />
          </BarChart>
        </ResponsiveContainer>
        <p className="text-xs text-slate-400 mt-2">
          Higher synth-to-real distances indicate better privacy. Synth-to-real should be comparable to or higher than real-to-real baseline.
        </p>
      </div>

      <div className="card">
        <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-3">Disclaimer</h2>
        <p className="text-sm text-slate-600">{data.disclaimer}</p>
      </div>
    </div>
  );
}
