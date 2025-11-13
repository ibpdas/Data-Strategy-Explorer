# lenses_tab.py
import io
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# Six maturity themes (gov framework)
MATURITY_THEMES = [
    ("Uses", "How you get value out of data. Making decisions, evidencing impact, improving services."),
    ("Data", "Technical aspects of managing data as an asset: collection, quality, cataloguing, interoperability."),
    ("Leadership", "How senior and business leaders engage with data: strategy, responsibility, oversight, investment."),
    ("Culture", "Attitudes to data across the organisation: awareness, openness, security, responsibility."),
    ("Tools", "The systems and tools you use to store, share and work with data."),
    ("Skills", "Data and analytical literacy across the organisation, including how people build and maintain those skills."),
]

MATURITY_SCALE = {
    1: "Beginning",
    2: "Emerging",
    3: "Learning",
    4: "Developing",
    5: "Mastering",
}


def maturity_label(avg: float) -> str:
    idx = int(round(avg))
    idx = max(1, min(5, idx))
    return MATURITY_SCALE[idx]


# Ten lenses
AXES = [
    ("Abstraction Level", "Conceptual", "Logical / Physical"),
    ("Adaptability", "Living", "Fixed"),
    ("Ambition", "Essential", "Transformational"),
    ("Coverage", "Horizontal", "Use-case-based"),
    ("Governance Structure", "Ecosystem / Federated", "Centralised"),
    ("Orientation", "Technology-focused", "Value-focused"),
    ("Motivation", "Compliance-driven", "Innovation-driven"),
    ("Access Philosophy", "Data-democratised", "Controlled access"),
    ("Delivery Mode", "Incremental", "Big Bang"),
    ("Decision Model", "Data-informed", "Data-driven"),
]
DIMENSIONS = [a[0] for a in AXES]


def radar_trace(values01, dims, name, opacity=0.6):
    r = list(values01) + [values01[0]]
    t = list(dims) + [dims[0]]
    return go.Scatterpolar(
        r=r, theta=t, name=name, fill="toself", opacity=opacity
    )


def ensure_sessions():
    if "_maturity_scores" not in st.session_state:
        st.session_state["_maturity_scores"] = {k: 3 for k, _ in MATURITY_THEMES}
    if "_current_scores" not in st.session_state:
        st.session_state["_current_scores"] = {d: 50 for d in DIMENSIONS}
    if "_target_scores" not in st.session_state:
        st.session_state["_target_scores"] = {d: 50 for d in DIMENSIONS}
    if "_actions_df" not in st.session_state:
        st.session_state["_actions_df"] = pd.DataFrame(
            columns=["Priority", "Lens", "Direction", "Owner", "Timeline", "Metric", "Status"]
        )


