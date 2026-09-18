"""Visualization components for the ClinSynth dashboard."""
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots


COLORS = {
    "original": "#2563eb",
    "synthetic": "#f59e0b",
    "pass": "#10b981",
    "fail": "#ef4444",
    "neutral": "#6b7280",
    "accent": "#8b5cf6",
    "low": "#10b981",
    "balanced": "#f59e0b",
    "high": "#ef4444",
}


def distribution_histogram(
    original: pd.Series, synthetic: pd.Series, title: str, xaxis_title: str = ""
) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=original, name="Original", marker_color=COLORS["original"],
        opacity=0.6, nbinsx=30,
    ))
    fig.add_trace(go.Histogram(
        x=synthetic, name="Synthetic", marker_color=COLORS["synthetic"],
        opacity=0.6, nbinsx=30,
    ))
    fig.update_layout(
        title=title, barmode="overlay",
        xaxis_title=xaxis_title or title.replace("Distribution: ", ""),
        yaxis_title="Count",
        template="plotly_white", height=350,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def categorical_bar_chart(
    categories: list, orig_props: list, synth_props: list, title: str
) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=categories, y=orig_props, name="Original",
        marker_color=COLORS["original"], opacity=0.8,
    ))
    fig.add_trace(go.Bar(
        x=categories, y=synth_props, name="Synthetic",
        marker_color=COLORS["synthetic"], opacity=0.8,
    ))
    fig.update_layout(
        title=title, barmode="group",
        yaxis_title="Proportion", template="plotly_white", height=350,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def correlation_heatmap(corr_matrix: pd.DataFrame, title: str) -> go.Figure:
    fig = go.Figure(data=go.Heatmap(
        z=corr_matrix.values, x=corr_matrix.columns.tolist(),
        y=corr_matrix.index.tolist(), colorscale="RdBu_r",
        zmin=-1, zmax=1, text=corr_matrix.round(2).values,
        texttemplate="%{text}", textfont={"size": 10},
    ))
    fig.update_layout(
        title=title, template="plotly_white", height=400,
        xaxis=dict(tickangle=45),
    )
    return fig


def trend_line_chart(
    days: list, orig_means: list, synth_means: list, title: str, yaxis_title: str = ""
) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=days, y=orig_means, name="Original", mode="lines+markers",
        line=dict(color=COLORS["original"], width=2), marker=dict(size=4),
    ))
    fig.add_trace(go.Scatter(
        x=days, y=synth_means, name="Synthetic", mode="lines+markers",
        line=dict(color=COLORS["synthetic"], width=2), marker=dict(size=4),
    ))
    fig.update_layout(
        title=title, xaxis_title="Day", yaxis_title=yaxis_title or title,
        template="plotly_white", height=350,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def distance_distribution_chart(distances: list, threshold: float = 0.1) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=distances, nbinsx=50, name="Distance to Closest Real Record",
        marker_color=COLORS["original"], opacity=0.7,
    ))
    fig.add_vline(x=threshold, line_dash="dash", line_color=COLORS["fail"],
                  annotation_text=f"Near-copy threshold ({threshold})")
    fig.update_layout(
        title="Distance to Closest Real Record",
        xaxis_title="Euclidean Distance (standardized)", yaxis_title="Count",
        template="plotly_white", height=350,
    )
    return fig


def box_plot_comparison(original: pd.Series, synthetic: pd.Series, title: str) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Box(y=original, name="Original", marker_color=COLORS["original"]))
    fig.add_trace(go.Box(y=synthetic, name="Synthetic", marker_color=COLORS["synthetic"]))
    fig.update_layout(title=title, template="plotly_white", height=350)
    return fig


def patient_journey_chart(patient_data: pd.DataFrame, patient_id: str) -> go.Figure:
    p = patient_data[patient_data["patient_id"] == patient_id].sort_values("day")
    if len(p) == 0:
        fig = go.Figure()
        fig.update_layout(title="No data for selected patient")
        return fig

    metrics = ["systolic_bp", "diastolic_bp", "steps", "medication_adherence", "pain_score"]
    available = [m for m in metrics if m in p.columns]

    fig = make_subplots(
        rows=len(available), cols=1, shared_xaxes=True,
        subplot_titles=[m.replace("_", " ").title() for m in available],
        vertical_spacing=0.06,
    )

    colors = ["#2563eb", "#dc2626", "#10b981", "#f59e0b", "#8b5cf6"]
    for i, (metric, color) in enumerate(zip(available, colors)):
        fig.add_trace(
            go.Scatter(x=p["day"], y=p[metric], mode="lines+markers",
                       name=metric.replace("_", " ").title(),
                       line=dict(color=color, width=2), marker=dict(size=4)),
            row=i + 1, col=1,
        )

    fig.update_layout(
        title=f"Patient Journey: {patient_id}",
        height=200 * len(available), template="plotly_white", showlegend=False,
    )
    fig.update_xaxes(title_text="Day", row=len(available), col=1)
    return fig


