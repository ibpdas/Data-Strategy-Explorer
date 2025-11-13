# journey_tab.py
import pandas as pd
import plotly.express as px
import streamlit as st

from lenses_tab import (
    MATURITY_THEMES,
    MATURITY_SCALE,
    AXES,
    maturity_label,
    ensure_sessions,
)


def conflict_for_target(lens_name, target_score, maturity_avg):
    level = maturity_label(maturity_avg)
    low = level in ("Beginning", "Emerging")
    highish = level in ("Developing", "Mastering")  # treat Learning as middle

    if low:
        if lens_name == "Delivery Mode" and target_score >= 70:
            return "Big-bang at Beginning/Emerging maturity is high risk — consider phased delivery."
        if lens_name == "Governance Structure" and target_score <= 30:
            return "Federated at low maturity can fragment standards — strengthen central controls first."
        if lens_name == "Access Philosophy" and target_score <= 30:
            return "Wide democratisation needs strong basics — start with controlled, role-based access."
        if lens_name == "Decision Model" and target_score >= 70:
            return "Highly data-driven decisions need robust data quality, monitoring and skills."
        if lens_name == "Motivation" and target_score >= 70:
            return "Innovation-first without guardrails can raise risk — keep compliance in the loop."

    if highish:
        if lens_name == "Delivery Mode" and target_score <= 30:
            return "At Developing/Mastering, being too incremental may under-deliver benefits."
        if lens_name == "Governance Structure" and target_score >= 80:
            return "Highly centralised models may slow teams at higher maturity — consider selective federation."
        if lens_name == "Access Philosophy" and target_score >= 80:
            return "Excessive control may limit value realisation — revisit openness where safe."

    return None


def render_journey() -> None:
    ensure_sessions()
    st.subheader("Journey — compare and prioritise")

    st.caption(
        "Signed change: negative = move toward LEFT label; positive = move toward RIGHT label. "
        "Conflicts highlight ambition that may exceed readiness."
    )

    dims = [a[0] for a in AXES]
    current = st.session_state.get("_current_scores", {d: 50 for d in dims})
    target = st.session_state.get("_target_scores", {d: 50 for d in dims})
    m_scores = st.session_state.get("_maturity_scores", {k: 3 for k, _ in MATURITY_THEMES})
    m_avg = sum(m_scores.values()) / len(m_scores)
    level_name = maturity_label(m_avg)

    rows = []
    for d, left_lbl, right_lbl in AXES:
        diff = target[d] - current[d]
        mag = abs(diff)
        direction = (
            f"→ **{right_lbl}**"
            if diff > 0
            else (f"→ **{left_lbl}**" if diff < 0 else "—")
        )
        conflict = conflict_for_target(d, target[d], m_avg)
        rows.append(
            {
                "Lens": d,
                "Current": current[d],
                "Target": target[d],
                "Change needed": diff,
                "Magnitude": mag,
                "Direction": direction,
                "Conflict": bool(conflict),
                "Conflict note": conflict or "",
            }
        )
    gap_df = pd.DataFrame(rows).sort_values(
        ["Conflict", "Magnitude"], ascending=[False, False]
    )

    moves_left = sum(1 for v in gap_df["Change needed"] if v < 0)
    moves_right = sum(1 for v in gap_df["Change needed"] if v > 0)
    zero_moves = sum(1 for v in gap_df["Change needed"] if v == 0)

    st.markdown(
        f"**Summary:** At overall maturity level **{level_name}** (avg {m_avg:.1f}/5), "
        f"you are planning to move **{moves_left} lens(es) toward the left**, "
        f"**{moves_right} toward the right**, and leaving **{zero_moves} unchanged.**"
    )

    st.markdown("#### Gap by lens (conflicts first)")
    st.dataframe(
        gap_df[["Lens", "Current", "Target", "Change needed", "Direction", "Conflict"]],
        use_container_width=True,
    )

    # bar chart
    color_series = gap_df["Conflict"].map({True: "#d4351c", False: "#1d70b8"})
    bar = px.bar(
        gap_df.sort_values("Change needed"),
        x="Change needed",
        y="Lens",
        orientation="h",
        title="Signed change needed (− move left • + move right)",
    )
    bar.data[0].marker.color = color_series
    st.plotly_chart(bar, use_container_width=True)

    TOP_N = 3
    top = gap_df.head(TOP_N)
    if len(top):
        st.markdown(f"#### Priority shifts (top {TOP_N})")
        bullets = []
        for _, row in top.iterrows():
            d = row["Lens"]
            diff = row["Change needed"]
            note = row["Conflict note"]
            left_lbl = [a[1] for a in AXES if a[0] == d][0]
            right_lbl = [a[2] for a in AXES if a[0] == d][0]
            if diff > 0:
                line = f"- **{d}**: shift toward **{right_lbl}** (+{int(diff)} pts)"
            elif diff < 0:
                line = f"- **{d}**: shift toward **{left_lbl}** ({int(diff)} pts)"
            else:
                line = f"- **{d}**: no change"
            if note:
                line += f"  \n  <span class='warn'>⚠️ {note}</span>"
            bullets.append(line)
        st.markdown("\n".join(bullets), unsafe_allow_html=True)

        # Seed actions
        actions_rows = []
        for i, (_, row) in enumerate(top.iterrows(), start=1):
            d = row["Lens"]
            diff = row["Change needed"]
            left_lbl = [a[1] for a in AXES if a[0] == d][0]
            right_lbl = [a[2] for a in AXES if a[0] == d][0]
            if diff > 0:
                direction = f"toward {right_lbl}"
            elif diff < 0:
                direction = f"toward {left_lbl}"
            else:
                direction = "no change"
            actions_rows.append(
                {
                    "Priority": i,
                    "Lens": d,
                    "Direction": direction,
                    "Owner": "",
                    "Timeline": "",
                    "Metric": "",
                    "Status": "",
                }
            )
        st.session_state["_actions_df"] = pd.DataFrame(actions_rows)
    else:
        st.info(
            "Current and target are identical — no change required. "
            "Adjust the sliders in the Lenses tab to see gaps."
        )

    st.markdown(
        "_Want to go deeper on coherence or pacing? See the **Strategy Kernel** and **Three Horizons** in the Resources tab._"
    )
