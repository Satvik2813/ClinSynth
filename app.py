"""ClinSynth — Privacy-Preserving Synthetic Patient Data Platform.

Main Streamlit application.
"""
import sys
import time
from pathlib import Path

import streamlit as st
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.data.loader import load_demo_dataset, load_uploaded_csv, detect_dataset_type, map_schema, get_data_summary
from src.preprocessing.pipeline import preprocess_profiles, preprocess_longitudinal, get_quality_report
from src.synthesis.synthesizer import train_synthesizer, save_synthesizer, load_synthesizer, generate_samples, build_metadata
from src.cohort.builder import build_cohort
from src.temporal.generator import TemporalEngine
from src.validation.engine import validate_profiles, validate_longitudinal, compute_fidelity_summary
from src.privacy.evaluator import privacy_screening
from src.visualization.charts import (
    distribution_histogram, categorical_bar_chart, correlation_heatmap,
    trend_line_chart, distance_distribution_chart, box_plot_comparison,
    patient_journey_chart, cohort_comparison_gauge,
)
from src.utils.export import export_csv, export_json, create_export_zip
from src.utils.config import DEFAULT_COHORT, MODELS_DIR, RANDOM_SEED


st.set_page_config(
    page_title="ClinSynth",
    page_icon=":hospital:",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem; font-weight: 700; color: #1e3a5f;
        margin-bottom: 0;
    }
    .sub-header {
        font-size: 1rem; color: #64748b; margin-top: -0.5rem;
    }
    .tagline {
        font-size: 0.85rem; color: #94a3b8; font-style: italic;
    }
    .metric-card {
        background: #f8fafc; border-radius: 8px; padding: 1rem;
        border-left: 4px solid #2563eb; margin-bottom: 0.5rem;
    }
    .status-pass { color: #10b981; font-weight: 600; }
    .status-fail { color: #ef4444; font-weight: 600; }
    .status-pending { color: #f59e0b; font-weight: 600; }
</style>
""", unsafe_allow_html=True)


def init_session_state():
    defaults = {
        "profiles": None, "longitudinal": None,
        "profiles_processed": None, "longitudinal_processed": None,
        "synthesizer": None, "train_info": None,
        "synthetic_profiles": None, "synthetic_longitudinal": None,
        "cohort_stats": None,
        "validation_profile_results": None, "validation_long_results": None,
        "fidelity_summary": None, "privacy_results": None,
        "data_loaded": False, "model_trained": False, "cohort_generated": False,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


init_session_state()


# --- Sidebar ---
with st.sidebar:
    st.markdown('<p class="main-header">ClinSynth</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Privacy-Preserving Synthetic Patient Data Platform</p>', unsafe_allow_html=True)
    st.markdown('<p class="tagline">Realistic Data. Zero Patient Exposure.</p>', unsafe_allow_html=True)
    st.divider()

    st.markdown("**Status**")
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
         "Validation", "Privacy", "Export"],
        label_visibility="collapsed",
    )


# ======================= PAGES =======================

if page == "Overview":
    st.markdown("## ClinSynth")
    st.markdown("### Privacy-Preserving Synthetic Patient Data Platform")
    st.markdown("*Realistic Data. Zero Patient Exposure.*")
    st.divider()

    st.markdown("""
    ClinSynth generates realistic synthetic patient cohorts for healthcare research and
    digital-health testing without exposing real patient records.

    **Workflow:**
    1. **Load** a patient dataset (bundled demo or upload CSV)
    2. **Inspect** data quality and distributions
    3. **Train** a synthetic data generator (CTGAN or Gaussian Copula)
    4. **Define** a custom cohort with demographic constraints
    5. **Generate** synthetic patient profiles and longitudinal health journeys
    6. **Validate** synthetic data against the original statistically
    7. **Screen** for privacy leakage risk
    8. **Export** as CSV, JSON, or ZIP
    """)

    st.info(
        "CTGAN is not a pretrained healthcare model. It is fitted on your selected source dataset "
        "and learns statistical relationships from that data. Generated records are synthetic approximations, "
        "not clinically validated data.",
        icon=":material/info:"
    )

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Profile Fields", "6")
    with col2:
        st.metric("Longitudinal Fields", "7")
    with col3:
        st.metric("Synth Methods", "2")
    with col4:
        st.metric("Privacy Checks", "3")


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
            st.markdown("### Longitudinal Summary Statistics")
            st.dataframe(longitudinal.describe(), use_container_width=True)
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
                status.info(f"Training {synth_type}... This may take a few minutes.")
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

                status.success("Model trained and saved successfully!")
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
        st.markdown("Configure your synthetic cohort parameters.")

        col1, col2 = st.columns(2)
        with col1:
            num_patients = st.number_input(
                "Number of Synthetic Patients", 100, 50000, DEFAULT_COHORT["num_patients"], step=100,
            )
            elderly_pct = st.slider(
                "Target Age 60+ (%)", 0, 100, int(DEFAULT_COHORT["elderly_pct"] * 100),
            ) / 100
            diabetes_pct = st.slider(
                "Target Diabetes (%)", 0, 100, int(DEFAULT_COHORT["diabetes_pct"] * 100),
            ) / 100
        with col2:
            hypertension_pct = st.slider(
                "Target Hypertension (%)", 0, 100, int(DEFAULT_COHORT["hypertension_pct"] * 100),
            ) / 100
            timeline_days = st.select_slider(
                "Longitudinal Timeline (days)",
                options=[7, 14, 30, 60, 90], value=30,
            )

        st.markdown("#### Cohort Preview")
        preview_data = {
            "Parameter": ["Patients", "Age 60+", "Diabetes", "Hypertension", "Timeline"],
            "Value": [
                f"{num_patients:,}", f"{elderly_pct:.0%}",
                f"{diabetes_pct:.0%}", f"{hypertension_pct:.0%}", f"{timeline_days} days",
            ],
        }
        st.dataframe(pd.DataFrame(preview_data), use_container_width=True, hide_index=True)

        if st.button("Generate Synthetic Cohort", type="primary"):
            with st.spinner("Generating synthetic profiles..."):
                raw = generate_samples(st.session_state.synthesizer, num_patients * 5)
                cohort, stats = build_cohort(
                    raw, num_patients=num_patients,
                    elderly_pct=elderly_pct, diabetes_pct=diabetes_pct,
                    hypertension_pct=hypertension_pct,
                )

            with st.spinner("Generating longitudinal health journeys..."):
                engine = TemporalEngine(seed=RANDOM_SEED)
                if st.session_state.profiles_processed is not None and st.session_state.longitudinal_processed is not None:
                    engine.learn_from_data(
                        st.session_state.profiles_processed,
                        st.session_state.longitudinal_processed,
                    )
                synth_long = engine.generate_journeys(cohort, days=timeline_days)

            st.session_state.synthetic_profiles = cohort
            st.session_state.synthetic_longitudinal = synth_long
            st.session_state.cohort_stats = stats
            st.session_state.cohort_generated = True

            st.session_state.validation_profile_results = None
            st.session_state.validation_long_results = None
            st.session_state.fidelity_summary = None
            st.session_state.privacy_results = None

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

        st.markdown("### Cohort Statistics")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Patients", f"{stats['total_patients']:,}")
            st.metric("Longitudinal Records", f"{len(synth_long):,}")
        with col2:
            st.metric("Timeline", f"{synth_long['day'].max()} days")

        st.markdown("### Cohort Constraint Comparison")
        constraint_data = {
            "Constraint": ["Age 60+", "Diabetes", "Hypertension"],
            "Requested": [
                f"{stats['requested_elderly_pct']:.1%}",
                f"{stats['requested_diabetes_pct']:.1%}",
                f"{stats['requested_hypertension_pct']:.1%}",
            ],
            "Actual": [
                f"{stats['actual_elderly_pct']:.1%}",
                f"{stats['actual_diabetes_pct']:.1%}" if stats['actual_diabetes_pct'] is not None else "N/A",
                f"{stats['actual_hypertension_pct']:.1%}" if stats['actual_hypertension_pct'] is not None else "N/A",
            ],
        }
        st.dataframe(pd.DataFrame(constraint_data), use_container_width=True, hide_index=True)

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

        st.markdown("### Synthetic Profile Preview")
        st.dataframe(cohort.head(20), use_container_width=True)

        st.markdown("### Patient Journey Explorer")
        patient_ids = cohort["patient_id"].head(50).tolist()
        selected_patient = st.selectbox("Select Patient", patient_ids)
        if selected_patient:
            fig = patient_journey_chart(synth_long, selected_patient)
            st.plotly_chart(fig, use_container_width=True)


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

                st.session_state.validation_profile_results = profile_results
                st.session_state.validation_long_results = long_results
                st.session_state.fidelity_summary = fidelity

        profile_results = st.session_state.validation_profile_results
        long_results = st.session_state.validation_long_results
        fidelity = st.session_state.fidelity_summary

        tab_overview, tab_dist, tab_corr, tab_trend = st.tabs(
            ["Overview", "Distributions", "Correlations", "Longitudinal Trends"]
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
                cols = corr_data["columns"]
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

        st.markdown("### Exact Duplicate Analysis")
        dup = results["exact_duplicates"]
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Exact Duplicates", dup["exact_duplicates"])
        with col2:
            st.metric("Duplicate Rate", f"{dup['duplicate_rate']:.4%}")
        with col3:
            st.metric("Columns Compared", len(dup["columns_compared"]))

        st.markdown("### Nearest-Neighbor Distance Analysis")
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

        st.divider()
        st.info(results["disclaimer"], icon=":material/info:")


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

        st.markdown("### Validation Report")
        if st.session_state.fidelity_summary:
            report = {
                "fidelity_summary": st.session_state.fidelity_summary,
                "profile_validation": st.session_state.validation_profile_results,
            }
            long_report = st.session_state.validation_long_results or {}
            safe_long = {}
            for k, v in long_report.items():
                safe_long[k] = {}
                for kk, vv in v.items():
                    if isinstance(vv, dict):
                        safe_long[k][kk] = {kkk: vvv for kkk, vvv in vv.items()
                                             if not isinstance(vvv, (list,)) or len(vvv) < 100}
                    else:
                        safe_long[k][kk] = vv
            report["longitudinal_validation"] = safe_long
            st.download_button(
                "Download Validation Report JSON",
                export_json(report),
                "clinsynth_validation_report.json",
                "application/json",
            )

        st.markdown("### Complete Export (ZIP)")
        zip_bytes = create_export_zip(
            cohort, synth_long,
            validation_report=st.session_state.fidelity_summary,
            privacy_report=st.session_state.privacy_results,
            n_patients=n_patients, days=days,
        )
        st.download_button(
            "Download All (ZIP)",
            zip_bytes,
            f"clinsynth_export_{n_patients}_{days}d.zip",
            "application/zip",
        )
