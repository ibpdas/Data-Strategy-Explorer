# home_tab.py
import time
import pandas as pd
import streamlit as st


def render_home(df: pd.DataFrame, app_version: str) -> None:
    st.markdown(
        """
<div class="info-panel">
<strong>Quick start:</strong> Begin with <strong>Lenses → Maturity</strong> to understand your current readiness,
then set your strategic tensions and review the Journey.
</div>
""",
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            """
<div class="card">
<h3>Explore</h3>
<p class="desc">
See patterns in real strategies — by year, country, organisation type and scope.
Maps, timelines and composition views give fast context.
</p>
</div>
""",
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            """
<div class="card">
<h3>Lenses</h3>
<p class="desc">
<strong>Step 1:</strong> Self-diagnose maturity across six government themes.<br>
<strong>Step 2:</strong> Set <em>Current vs Target</em> positions across Ten Lenses,
with hints and conflict flags.
</p>
</div>
""",
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            """
<div class="card">
<h3>Journey & Actions</h3>
<p class="desc">
Gap analysis, conflicts and priorities — then turn shifts into an
action log with owners, timelines and metrics.
</p>
</div>
""",
            unsafe_allow_html=True,
        )

    st.markdown("---")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Rows loaded", len(df))
    k2.metric("Countries", df["country"].nunique() if "country" in df.columns else 0)
    k3.metric("Org types", df["org_type"].nunique() if "org_type" in df.columns else 0)
    k4.metric("Session time", time.strftime("%H:%M:%S", time.localtime()))

    st.markdown("---")
    st.markdown("### How to use this explorer")
    st.markdown(
        """
1. **Explore** — get a feel for what other organisations are doing (by year, country, org type, scope).  
2. **Assess maturity** — use the six government themes (Uses, Data, Leadership, Culture, Tools, Skills) to agree where you are today.  
3. **Set tensions** — define Current vs Target on the Ten Lenses and see where the biggest shifts are.  
4. **Review the journey** — focus on the 3–5 most important shifts and check for conflicts with your maturity.  
5. **Capture actions** — export a small action log and plug it into your programme plan or OKRs.
"""
    )

    st.caption(f"App version: {app_version}")