def patient_journey_with_cohort(
    patient_data: pd.DataFrame,
    patient_id: str,
    all_data: pd.DataFrame,
) -> go.Figure:
    p = patient_data[patient_data["patient_id"] == patient_id].sort_values("day")
    if len(p) == 0:
        fig = go.Figure()
        fig.update_layout(title="No data for selected patient")
        return fig

    metrics = ["systolic_bp", "diastolic_bp", "steps", "medication_adherence", "pain_score"]
    available = [m for m in metrics if m in p.columns]

    fig = make_subplots(
        rows=len(available), cols=1, shared_xaxes=True,
        subplot_titles=[m.replace("_", " ").title() for m in available],
        vertical_spacing=0.06,
    )

    colors = ["#2563eb", "#dc2626", "#10b981", "#f59e0b", "#8b5cf6"]
    cohort_daily = all_data.groupby("day")

    for i, (metric, color) in enumerate(zip(available, colors)):
        if metric in all_data.columns:
            daily_mean = cohort_daily[metric].mean()
            fig.add_trace(
                go.Scatter(x=daily_mean.index, y=daily_mean.values,
                           mode="lines", name=f"Cohort Mean",
                           line=dict(color="#94a3b8", width=1, dash="dash"),
                           showlegend=(i == 0)),
                row=i + 1, col=1,
            )

        fig.add_trace(
            go.Scatter(x=p["day"], y=p[metric], mode="lines+markers",
                       name=metric.replace("_", " ").title(),
                       line=dict(color=color, width=2), marker=dict(size=4)),
            row=i + 1, col=1,
        )

    fig.update_layout(
        title=f"Patient Journey: {patient_id} (vs Cohort Average)",
        height=200 * len(available), template="plotly_white", showlegend=True,
    )
    fig.update_xaxes(title_text="Day", row=len(available), col=1)
    return fig


def cohort_comparison_gauge(requested: float, actual: float, label: str) -> go.Figure:
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=actual * 100,
        delta={"reference": requested * 100, "suffix": "%"},
        title={"text": label},
        gauge={
            "axis": {"range": [0, 100]},
            "bar": {"color": COLORS["synthetic"]},
            "steps": [{"range": [0, requested * 100], "color": "#e0e7ff"}],
            "threshold": {
                "line": {"color": COLORS["original"], "width": 3},
                "thickness": 0.75, "value": requested * 100,
            },
        },
    ))
    fig.update_layout(height=250, template="plotly_white")
    return fig


def privacy_fidelity_scatter(results: list[dict]) -> go.Figure:
    fig = go.Figure()
    mode_colors = {"low": COLORS["low"], "balanced": COLORS["balanced"], "high": COLORS["high"]}

    for r in results:
        mode = r.get("mode", "unknown")
        fig.add_trace(go.Scatter(
            x=[r.get("median_nn_distance", 0)],
            y=[r.get("fidelity_score", 0)],
            mode="markers+text",
            marker=dict(size=16, color=mode_colors.get(mode, COLORS["neutral"])),
            text=[mode.title()],
            textposition="top center",
            name=mode.title(),
        ))

    fig.update_layout(
        title="Privacy vs Fidelity Tradeoff",
        xaxis_title="Median Nearest-Neighbor Distance (higher = more private)",
        yaxis_title="Fidelity Score (higher = more faithful)",
        template="plotly_white", height=400,
    )
    return fig


def model_comparison_bar(comparison_df: pd.DataFrame) -> go.Figure:
    metrics = ["KS Similarity", "Corr Preservation", "Fidelity Score"]
    available = [m for m in metrics if m in comparison_df.columns]
    if not available:
        fig = go.Figure()
        fig.update_layout(title="No comparison metrics available")
        return fig

    fig = go.Figure()
    colors = ["#2563eb", "#f59e0b", "#10b981"]
    for i, metric in enumerate(available):
        vals = comparison_df[metric].tolist()
        fig.add_trace(go.Bar(
            x=comparison_df["Model"].tolist(),
            y=vals,
            name=metric,
            marker_color=colors[i % len(colors)],
        ))

    fig.update_layout(
        title="Model Fidelity Comparison",
        barmode="group", template="plotly_white", height=400,
        yaxis_title="Score",
    )
    return fig


def subgroup_fidelity_bar(subgroup_results: list[dict]) -> go.Figure:
    labels = [r.get("label", r.get("subgroup", "")) for r in subgroup_results]
    fidelities = [r.get("fidelity") or 0 for r in subgroup_results]
    sizes = [r.get("synthetic_n", 0) for r in subgroup_results]

    colors = [COLORS["pass"] if f >= 0.85 else COLORS["synthetic"] if f >= 0.70 else COLORS["fail"]
              for f in fidelities]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=labels, y=fidelities, marker_color=colors,
        text=[f"{f:.2f}" for f in fidelities], textposition="auto",
    ))

    fig.update_layout(
        title="Subgroup Fidelity Analysis",
        yaxis_title="Fidelity Score", yaxis_range=[0, 1],
        template="plotly_white", height=400,
    )
    return fig


def pipeline_visualization() -> go.Figure:
    stages = [
        "Source Data", "Model Training", "Cohort Design",
        "Temporal Journeys", "Validation", "Privacy Check", "Export",
    ]
    x_pos = list(range(len(stages)))

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x_pos, y=[1] * len(stages),
        mode="markers+text",
        marker=dict(size=30, color="#2563eb", symbol="circle"),
        text=stages, textposition="bottom center",
        textfont=dict(size=10),
        showlegend=False,
    ))

    for i in range(len(stages) - 1):
        fig.add_annotation(
            x=x_pos[i] + 0.5, y=1, text="→",
            showarrow=False, font=dict(size=18, color="#64748b"),
        )

    fig.update_layout(
        height=120, template="plotly_white",
        xaxis=dict(visible=False), yaxis=dict(visible=False, range=[0.5, 1.5]),
        margin=dict(l=20, r=20, t=10, b=40),
    )
    return fig
