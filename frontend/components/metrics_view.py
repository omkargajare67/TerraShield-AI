"""Results and metrics dashboard component for TerraShield AI."""

from typing import Any, Dict, List
import pandas as pd
import streamlit as st


def render_metrics_cards(analysis_data: Dict[str, Any]) -> None:
    """Render top-level KPI metric cards for demonstration analysis."""
    total = analysis_data.get("total_candidate_parcels", 0)
    eligible = analysis_data.get("eligible_parcels_count", 0)
    excluded = analysis_data.get("excluded_parcels_count", 0)
    highest_score = analysis_data.get("highest_leverage_score")
    top_parcel = analysis_data.get("highest_leverage_parcel_id", "N/A")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Sample Candidate Parcels",
            value=f"{total}",
            help="Total synthetic parcels evaluated in the demonstration dataset.",
        )
    with col2:
        st.metric(
            label="Eligible Sites",
            value=f"{eligible}",
            delta=f"{(eligible/total*100):.0f}% of sample" if total > 0 else None,
            help="Parcels passing statutory reserve and soil capacity checks.",
        )
    with col3:
        st.metric(
            label="Excluded Sites",
            value=f"{excluded}",
            help="Parcels restricted by simulated environmental or physical constraints.",
        )
    with col4:
        score_display = f"{highest_score:.6f}" if highest_score is not None else "N/A"
        st.metric(
            label="Peak Leverage Score (ΔR / N)",
            value=score_display,
            delta=f"Top: {top_parcel}" if top_parcel != "N/A" else None,
            help="Highest modeled risk reduction achieved per planted tree.",
        )


def build_analysis_dataframe(parcels: List[Dict[str, Any]]) -> pd.DataFrame:
    """Convert parcel result objects into a clean Pandas DataFrame for tabular display."""
    rows = []
    for p in parcels:
        leverage = p.get("demo_leverage_score")
        leverage_str = f"{leverage:.6f}" if leverage is not None else "—"
        rank = p.get("rank")
        rank_str = f"#{rank}" if rank is not None else "Excluded"

        rows.append(
            {
                "Priority Rank": rank_str,
                "Parcel ID": p.get("parcel_id", ""),
                "Name": p.get("name", ""),
                "Area (ha)": f"{p.get('area_hectares', 0.0):.1f}",
                "Baseline Risk": f"{p.get('demo_baseline_risk', 0.0):.2f}",
                "Modeled Δ Risk": f"{p.get('demo_delta_risk', 0.0):.2f}",
                "Trees Required (N)": p.get("demo_tree_count", 0),
                "Demo Leverage (ΔR/N)": leverage_str,
                "Status": "Excluded" if p.get("is_excluded") else "Eligible",
                "Exclusion Reason": p.get("exclusion_reason") or "None (Eligible)",
            }
        )

    return pd.DataFrame(rows)


def render_parcels_table(parcels: List[Dict[str, Any]]) -> None:
    """Render the ranked parcel results table and exclusion details."""
    st.subheader("Candidate Parcel Prioritization Table")
    df = build_analysis_dataframe(parcels)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Exclusions detail section
    excluded_parcels = [p for p in parcels if p.get("is_excluded")]
    if excluded_parcels:
        with st.expander("ℹ️ View Exclusion Explanations & Constraints", expanded=False):
            st.markdown(
                "TerraShield AI explicitly records and explains why parcels are excluded "
                "rather than silently omitting candidate parcels from the analysis."
            )
            for p in excluded_parcels:
                st.markdown(
                    f"- **{p.get('parcel_id')} ({p.get('name')})**: "
                    f"`{p.get('exclusion_reason')}`"
                )
