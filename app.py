"""ClinSynth — Privacy-Preserving Synthetic Patient Data Platform.

Main Streamlit application.
"""
import sys
import time
from datetime import datetime
from pathlib import Path

import streamlit as st
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.data.loader import load_demo_dataset, load_uploaded_csv, detect_dataset_type, map_schema, get_data_summary
from src.preprocessing.pipeline import preprocess_profiles, preprocess_longitudinal, get_quality_report
from src.preprocessing.guardrails import check_plausibility, repair_profiles, repair_longitudinal
from src.synthesis.synthesizer import train_synthesizer, save_synthesizer, load_synthesizer, generate_samples, build_metadata
from src.synthesis.comparison import compare_models, format_comparison_table
from src.cohort.builder import build_cohort
from src.temporal.generator import TemporalEngine
from src.validation.engine import (
    validate_profiles, validate_longitudinal, compute_fidelity_summary,
    compute_per_column_quality, compute_all_subgroup_fidelity,
)
from src.privacy.evaluator import (
    privacy_screening, apply_privacy_mode, nearest_neighbor_analysis, detect_exact_duplicates,
)
from src.visualization.charts import (
    distribution_histogram, categorical_bar_chart, correlation_heatmap,
    trend_line_chart, distance_distribution_chart, box_plot_comparison,
    patient_journey_chart, patient_journey_with_cohort, cohort_comparison_gauge,
    privacy_fidelity_scatter, model_comparison_bar, subgroup_fidelity_bar,
    pipeline_visualization,
)
from src.utils.export import export_csv, export_json, create_export_zip, create_quality_report
from src.utils.config import (
    DEFAULT_COHORT, MODELS_DIR, RANDOM_SEED, RESEARCH_PRESETS,
    PRIVACY_MODES, DEFAULT_TRAJECTORY_DIST, TRAJECTORY_TYPES,
)
from src.utils.experiments import save_experiment, list_experiments, load_experiment