def hint_for_lens(lens_name, maturity_avg, maturity_level_name=None):
    level = maturity_level_name or maturity_label(maturity_avg)
    low = level in ("Beginning", "Emerging")
    mid = level in ("Learning", "Developing")
    high = level == "Mastering"

    if lens_name == "Governance Structure":
        if low:
            return "At Beginning/Emerging, stronger central coordination usually works best before moving to federated models."
        if mid:
            return "At Learning/Developing, you can gradually federate – keep common standards and shared services."
        if high:
            return "At Mastering, federation can unlock autonomy – but guard against fragmentation with shared guardrails."
    if lens_name == "Delivery Mode":
        if low:
            return "Favour incremental delivery to build confidence and reduce risk – avoid a single big-bang change."
        if mid:
            return "Blend incremental delivery with a few larger change packages where foundations are solid."
        if high:
            return "At Mastering, big-bang change is possible – but only with strong programme discipline and clear benefits."
    if lens_name == "Access Philosophy":
        if low:
            return "Start with role-based access to a small number of trusted datasets before opening up more widely."
        if mid:
            return "Broaden access with good catalogue/search – keep tight controls around sensitive domains."
        if high:
            return "Push democratisation further – but make sure data protection and audit trails stay robust."
    if lens_name == "Decision Model":
        if low:
            return "Data-informed decisions with clear human oversight are safest while skills and quality are still building."
        if mid:
            return "Increase automation in low-risk areas – keep humans in the loop for high-impact decisions."
        if high:
            return "Mastering orgs can rely more on data-driven decisions – but need strong monitoring and fallback plans."
    if lens_name == "Motivation":
        if low:
            return "Keep compliance at the core while you pilot innovation in tightly scoped sandboxes."
        if mid:
            return "Balance compliance and innovation – use proof-of-concepts to justify broader change."
        if high:
            return "At Mastering, innovation and compliance can reinforce each other via strong governance by design."
    if lens_name == "Ambition":
        if low:
            return "Focus on essentials – data quality, governance, core platforms – before promising transformational change."
        if mid:
            return "You can mix foundational work with some transformational strands where benefits are clear."
        if high:
            return "Aim for transformational impact – but keep benefits and operating model changes clearly articulated."
    if lens_name == "Coverage":
        if low:
            return "Use a few high-impact use-cases to prove value while you build broader capabilities."
        if mid:
            return "Begin to spread capabilities horizontally to avoid islands of excellence."
        if high:
            return "Horizontal coverage makes sense – but choose a few flagship use-cases to anchor the narrative."
    if lens_name == "Orientation":
        if low:
            return "Platform and tooling investments will dominate early – link them clearly to outcomes."
        if mid:
            return "Balance platform work with visible value – avoid tech for tech’s sake."
        if high:
            return "Keep value firmly in the lead, with platforms treated as enablers rather than ends."
    if lens_name == "Adaptability":
        if low:
            return "Keep a stable core with a small living layer – too much churn can confuse people."
        if mid:
            return "Treat the strategy as living – schedule periodic reviews and small course corrections."
        if high:
            return "Mastering orgs can iterate often – just make sure changes are well-governed and communicated."
    if lens_name == "Abstraction Level":
        if low:
            return "Keep the strategy concise and vision-led, but quickly translate into practical roadmaps and controls."
        if mid:
            return "Balance vision with enough logical detail to guide delivery teams."
        if high:
            return "You can afford a more detailed logical/physical description – but avoid over-specifying too early."

    return ""