st.set_page_config(
    page_title="ClinSynth",
    page_icon=":hospital:",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .main-header { font-size: 2.2rem; font-weight: 700; color: #1e3a5f; margin-bottom: 0; }
    .sub-header { font-size: 1rem; color: #64748b; margin-top: -0.5rem; }
    .tagline { font-size: 0.85rem; color: #94a3b8; font-style: italic; }
    .metric-card {
        background: #f8fafc; border-radius: 8px; padding: 1rem;
        border-left: 4px solid #2563eb; margin-bottom: 0.5rem;
    }
    .status-pass { color: #10b981; font-weight: 600; }
    .status-fail { color: #ef4444; font-weight: 600; }
    .status-pending { color: #f59e0b; font-weight: 600; }
    .constraint-table th { text-align: left; padding: 0.5rem; }
    .constraint-table td { padding: 0.5rem; }
</style>
""", unsafe_allow_html=True)


def init_session_state():
    defaults = {
        "profiles": None, "longitudinal": None,
        "profiles_processed": None, "longitudinal_processed": None,
        "synthesizer": None, "train_info": None,
        "synthetic_profiles": None, "synthetic_longitudinal": None,
        "cohort_stats": None, "cohort_config": None,
        "validation_profile_results": None, "validation_long_results": None,
        "fidelity_summary": None, "privacy_results": None,
        "data_loaded": False, "model_trained": False, "cohort_generated": False,
        "model_comparison_results": None,
        "current_seed": RANDOM_SEED,
        "privacy_mode": "balanced",
        "trajectory_dist": dict(DEFAULT_TRAJECTORY_DIST),
        "plausibility_stats": None,
        "current_experiment_id": None,
        "subgroup_fidelity": None,
        "per_column_quality": None,
        "privacy_fidelity_results": None,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


init_session_state()


# --- Sidebar ---
with st.sidebar:
    st.markdown('<p class="main-header">ClinSynth</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Synthetic Patient Data Platform</p>', unsafe_allow_html=True)
    st.markdown('<p class="tagline">Realistic Data. Zero Patient Exposure.</p>', unsafe_allow_html=True)
    st.divider()

    st.markdown("**Pipeline Status**")
    col1, col2 = st.columns(2)
    with col1:
        if st.session_state.data_loaded:
            st.success("Dataset", icon=":material/check_circle:")
        else:
            st.info("Dataset", icon=":material/pending:")
        if st.session_state.cohort_generated:
            st.success("Cohort", icon=":material/check_circle:")
        else:
            st.info("Cohort", icon=":material/pending:")
    with col2:
        if st.session_state.model_trained:
            st.success("Model", icon=":material/check_circle:")
        else:
            st.info("Model", icon=":material/pending:")
        if st.session_state.privacy_results is not None:
            status = st.session_state.privacy_results.get("overall_status", "")
            if status == "PASSED":
                st.success("Privacy", icon=":material/check_circle:")
            else:
                st.warning("Privacy", icon=":material/warning:")
        else:
            st.info("Privacy", icon=":material/pending:")

    st.divider()
    page = st.radio(
        "Navigation",
        ["Overview", "Data", "Train", "Cohort Builder", "Synthetic Cohort",
         "Patient Journeys", "Validation", "Privacy", "Privacy vs Fidelity",
         "Model Comparison", "Experiments", "Export"],
        label_visibility="collapsed",
    )


# ======================= PAGES =======================

if page == "Overview":
    st.markdown("## ClinSynth")
    st.markdown("### Privacy-Preserving Synthetic Patient Data Platform")

    st.plotly_chart(pipeline_visualization(), use_container_width=True)

    st.divider()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        n_src = len(st.session_state.profiles_processed) if st.session_state.profiles_processed is not None else 0
        st.metric("Source Patients", f"{n_src:,}")
    with col2:
        n_long = len(st.session_state.longitudinal_processed) if st.session_state.longitudinal_processed is not None else 0
        st.metric("Source Records", f"{n_long:,}")
    with col3:
        model_name = "None"
        if st.session_state.train_info:
            model_name = st.session_state.train_info["synth_type"].replace("Synthesizer", "")
        st.metric("Active Model", model_name)
    with col4:
        n_synth = len(st.session_state.synthetic_profiles) if st.session_state.synthetic_profiles is not None else 0
        st.metric("Generated Patients", f"{n_synth:,}")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        n_synth_long = len(st.session_state.synthetic_longitudinal) if st.session_state.synthetic_longitudinal is not None else 0
        st.metric("Generated Records", f"{n_synth_long:,}")
    with col2:
        fid = st.session_state.fidelity_summary
        fid_score = f"{fid['overall_fidelity']:.2%}" if fid else "N/A"
        st.metric("Fidelity Score", fid_score)
    with col3:
        priv = st.session_state.privacy_results
        priv_status = priv["overall_status"] if priv else "Pending"
        st.metric("Privacy Status", priv_status)
    with col4:
        st.metric("Seed", st.session_state.current_seed)

    if st.session_state.cohort_stats:
        st.divider()
        st.markdown("#### Current Experiment")
        stats = st.session_state.cohort_stats
        constraints = stats.get("constraints", [])
        if constraints:
            df = pd.DataFrame(constraints)
            df["requested"] = df["requested"].apply(lambda x: f"{x:.1%}" if x is not None else "N/A")
            df["actual"] = df["actual"].apply(lambda x: f"{x:.1%}" if x is not None else "N/A")
            df["error"] = df["error"].apply(lambda x: f"{x:.1%}" if x is not None else "N/A")
            st.dataframe(df, use_container_width=True, hide_index=True)

    st.divider()
    st.info(
        "ClinSynth generates synthetic patient cohorts for healthcare research. "
        "Generated data is not clinically validated. Privacy screening provides "
        "metrics, not formal guarantees.",
        icon=":material/info:",
    )


elif page == "Data":
    st.markdown("## Data")
    st.divider()

    tab1, tab2 = st.tabs(["Bundled Demo Dataset", "Upload CSV"])

    with tab1:
        st.markdown("Load the bundled demo dataset (~500 synthetic sample patients with 30-day longitudinal records).")
        st.caption("Demo records are deterministically generated sample data and do not represent real patients.")
        if st.button("Load Demo Dataset", type="primary"):
            with st.spinner("Loading demo dataset..."):
                profiles, longitudinal = load_demo_dataset()
                st.session_state.profiles = profiles
                st.session_state.longitudinal = longitudinal
                st.session_state.profiles_processed = preprocess_profiles(profiles)
                st.session_state.longitudinal_processed = preprocess_longitudinal(longitudinal)
                st.session_state.data_loaded = True
                st.session_state.model_trained = False
                st.session_state.cohort_generated = False
                st.session_state.synthesizer = None
                st.session_state.model_comparison_results = None
            st.success("Demo dataset loaded.")
            st.rerun()

    with tab2:
        st.markdown("Upload your own CSV file. The system will attempt to detect and map the schema.")
        uploaded = st.file_uploader("Upload CSV", type=["csv"])
        if uploaded is not None:
            df = load_uploaded_csv(uploaded, uploaded.name)
            dtype = detect_dataset_type(df)
            st.info(f"Detected dataset type: **{dtype}**")
            df = map_schema(df, dtype)

            if dtype == "profile":
                st.session_state.profiles = df
                st.session_state.profiles_processed = preprocess_profiles(df)
                if st.session_state.longitudinal is None:
                    st.warning("No longitudinal data loaded. Temporal features will use generated data.")
                st.session_state.data_loaded = True
            elif dtype == "longitudinal":
                st.session_state.longitudinal = df
                st.session_state.longitudinal_processed = preprocess_longitudinal(df)
                if st.session_state.profiles is None:
                    st.warning("No profile data loaded. Please also upload a profile dataset.")
            else:
                st.warning("Could not determine dataset type. Please ensure columns match the expected schema.")
            st.rerun()

    if st.session_state.data_loaded:
        st.divider()
        st.markdown("### Dataset Summary")
        profiles = st.session_state.profiles_processed
        longitudinal = st.session_state.longitudinal_processed

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Patients", len(profiles))
        with col2:
            st.metric("Longitudinal Records", len(longitudinal) if longitudinal is not None else 0)
        with col3:
            st.metric("Profile Columns", len(profiles.columns))

        quality = get_quality_report(profiles)
        missing_total = quality["missing_total"]
        if missing_total > 0:
            st.warning(f"Missing values detected: {missing_total}")
        else:
            st.success("No missing values in profile data.")

        st.markdown("**Detected Variable Types**")
        st.json(quality["column_types"])

        st.markdown("### Profile Data Preview")
        st.dataframe(profiles.head(20), use_container_width=True)

        st.markdown("### Profile Summary Statistics")
        st.dataframe(profiles.describe(), use_container_width=True)

        if longitudinal is not None and len(longitudinal) > 0:
            st.markdown("### Longitudinal Data Preview")
            st.dataframe(longitudinal.head(20), use_container_width=True)
    else:
        st.info("Load a dataset to get started.")


elif page == "Train":
    st.markdown("## Train Synthesizer")
    st.divider()

    if not st.session_state.data_loaded:
        st.warning("Please load a dataset first.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            synth_type = st.selectbox(
                "Synthesizer",
                ["CTGANSynthesizer", "GaussianCopulaSynthesizer"],
                help="CTGAN learns complex relationships but takes longer. "
                     "Gaussian Copula is faster and more stable for small datasets.",
            )
        with col2:
            mode = st.selectbox("Mode", ["Demo (fast)", "Standard", "High Quality"])

        epoch_map = {"Demo (fast)": 50, "Standard": 150, "High Quality": 300}
        epochs = epoch_map[mode]

        with st.expander("Advanced Settings"):
            epochs = st.number_input("Epochs (CTGAN only)", 10, 1000, epochs)
            batch_size = st.number_input("Batch Size", 50, 5000, 500)

        st.caption(f"Training data: {len(st.session_state.profiles_processed)} patients")

        if st.button("Train Model", type="primary"):
            profiles = st.session_state.profiles_processed
            train_df = profiles.drop(columns=["patient_id"], errors="ignore")

            progress = st.progress(0, text="Initializing...")
            status = st.empty()

            try:
                status.info(f"Training {synth_type}...")
                progress.progress(10, text="Fitting model...")

                synthesizer, info = train_synthesizer(
                    train_df, synth_type=synth_type,
                    epochs=epochs, batch_size=batch_size,
                )

                progress.progress(80, text="Saving model...")
                save_synthesizer(synthesizer)

                progress.progress(100, text="Complete!")
                st.session_state.synthesizer = synthesizer
                st.session_state.train_info = info
                st.session_state.model_trained = True
                st.session_state.cohort_generated = False

                status.success("Model trained and saved!")
            except Exception as e:
                if synth_type == "CTGANSynthesizer":
                    status.warning(f"CTGAN failed ({e}). Falling back to Gaussian Copula...")
                    try:
                        synthesizer, info = train_synthesizer(
                            train_df, synth_type="GaussianCopulaSynthesizer",
                        )
                        save_synthesizer(synthesizer)
                        st.session_state.synthesizer = synthesizer
                        st.session_state.train_info = info
                        st.session_state.model_trained = True
                        progress.progress(100, text="Fallback complete!")
                        status.success("Gaussian Copula trained as fallback.")
                    except Exception as e2:
                        status.error(f"Training failed: {e2}")
                else:
                    status.error(f"Training failed: {e}")

        if st.session_state.train_info:
            st.divider()
            st.markdown("### Training Results")
            info = st.session_state.train_info
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Model", info["synth_type"].replace("Synthesizer", ""))
            with col2:
                st.metric("Rows", info["training_rows"])
            with col3:
                ep = info.get("epochs")
                st.metric("Epochs", ep if ep else "N/A")
            with col4:
                st.metric("Duration", f"{info['duration_seconds']}s")


elif page == "Cohort Builder":
    st.markdown("## Cohort Builder")
    st.divider()

    if not st.session_state.model_trained:
        st.warning("Please train a model first.")
    else:
        st.markdown("#### Research Scenario Presets")
        st.caption("Simulation presets for research — not clinical recommendations.")
        preset_options = ["Custom"] + [v["name"] for v in RESEARCH_PRESETS.values()]
        preset_keys = ["custom"] + list(RESEARCH_PRESETS.keys())
        selected_preset_name = st.selectbox("Preset", preset_options)
        selected_preset_key = preset_keys[preset_options.index(selected_preset_name)]

        if selected_preset_key != "custom":
            preset = RESEARCH_PRESETS[selected_preset_key]
            st.info(preset["description"])
            default_elderly = int(preset["elderly_pct"] * 100)
            default_diabetes = int(preset["diabetes_pct"] * 100)
            default_htn = int(preset["hypertension_pct"] * 100)
            default_htn_dm = int(preset["htn_among_diabetic_pct"] * 100)
            default_dm_elderly = int(preset["diabetes_among_elderly_pct"] * 100)
            default_traj = preset["trajectory_dist"]
        else:
            default_elderly = int(DEFAULT_COHORT["elderly_pct"] * 100)
            default_diabetes = int(DEFAULT_COHORT["diabetes_pct"] * 100)
            default_htn = int(DEFAULT_COHORT["hypertension_pct"] * 100)
            default_htn_dm = 40
            default_dm_elderly = 30
            default_traj = DEFAULT_TRAJECTORY_DIST

        st.markdown("#### Cohort Parameters")
        col1, col2 = st.columns(2)
        with col1:
            num_patients = st.number_input(
                "Number of Synthetic Patients", 100, 50000, DEFAULT_COHORT["num_patients"], step=100,
            )
            elderly_pct = st.slider("Target Age 60+ (%)", 0, 100, default_elderly) / 100
            diabetes_pct = st.slider("Target Diabetes (%)", 0, 100, default_diabetes) / 100
        with col2:
            hypertension_pct = st.slider("Target Hypertension (%)", 0, 100, default_htn) / 100
            timeline_days = st.select_slider(
                "Longitudinal Timeline (days)", options=[7, 14, 30, 60, 90], value=30,
            )

        st.markdown("#### Conditional Constraints")
        htn_among_dm = st.slider("HTN among Diabetic (%)", 0, 100, default_htn_dm) / 100
        dm_among_elderly = st.slider("DM among Age 60+ (%)", 0, 100, default_dm_elderly) / 100

        st.markdown("#### Trajectory Distribution")
        st.caption("Synthetic simulation patterns — not clinically validated disease progression.")
        tcol1, tcol2, tcol3, tcol4 = st.columns(4)
        with tcol1:
            t_stable = st.number_input("Stable (%)", 0, 100, int(default_traj.get("stable", 50) * 100))
        with tcol2:
            t_improving = st.number_input("Improving (%)", 0, 100, int(default_traj.get("improving", 20) * 100))
        with tcol3:
            t_worsening = st.number_input("Worsening (%)", 0, 100, int(default_traj.get("worsening", 15) * 100))
        with tcol4:
            t_fluctuating = st.number_input("Fluctuating (%)", 0, 100, int(default_traj.get("fluctuating", 15) * 100))

        traj_total = t_stable + t_improving + t_worsening + t_fluctuating
        if traj_total != 100:
            st.warning(f"Trajectory percentages sum to {traj_total}%. They will be normalized to 100%.")

        trajectory_dist = {
            "stable": t_stable / max(traj_total, 1),
            "improving": t_improving / max(traj_total, 1),
            "worsening": t_worsening / max(traj_total, 1),
            "fluctuating": t_fluctuating / max(traj_total, 1),
        }

        st.markdown("#### Privacy & Reproducibility")
        pcol1, pcol2 = st.columns(2)
        with pcol1:
            privacy_mode = st.selectbox(
                "Privacy Mode",
                list(PRIVACY_MODES.keys()),
                index=1,
                format_func=lambda x: PRIVACY_MODES[x]["label"],
            )
            st.caption(PRIVACY_MODES[privacy_mode]["description"])
        with pcol2:
            seed = st.number_input("Random Seed", 0, 999999, st.session_state.current_seed)

        st.divider()

        if st.button("Generate Synthetic Cohort", type="primary"):
            st.session_state.current_seed = seed
            st.session_state.privacy_mode = privacy_mode
            st.session_state.trajectory_dist = trajectory_dist

            with st.spinner("Generating synthetic profiles..."):
                raw = generate_samples(st.session_state.synthesizer, num_patients * 5)
                cohort, stats = build_cohort(
                    raw, num_patients=num_patients,
                    elderly_pct=elderly_pct, diabetes_pct=diabetes_pct,
                    hypertension_pct=hypertension_pct,
                    htn_among_diabetic_pct=htn_among_dm,
                    diabetes_among_elderly_pct=dm_among_elderly,
                    seed=seed,
                )

            if privacy_mode != "low":
                with st.spinner(f"Applying {privacy_mode} privacy filtering..."):
                    orig = st.session_state.profiles_processed
                    cohort, priv_stats = apply_privacy_mode(cohort, orig, mode=privacy_mode, seed=seed)
                    if len(cohort) < num_patients:
                        st.info(f"Privacy filtering reduced cohort from {num_patients} to {len(cohort)} patients.")
                    cohort["patient_id"] = [f"SYN-{i+1:06d}" for i in range(len(cohort))]
                    stats["privacy_filter_stats"] = priv_stats

            with st.spinner("Applying plausibility checks..."):
                cohort = repair_profiles(cohort)

            with st.spinner("Generating longitudinal health journeys..."):
                engine = TemporalEngine(seed=seed)
                if st.session_state.profiles_processed is not None and st.session_state.longitudinal_processed is not None:
                    engine.learn_from_data(
                        st.session_state.profiles_processed,
                        st.session_state.longitudinal_processed,
                    )
                synth_long = engine.generate_journeys(cohort, days=timeline_days, trajectory_dist=trajectory_dist)

            with st.spinner("Applying longitudinal guardrails..."):
                synth_long = repair_longitudinal(synth_long)

            plaus = check_plausibility(cohort, synth_long)

            cohort_config = {
                "num_patients": len(cohort),
                "timeline_days": timeline_days,
                "elderly_pct": elderly_pct,
                "diabetes_pct": diabetes_pct,
                "hypertension_pct": hypertension_pct,
                "htn_among_diabetic_pct": htn_among_dm,
                "diabetes_among_elderly_pct": dm_among_elderly,
                "privacy_mode": privacy_mode,
                "seed": seed,
                "trajectory_dist": trajectory_dist,
                "preset": selected_preset_key,
            }

            st.session_state.synthetic_profiles = cohort
            st.session_state.synthetic_longitudinal = synth_long
            st.session_state.cohort_stats = stats
            st.session_state.cohort_config = cohort_config
            st.session_state.cohort_generated = True
            st.session_state.plausibility_stats = plaus

            st.session_state.validation_profile_results = None
            st.session_state.validation_long_results = None
            st.session_state.fidelity_summary = None
            st.session_state.privacy_results = None
            st.session_state.subgroup_fidelity = None
            st.session_state.per_column_quality = None
            st.session_state.privacy_fidelity_results = None

            st.success(f"Generated {len(cohort)} patients with {len(synth_long)} longitudinal records.")
            st.rerun()


elif page == "Synthetic Cohort":
    st.markdown("## Synthetic Cohort")
    st.divider()

    if not st.session_state.cohort_generated:
        st.warning("Please generate a cohort first.")
    else:
        stats = st.session_state.cohort_stats
        cohort = st.session_state.synthetic_profiles
        synth_long = st.session_state.synthetic_longitudinal

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Patients", f"{stats['total_patients']:,}")
        with col2:
            st.metric("Longitudinal Records", f"{len(synth_long):,}")
        with col3:
            st.metric("Timeline", f"{synth_long['day'].max()} days")
        with col4:
            st.metric("Seed", st.session_state.current_seed)

        st.markdown("### Constraint Satisfaction")
        constraints = stats.get("constraints", [])
        if constraints:
            cdf = pd.DataFrame(constraints)
            cdf["requested"] = cdf["requested"].apply(lambda x: f"{x:.1%}" if x is not None else "N/A")
            cdf["actual"] = cdf["actual"].apply(lambda x: f"{x:.1%}" if x is not None else "N/A")
            cdf["error"] = cdf["error"].apply(lambda x: f"{x:.1%}" if x is not None else "N/A")
            st.dataframe(cdf, use_container_width=True, hide_index=True)

        g_cols = st.columns(3)
        with g_cols[0]:
            st.plotly_chart(cohort_comparison_gauge(
                stats["requested_elderly_pct"], stats["actual_elderly_pct"], "Age 60+"),
                use_container_width=True)
        with g_cols[1]:
            if stats["actual_diabetes_pct"] is not None:
                st.plotly_chart(cohort_comparison_gauge(
                    stats["requested_diabetes_pct"], stats["actual_diabetes_pct"], "Diabetes"),
                    use_container_width=True)
        with g_cols[2]:
            if stats["actual_hypertension_pct"] is not None:
                st.plotly_chart(cohort_comparison_gauge(
                    stats["requested_hypertension_pct"], stats["actual_hypertension_pct"], "Hypertension"),
                    use_container_width=True)

        if "trajectory_type" in synth_long.columns:
            st.markdown("### Trajectory Distribution")
            traj_counts = synth_long.groupby("patient_id")["trajectory_type"].first().value_counts()
            st.dataframe(
                pd.DataFrame({"Type": traj_counts.index, "Count": traj_counts.values,
                               "Percentage": (traj_counts.values / traj_counts.values.sum() * 100).round(1)}),
                use_container_width=True, hide_index=True,
            )

        if st.session_state.plausibility_stats:
            ps = st.session_state.plausibility_stats
            if ps["pass"]:
                st.success(f"Plausibility checks passed. {ps['total_checked']} records verified.")
            else:
                st.warning(f"Plausibility: {ps['violations_found']} violations repaired.")
                if ps["repairs"]:
                    st.json(ps["repairs"])

        st.markdown("### Synthetic Profile Preview")
        st.dataframe(cohort.head(20), use_container_width=True)


elif page == "Patient Journeys":
    st.markdown("## Patient Journey Explorer")
    st.divider()

    if not st.session_state.cohort_generated:
        st.warning("Please generate a cohort first.")
    else:
        cohort = st.session_state.synthetic_profiles
        synth_long = st.session_state.synthetic_longitudinal

        col1, col2 = st.columns([1, 2])
        with col1:
            patient_ids = cohort["patient_id"].head(100).tolist()
            selected_patient = st.selectbox("Select Patient", patient_ids)

            if selected_patient:
                p_row = cohort[cohort["patient_id"] == selected_patient].iloc[0]
                st.markdown("#### Demographics")
                st.markdown(f"**Age:** {p_row.get('age', 'N/A')}")
                st.markdown(f"**Gender:** {p_row.get('gender', 'N/A')}")
                st.markdown(f"**BMI:** {p_row.get('bmi', 'N/A')}")
                st.markdown(f"**Diabetes:** {'Yes' if p_row.get('diabetes') == 1 else 'No'}")
                st.markdown(f"**Hypertension:** {'Yes' if p_row.get('hypertension') == 1 else 'No'}")

                p_data = synth_long[synth_long["patient_id"] == selected_patient]
                if "trajectory_type" in p_data.columns and len(p_data) > 0:
                    st.markdown(f"**Trajectory:** {p_data['trajectory_type'].iloc[0].title()}")

            timeline_filter = st.select_slider(
                "Timeline Range (days)",
                options=[7, 14, 30, 60, 90],
                value=int(synth_long["day"].max()),
            )

            show_cohort_avg = st.checkbox("Compare with cohort average", value=True)

        with col2:
            if selected_patient:
                p_data = synth_long[
                    (synth_long["patient_id"] == selected_patient) &
                    (synth_long["day"] <= timeline_filter)
                ]
                full_data = synth_long[synth_long["day"] <= timeline_filter]

                if show_cohort_avg:
                    fig = patient_journey_with_cohort(p_data, selected_patient, full_data)
                else:
                    fig = patient_journey_chart(p_data, selected_patient)
                st.plotly_chart(fig, use_container_width=True)

                st.markdown("#### Journey Statistics")
                metrics = ["systolic_bp", "diastolic_bp", "steps", "medication_adherence", "pain_score"]
                available = [m for m in metrics if m in p_data.columns]
                stat_rows = []
                for m in available:
                    vals = p_data[m]
                    stat_rows.append({
                        "Metric": m.replace("_", " ").title(),
                        "Baseline": round(float(vals.iloc[0]), 2) if len(vals) > 0 else "N/A",
                        "Final": round(float(vals.iloc[-1]), 2) if len(vals) > 0 else "N/A",
                        "Change": round(float(vals.iloc[-1] - vals.iloc[0]), 2) if len(vals) > 1 else "N/A",
                        "Mean": round(float(vals.mean()), 2),
                        "Min": round(float(vals.min()), 2),
                        "Max": round(float(vals.max()), 2),
                    })
                st.dataframe(pd.DataFrame(stat_rows), use_container_width=True, hide_index=True)


elif page == "Validation":
    st.markdown("## Statistical Validation")
    st.markdown("*Comparing synthetic data against original source data for statistical fidelity.*")
    st.divider()

    if not st.session_state.cohort_generated:
        st.warning("Please generate a cohort first.")
    else:
        if st.session_state.validation_profile_results is None:
            with st.spinner("Computing validation metrics..."):
                orig_profiles = st.session_state.profiles_processed
                synth_profiles = st.session_state.synthetic_profiles
                orig_long = st.session_state.longitudinal_processed
                synth_long = st.session_state.synthetic_longitudinal

                profile_results = validate_profiles(orig_profiles, synth_profiles)
                long_results = validate_longitudinal(orig_long, synth_long)
                fidelity = compute_fidelity_summary(profile_results, long_results)
                per_col = compute_per_column_quality(orig_profiles, synth_profiles)
                subgroup = compute_all_subgroup_fidelity(orig_profiles, synth_profiles)

                st.session_state.validation_profile_results = profile_results
                st.session_state.validation_long_results = long_results
                st.session_state.fidelity_summary = fidelity
                st.session_state.per_column_quality = per_col
                st.session_state.subgroup_fidelity = subgroup

        profile_results = st.session_state.validation_profile_results
        long_results = st.session_state.validation_long_results
        fidelity = st.session_state.fidelity_summary

        tab_overview, tab_cols, tab_dist, tab_corr, tab_trend, tab_subgroup = st.tabs(
            ["Overview", "Per-Column Quality", "Distributions", "Correlations",
             "Longitudinal Trends", "Subgroup Fidelity"]
        )

        with tab_overview:
            st.markdown("### Fidelity Summary")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Overall Fidelity Score", f"{fidelity['overall_fidelity']:.2%}")
            with col2:
                st.metric("Components", fidelity["component_count"])
            with col3:
                corr_diff = profile_results.get("correlation", {}).get("mean_absolute_correlation_difference", "N/A")
                st.metric("Correlation Diff", f"{corr_diff:.4f}" if isinstance(corr_diff, float) else corr_diff)

            st.info(fidelity.get("formula", ""))
            st.caption(fidelity.get("interpretation", ""))

            st.markdown("### Numerical Variable Summary")
            for col, data in profile_results.get("numerical", {}).items():
                with st.expander(f"{col}"):
                    s = data["stats"]
                    ks = data["ks_test"]
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.metric("Orig Mean", s["original_mean"])
                        st.metric("Synth Mean", s["synthetic_mean"])
                    with c2:
                        st.metric("Orig Std", s["original_std"])
                        st.metric("Synth Std", s["synthetic_std"])
                    with c3:
                        st.metric("KS Statistic", ks["ks_statistic"])
                        st.metric("Wasserstein", data.get("wasserstein", "N/A"))

            st.markdown("### Categorical Variable Summary")
            for col, data in profile_results.get("categorical", {}).items():
                with st.expander(f"{col} (TVD: {data['total_variation_distance']:.4f})"):
                    st.plotly_chart(
                        categorical_bar_chart(
                            data["categories"], data["original_proportions"],
                            data["synthetic_proportions"], f"{col} Distribution",
                        ), use_container_width=True,
                    )

        with tab_cols:
            st.markdown("### Per-Column Quality Cards")
            per_col = st.session_state.per_column_quality or []
            if per_col:
                df_cols = pd.DataFrame(per_col)
                st.dataframe(df_cols, use_container_width=True, hide_index=True)
            else:
                st.info("No per-column quality data available.")

        with tab_dist:
            st.markdown("### Distribution Comparisons")
            orig = st.session_state.profiles_processed
            synth = st.session_state.synthetic_profiles

            for col in ["age", "bmi"]:
                if col in orig.columns and col in synth.columns:
                    c1, c2 = st.columns(2)
                    with c1:
                        st.plotly_chart(
                            distribution_histogram(orig[col], synth[col], f"Distribution: {col}"),
                            use_container_width=True,
                        )
                    with c2:
                        st.plotly_chart(
                            box_plot_comparison(orig[col], synth[col], f"Box Plot: {col}"),
                            use_container_width=True,
                        )

            st.markdown("### Longitudinal Distributions")
            orig_l = st.session_state.longitudinal_processed
            synth_l = st.session_state.synthetic_longitudinal
            for col in ["systolic_bp", "diastolic_bp", "steps", "medication_adherence", "pain_score"]:
                if col in orig_l.columns and col in synth_l.columns:
                    st.plotly_chart(
                        distribution_histogram(orig_l[col], synth_l[col], f"Distribution: {col}"),
                        use_container_width=True,
                    )

        with tab_corr:
            st.markdown("### Correlation Comparison")
            corr_data = profile_results.get("correlation", {})
            if "error" not in corr_data and "columns" in corr_data:
                c1, c2 = st.columns(2)
                with c1:
                    orig_corr = pd.DataFrame(corr_data["original_correlation"])
                    st.plotly_chart(
                        correlation_heatmap(orig_corr, "Original Correlation"),
                        use_container_width=True,
                    )
                with c2:
                    synth_corr = pd.DataFrame(corr_data["synthetic_correlation"])
                    st.plotly_chart(
                        correlation_heatmap(synth_corr, "Synthetic Correlation"),
                        use_container_width=True,
                    )

                diff_corr = (orig_corr - synth_corr).abs()
                st.plotly_chart(
                    correlation_heatmap(diff_corr, "Absolute Correlation Difference"),
                    use_container_width=True,
                )

        with tab_trend:
            st.markdown("### Longitudinal Trend Comparison")
            for col, data in long_results.get("trend", {}).items():
                st.plotly_chart(
                    trend_line_chart(
                        data["days"], data["original_daily_mean"],
                        data["synthetic_daily_mean"],
                        f"Daily Mean: {col.replace('_', ' ').title()}",
                        col.replace("_", " ").title(),
                    ), use_container_width=True,
                )
                st.caption(f"Trend correlation: {data['trend_correlation']:.4f}")

        with tab_subgroup:
            st.markdown("### Subgroup Fidelity Analysis")
            st.caption("Compares fidelity metrics across demographic subgroups to detect quality disparities.")
            subgroup_results = st.session_state.subgroup_fidelity or []
            if subgroup_results:
                st.plotly_chart(subgroup_fidelity_bar(subgroup_results), use_container_width=True)
                sub_df = pd.DataFrame([{
                    "Subgroup": r.get("label", r.get("subgroup", "")),
                    "Orig N": r["original_n"],
                    "Synth N": r["synthetic_n"],
                    "Fidelity": f"{r['fidelity']:.4f}" if r.get("fidelity") is not None else "N/A",
                    "Warning": r.get("warning", ""),
                } for r in subgroup_results])
                st.dataframe(sub_df, use_container_width=True, hide_index=True)
            else:
                st.info("No subgroup fidelity data available.")


elif page == "Privacy":
    st.markdown("## Privacy Evaluation")
    st.markdown("*Screening synthetic data for potential privacy leakage.*")
    st.divider()

    if not st.session_state.cohort_generated:
        st.warning("Please generate a cohort first.")
    else:
        if st.session_state.privacy_results is None:
            with st.spinner("Running privacy screening..."):
                orig = st.session_state.profiles_processed
                synth = st.session_state.synthetic_profiles
                results = privacy_screening(orig, synth)
                st.session_state.privacy_results = results

        results = st.session_state.privacy_results

        status = results["overall_status"]
        if status == "PASSED":
            st.success(f"Privacy Screening: **{status}**", icon=":material/verified_user:")
        else:
            st.warning(f"Privacy Screening: **{status}**", icon=":material/warning:")

        st.markdown("### Privacy Checks")
        for check in results["checks"]:
            icon = ":material/check_circle:" if check["passed"] else ":material/cancel:"
            if check["passed"]:
                st.success(f"**{check['check']}**: {check['detail']}", icon=icon)
            else:
                st.error(f"**{check['check']}**: {check['detail']}", icon=icon)

        tab_dup, tab_nn, tab_rr = st.tabs(
            ["Exact Duplicates", "Nearest-Neighbor Analysis", "Real-to-Real Baseline"]
        )

        with tab_dup:
            dup = results["exact_duplicates"]
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Exact Duplicates", dup["exact_duplicates"])
            with col2:
                st.metric("Duplicate Rate", f"{dup['duplicate_rate']:.4%}")
            with col3:
                st.metric("Columns Compared", len(dup["columns_compared"]))

        with tab_nn:
            nn = results["nearest_neighbor"]
            if "error" not in nn:
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Mean Distance", f"{nn['mean_distance']:.4f}")
                with col2:
                    st.metric("Median Distance", f"{nn['median_distance']:.4f}")
                with col3:
                    st.metric("Min Distance", f"{nn['min_distance']:.4f}")
                with col4:
                    st.metric("Near Copies", nn["near_copy_count"])

                if "distances" in nn:
                    st.plotly_chart(
                        distance_distribution_chart(nn["distances"], nn["near_copy_threshold"]),
                        use_container_width=True,
                    )

        with tab_rr:
            st.markdown("### Real-to-Real Baseline")
            st.caption("Distance between real records provides context for evaluating synthetic-to-real distances.")
            rr = results.get("real_to_real_baseline", {})
            if "error" not in rr and rr:
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("R-R Mean Distance", f"{rr.get('mean_distance', 0):.4f}")
                with col2:
                    st.metric("R-R Median Distance", f"{rr.get('median_distance', 0):.4f}")
                with col3:
                    st.metric("R-R Min Distance", f"{rr.get('min_distance', 0):.4f}")

            ss = results.get("synth_to_synth", {})
            if "error" not in ss and ss:
                st.markdown("### Synth-to-Synth Distances")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("S-S Mean Distance", f"{ss.get('mean_distance', 0):.4f}")
                with col2:
                    st.metric("S-S Median Distance", f"{ss.get('median_distance', 0):.4f}")
                with col3:
                    st.metric("S-S Min Distance", f"{ss.get('min_distance', 0):.4f}")

        st.divider()
        st.info(results["disclaimer"], icon=":material/info:")


elif page == "Privacy vs Fidelity":
    st.markdown("## Privacy vs Fidelity Explorer")
    st.markdown("*Compare how different privacy modes affect data quality.*")
    st.divider()

    if not st.session_state.model_trained:
        st.warning("Please train a model and generate a cohort first.")
    elif not st.session_state.cohort_generated:
        st.warning("Please generate a cohort first.")
    else:
        st.caption("This generates the same cohort under different privacy settings to show the tradeoff.")

        if st.button("Run Privacy-Fidelity Comparison", type="primary"):
            orig = st.session_state.profiles_processed
            synth = st.session_state.synthetic_profiles
            seed = st.session_state.current_seed

            pf_results = []
            progress = st.progress(0)

            for i, mode in enumerate(["low", "balanced", "high"]):
                progress.progress((i + 1) / 3, text=f"Evaluating {mode} mode...")

                filtered, filter_stats = apply_privacy_mode(synth.copy(), orig, mode=mode, seed=seed)

                profile_results = validate_profiles(orig, filtered)
                fidelity = compute_fidelity_summary(profile_results, {"numerical": {}})

                nn = nearest_neighbor_analysis(orig, filtered, sample_size=min(200, len(filtered)))

                pf_results.append({
                    "mode": mode,
                    "fidelity_score": fidelity["overall_fidelity"],
                    "median_nn_distance": nn.get("median_distance", 0),
                    "exact_duplicates": detect_exact_duplicates(orig, filtered)["exact_duplicates"],
                    "near_copy_count": nn.get("near_copy_count", 0),
                    "correlation_diff": profile_results.get("correlation", {}).get(
                        "mean_absolute_correlation_difference", None),
                    "records_after_filter": len(filtered),
                    "records_rejected": filter_stats.get("records_rejected", 0),
                })

            st.session_state.privacy_fidelity_results = pf_results
            progress.progress(1.0, text="Complete!")

        if st.session_state.privacy_fidelity_results:
            pf_results = st.session_state.privacy_fidelity_results

            st.plotly_chart(privacy_fidelity_scatter(pf_results), use_container_width=True)

            st.markdown("### Detailed Comparison")
            pf_df = pd.DataFrame(pf_results)
            pf_df.columns = [c.replace("_", " ").title() for c in pf_df.columns]
            st.dataframe(pf_df, use_container_width=True, hide_index=True)

            st.divider()
            st.caption(
                "Lower privacy modes preserve more statistical fidelity. "
                "Higher privacy modes increase distance from real records. "
                "Neither setting is inherently better — choose based on your use case."
            )



elif page == "Model Comparison":
    st.markdown("## Model Comparison Lab")
    st.divider()

    if not st.session_state.data_loaded:
        st.warning("Please load a dataset first.")
    else:
        st.caption("Trains and compares multiple synthesizer models on measured metrics.")

        col1, col2 = st.columns(2)
        with col1:
            comp_epochs = st.number_input("CTGAN Epochs", 10, 500, 50, key="comp_epochs")
        with col2:
            comp_samples = st.number_input("Evaluation Samples", 100, 5000, 500, key="comp_samples")

        if st.button("Run Model Comparison", type="primary"):
            profiles = st.session_state.profiles_processed
            train_df = profiles.drop(columns=["patient_id"], errors="ignore")

            with st.spinner("Training and comparing models... This may take a few minutes."):
                results = compare_models(
                    train_df, profiles,
                    model_types=["CTGANSynthesizer", "GaussianCopulaSynthesizer"],
                    n_eval_samples=comp_samples,
                    epochs=comp_epochs,
                    seed=st.session_state.current_seed,
                )
                st.session_state.model_comparison_results = results

        if st.session_state.model_comparison_results:
            results = st.session_state.model_comparison_results
            comp_df = format_comparison_table(results)

            st.markdown("### Comparison Results")
            st.dataframe(comp_df, use_container_width=True, hide_index=True)

            st.plotly_chart(model_comparison_bar(comp_df), use_container_width=True)

            st.markdown("### Select Model for Current Experiment")
            available_models = [k for k, v in results.items() if v.get("training_success")]
            if available_models:
                selected = st.selectbox(
                    "Use model",
                    available_models,
                    format_func=lambda x: x.replace("Synthesizer", ""),
                )
                if st.button("Select This Model"):
                    entry = results[selected]
                    st.session_state.synthesizer = entry["synthesizer"]
                    st.session_state.train_info = entry["train_info"]
                    st.session_state.model_trained = True
                    st.session_state.cohort_generated = False
                    save_synthesizer(entry["synthesizer"])
                    st.success(f"Selected {selected.replace('Synthesizer', '')} as active model.")
                    st.rerun()

            st.divider()
            st.caption(
                "Metrics are measured, not subjective. Choose based on your requirements: "
                "higher fidelity, faster training, or stronger privacy."
            )


elif page == "Experiments":
    st.markdown("## Experiment History")
    st.divider()

    if st.session_state.cohort_generated and st.session_state.fidelity_summary:
        if st.button("Save Current Experiment"):
            cohort_config = st.session_state.cohort_config or {}
            fid = st.session_state.fidelity_summary
            priv = st.session_state.privacy_results
            priv_summary = None
            if priv:
                priv_summary = {
                    "status": priv["overall_status"],
                    "exact_duplicates": priv["exact_duplicates"]["exact_duplicates"],
                    "median_nn_distance": priv["nearest_neighbor"].get("median_distance"),
                }

            exp = save_experiment(
                model=st.session_state.train_info["synth_type"] if st.session_state.train_info else "unknown",
                num_patients=len(st.session_state.synthetic_profiles),
                timeline_days=int(st.session_state.synthetic_longitudinal["day"].max()),
                constraints=cohort_config,
                privacy_mode=st.session_state.privacy_mode,
                seed=st.session_state.current_seed,
                trajectory_dist=st.session_state.trajectory_dist,
                fidelity_summary=fid,
                privacy_summary=priv_summary,
            )
            st.session_state.current_experiment_id = exp["experiment_id"]
            st.success(f"Experiment saved: {exp['experiment_id']}")
    elif st.session_state.cohort_generated:
        st.info("Run validation before saving an experiment.")

    st.markdown("### Past Experiments")
    experiments = list_experiments()
    if experiments:
        exp_rows = []
        for exp in experiments[:20]:
            fid = exp.get("fidelity_summary", {})
            priv = exp.get("privacy_summary", {})
            exp_rows.append({
                "ID": exp["experiment_id"],
                "Timestamp": exp["timestamp"][:19],
                "Model": exp.get("model", "").replace("Synthesizer", ""),
                "Patients": exp.get("num_patients"),
                "Days": exp.get("timeline_days"),
                "Privacy Mode": exp.get("privacy_mode"),
                "Seed": exp.get("seed"),
                "Fidelity": f"{fid.get('overall_fidelity', 0):.2%}" if fid else "N/A",
                "Privacy": priv.get("status", "N/A") if priv else "N/A",
            })
        st.dataframe(pd.DataFrame(exp_rows), use_container_width=True, hide_index=True)

        selected_exp = st.selectbox(
            "View Experiment Details",
            [e["experiment_id"] for e in experiments[:20]],
        )
        if selected_exp:
            exp_data = load_experiment(selected_exp)
            if exp_data:
                st.json(exp_data)
    else:
        st.info("No experiments saved yet. Generate a cohort, run validation, and save.")


elif page == "Export":
    st.markdown("## Export")
    st.divider()

    if not st.session_state.cohort_generated:
        st.warning("Please generate a cohort first.")
    else:
        cohort = st.session_state.synthetic_profiles
        synth_long = st.session_state.synthetic_longitudinal
        n_patients = len(cohort)
        days = int(synth_long["day"].max()) if len(synth_long) > 0 else 0

        st.markdown(f"**Cohort:** {n_patients:,} patients, {days} days, "
                    f"{len(synth_long):,} longitudinal records")

        st.markdown("### Individual Downloads")
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                "Download Profiles CSV",
                export_csv(cohort),
                f"clinsynth_profiles_{n_patients}.csv",
                "text/csv",
            )
            st.download_button(
                "Download Longitudinal CSV",
                export_csv(synth_long),
                f"clinsynth_longitudinal_{n_patients}_{days}d.csv",
                "text/csv",
            )
        with col2:
            st.download_button(
                "Download Profiles JSON",
                export_json(cohort),
                f"clinsynth_profiles_{n_patients}.json",
                "application/json",
            )
            st.download_button(
                "Download Longitudinal JSON",
                export_json(synth_long),
                f"clinsynth_longitudinal_{n_patients}_{days}d.json",
                "application/json",
            )

        st.markdown("### Quality Report")
        src_summary = None
        if st.session_state.profiles_processed is not None:
            src_summary = {
                "n_patients": len(st.session_state.profiles_processed),
                "n_longitudinal": len(st.session_state.longitudinal_processed) if st.session_state.longitudinal_processed is not None else 0,
            }

        quality_report = create_quality_report(
            source_summary=src_summary,
            synthesizer_type=st.session_state.train_info["synth_type"] if st.session_state.train_info else None,
            seed=st.session_state.current_seed,
            cohort_constraints=st.session_state.cohort_config,
            cohort_stats=st.session_state.cohort_stats,
            trajectory_dist=st.session_state.trajectory_dist,
            fidelity_summary=st.session_state.fidelity_summary,
            privacy_metrics=st.session_state.privacy_results,
            privacy_mode=st.session_state.privacy_mode,
            plausibility_stats=st.session_state.plausibility_stats,
        )

        st.download_button(
            "Download Quality Report JSON",
            export_json(quality_report),
            "clinsynth_quality_report.json",
            "application/json",
        )

        st.markdown("### Complete Export (ZIP)")
        zip_bytes = create_export_zip(
            cohort, synth_long,
            validation_report=st.session_state.fidelity_summary,
            privacy_report=st.session_state.privacy_results,
            cohort_config=st.session_state.cohort_config,
            experiment_metadata={
                "seed": st.session_state.current_seed,
                "privacy_mode": st.session_state.privacy_mode,
                "trajectory_dist": st.session_state.trajectory_dist,
                "model": st.session_state.train_info["synth_type"] if st.session_state.train_info else None,
                "experiment_id": st.session_state.current_experiment_id,
            },
            quality_report=quality_report,
            n_patients=n_patients, days=days,
        )
        st.download_button(
            "Download All (ZIP)",
            zip_bytes,
            f"clinsynth_export_{n_patients}_{days}d.zip",
            "application/zip",
        )