def render_lenses() -> None:
    ensure_sessions()
    st.subheader("Lenses")

    st.caption(
        "First self-diagnose your organisation’s data maturity using the six themes from the "
        "Data Maturity Assessment for Government framework, then define where your strategy "
        "should sit on key tensions."
    )

    # --------- Section 1: Maturity ----------
    st.markdown("### 1) Understand maturity (self-diagnose)")

    st.markdown(
        "[Open the Data Maturity Assessment for Government framework]"
        "(https://www.gov.uk/government/publications/data-maturity-assessment-for-government-framework/"
        "data-maturity-assessment-for-government-framework-html)"
    )

    cols_theme = st.columns(3)
    for i, (name, desc) in enumerate(MATURITY_THEMES):
        with cols_theme[i % 3]:
            current_val = st.session_state["_maturity_scores"].get(name, 3)
            st.session_state["_maturity_scores"][name] = st.slider(
                name,
                min_value=1,
                max_value=5,
                value=current_val,
                help=desc,
                format="%d",
                key=f"mat_{name}",
            )
            level_name = MATURITY_SCALE[st.session_state["_maturity_scores"][name]]
            st.caption(f"Level: {level_name}")

    m_scores = st.session_state["_maturity_scores"]
    m_avg = sum(m_scores.values()) / len(m_scores)
    current_level_name = maturity_label(m_avg)

    colA, colB = st.columns(2)

    # Gauge-style bar
    with colA:
        st.metric("Overall maturity (average)", f"{m_avg:.1f} / 5")
        st.markdown(
            f"<span class='badge'>Overall level: {current_level_name}</span>",
            unsafe_allow_html=True,
        )

        gauge_df = pd.DataFrame({"Metric": ["Maturity"], "Score": [m_avg]})
        import plotly.express as px

        fig_bar = px.bar(
            gauge_df,
            x="Metric",
            y="Score",
            title="Overall maturity (1–5)",
            range_y=[0, 5],
        )
        fig_bar.update_yaxes(
            tickvals=[1, 2, 3, 4, 5],
            ticktext=["Beginning", "Emerging", "Learning", "Developing", "Mastering"],
            title=None,
        )
        fig_bar.update_xaxes(title=None, showticklabels=False)
        fig_bar.update_layout(margin=dict(l=80, r=10, t=40, b=20))
        st.plotly_chart(fig_bar, use_container_width=True)

    # Radar for themes
    with colB:
        dims_m = list(m_scores.keys())
        vals01 = [m_scores[d] / 5 for d in dims_m]
        figm = go.Figure()
        figm.add_trace(radar_trace(vals01, dims_m, "Maturity", opacity=0.6))
        figm.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 1],
                    tickvals=[x / 5 for x in [1, 2, 3, 4, 5]],
                    ticktext=["1", "2", "3", "4", "5"],
                )
            ),
            title="Maturity profile across six themes (1–5 scale)",
        )
        st.plotly_chart(figm, use_container_width=True)

    # Download maturity snapshot
    maturity_rows = []
    for name, _ in MATURITY_THEMES:
        score = st.session_state["_maturity_scores"][name]
        maturity_rows.append(
            {"Theme": name, "Score (1–5)": score, "Level": MATURITY_SCALE[score]}
        )
    maturity_rows.append(
        {
            "Theme": "Overall (average)",
            "Score (1–5)": round(m_avg, 2),
            "Level": current_level_name,
        }
    )
    maturity_df = pd.DataFrame(maturity_rows)
    maturity_csv = maturity_df.to_csv(index=False).encode("utf-8")

    st.download_button(
        "⬇️ Download maturity snapshot (CSV)",
        data=maturity_csv,
        file_name="maturity_snapshot.csv",
        mime="text/csv",
    )

    st.markdown("---")

    # --------- Section 2: Tensions ----------
    st.markdown("### 2) Determine strategic tensions (current vs target)")
    st.caption(
        "For each lens, 0 = left label and 100 = right label.\n"
        "Use your maturity baseline above to sense-check how bold your targets should be."
    )

    colL, colR = st.columns(2)

    # Current
    with colL:
        st.markdown("#### Current")
        cols = st.columns(2)
        for i, (dim, left_lbl, right_lbl) in enumerate(AXES):
            with cols[i % 2]:
                current_val = st.session_state["_current_scores"].get(dim, 50)
                st.session_state["_current_scores"][dim] = st.slider(
                    f"{dim} (current)",
                    min_value=0,
                    max_value=100,
                    value=current_val,
                    format="%d%%",
                    help=f"{left_lbl} ←→ {right_lbl}",
                    key=f"cur_{dim}",
                )
                st.caption(
                    f"{left_lbl} ←── {st.session_state['_current_scores'][dim]}% → {right_lbl}"
                )

    # Target + hints
    with colR:
        st.markdown("#### Target")
        cols = st.columns(2)
        for i, (dim, left_lbl, right_lbl) in enumerate(AXES):
            with cols[i % 2]:
                target_val = st.session_state["_target_scores"].get(dim, 50)
                st.session_state["_target_scores"][dim] = st.slider(
                    f"{dim} (target)",
                    min_value=0,
                    max_value=100,
                    value=target_val,
                    format="%d%%",
                    help=f"{left_lbl} ←→ {right_lbl}",
                    key=f"tgt_{dim}",
                )
                st.caption(
                    f"{left_lbl} ←── {st.session_state['_target_scores'][dim]}% → {right_lbl}"
                )

                hint = hint_for_lens(dim, m_avg, current_level_name)
                if hint:
                    st.markdown(
                        f"<div class='info-panel'><strong>Hint:</strong> {hint}</div>",
                        unsafe_allow_html=True,
                    )

    # Twin radar
    dims = [a[0] for a in AXES]
    cur01 = [st.session_state["_current_scores"][d] / 100 for d in dims]
    tgt01 = [st.session_state["_target_scores"][d] / 100 for d in dims]
    fig = go.Figure()
    fig.add_trace(radar_trace(cur01, dims, "Current", opacity=0.6))
    fig.add_trace(radar_trace(tgt01, dims, "Target", opacity=0.5))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
        title="Current vs Target — strategic fingerprints",
    )
    st.plotly_chart(fig, use_container_width=True)
