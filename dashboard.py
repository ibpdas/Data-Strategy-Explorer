# ---------------------------
# Public Sector Data Strategy Explorer — Minimal + Strategy Types (Ten Lenses)
# ---------------------------
import os, glob, time, json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Optional fuzzy search
try:
    from rapidfuzz import fuzz, process
    HAS_RAPIDFUZZ = True
except Exception:
    HAS_RAPIDFUZZ = False

REQUIRED = [
    "id","title","organisation","org_type","country","year","scope",
    "link","summary","source","date_added"
]

st.set_page_config(page_title="Public Sector Data Strategy Explorer", layout="wide")
st.title("Public Sector Data Strategy Explorer")
st.caption("Exploring how governments turn data into public value.")

# --- Data source picker (any CSV in current folder)
csv_files = sorted([f for f in glob.glob("*.csv") if os.path.isfile(f)])
default_csv = "strategies.csv" if "strategies.csv" in csv_files else (csv_files[0] if csv_files else None)
if not csv_files:
    st.error("No CSV files found in the app folder. Please add a CSV (e.g., strategies.csv).")
    st.stop()

with st.sidebar:
    st.subheader("Data source")
    csv_path = st.selectbox("CSV file", options=csv_files, index=csv_files.index(default_csv) if default_csv else 0)
    try:
        mtime = os.path.getmtime(csv_path)
        st.caption(f"📄 **{csv_path}** — last modified: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(mtime))}")
    except Exception:
        mtime = 0
        st.caption(f"📄 **{csv_path}** — last modified: unknown")

    if st.button("🔄 Reload data (clear cache)"):
        st.cache_data.clear()
        st.experimental_rerun()

@st.cache_data(show_spinner=False)
def load_data(path: str, modified_time: float):
    if not os.path.exists(path):
        raise FileNotFoundError(f"CSV not found at '{path}'.")
    try:
        df = pd.read_csv(path).fillna("")
    except Exception as e:
        raise RuntimeError(f"Could not read CSV: {e}")
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(f"Missing expected columns: {missing}. Expected columns: {REQUIRED}")
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    return df

try:
    df = load_data(csv_path, os.path.getmtime(csv_path))
except Exception as e:
    st.error(f"⚠️ {e}")
    st.stop()

# ---- Tabs: Explore / Strategy Types / About
tab_explore, tab_types, tab_about = st.tabs(["🔎 Explore", "👁️ Strategy Types", "ℹ️ About"])

# =====================
# 🔎 Explore (metadata-only; no archetypes, no explorer table)
# =====================
with tab_explore:
    # Sidebar filters (metadata only)
    with st.sidebar:
        st.subheader("Filters")
        years = sorted(y for y in df["year"].dropna().unique())
        if years:
            min_y, max_y = int(min(years)), int(max(years))
            year_range = st.slider("Year range", min_value=min_y, max_value=max_y, value=(min_y, max_y), step=1)
        else:
            year_range = None
            st.info("No valid 'year' values — skipping year filter.")

        org_types = sorted([v for v in df["org_type"].unique() if v != ""])
        org_type_sel = st.multiselect("Organisation type", org_types, default=org_types)

        countries = sorted([v for v in df["country"].unique() if v != ""])
        country_sel = st.multiselect("Country", countries, default=countries)

        scopes = sorted([v for v in df["scope"].unique() if v != ""])
        scope_sel = st.multiselect("Scope", scopes, default=scopes)

        q = st.text_input("Search title, organisation, summary", "", help="Fuzzy search on title/organisation/summary.")
        st.markdown("---")
        debug = st.checkbox("Show debug info")

    def fuzzy_filter(df_in, query, limit=500):
        if not query:
            return df_in
        q = query.strip()
        hay = (df_in["title"] + " " + df_in["organisation"] + " " + df_in["summary"]).fillna("")
        if HAS_RAPIDFUZZ:
            matches = process.extract(q, hay.tolist(), scorer=fuzz.WRatio, limit=len(hay))
            keep_idx = [i for _, score, i in matches if score >= 60]
            if not keep_idx: return df_in.iloc[0:0]
            return df_in.iloc[keep_idx].head(limit)
        else:
            mask = hay.str.contains(q, case=False, na=False)
            return df_in[mask].head(limit)

    # Apply filters
    fdf = df.copy()
    if year_range:
        fdf = fdf[(fdf["year"].between(year_range[0], year_range[1], inclusive="both")) | (fdf["year"].isna())]
    if org_type_sel:
        fdf = fdf[fdf["org_type"].isin(org_type_sel)]
    if country_sel:
        fdf = fdf[fdf["country"].isin(country_sel)]
    if scope_sel:
        fdf = fdf[fdf["scope"].isin(scope_sel)]
    fdf = fuzzy_filter(fdf, q)

    # Debug info
    st.info(f"Loaded **{len(df)}** rows from **{csv_path}**. After filters: **{len(fdf)}** rows.")
    if debug:
        with st.expander("🔎 Debug"):
            st.write("Working directory:", os.getcwd())
            st.write("Files:", os.listdir("."))
            st.dataframe(fdf.head(), use_container_width=True)

    if fdf.empty:
        st.warning("No results match your filters/search. Try clearing a filter or the search box.")
        st.stop()

    # KPIs
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Strategies", len(fdf))
    c2.metric("Org types", fdf["org_type"].nunique())
    c3.metric("Countries", fdf["country"].nunique())
    yr_min = int(fdf["year"].min()) if pd.notna(fdf["year"].min()) else "—"
    yr_max = int(fdf["year"].max()) if pd.notna(fdf["year"].max()) else "—"
    c4.metric("Year span", f"{yr_min}–{yr_max}")

    # Visuals
    st.subheader("Visuals")
    row1_left, row1_right = st.columns(2)

    if fdf["year"].notna().any():
        by_year = fdf[fdf["year"].notna()].groupby("year").size().reset_index(name="count").sort_values("year")
        row1_left.plotly_chart(px.bar(by_year, x="year", y="count", title="Strategies by year"), use_container_width=True)
    else:
        row1_left.info("No numeric 'year' values to chart.")

    by_org = fdf.groupby("organisation").size().reset_index(name="count").sort_values("count", ascending=False).head(15)
    row1_right.plotly_chart(px.bar(by_org, x="organisation", y="count", title="Top organisations (by count)"), use_container_width=True)

    st.markdown("---")

    # Download filtered CSV
    st.download_button(
        "Download filtered CSV",
        data=fdf.to_csv(index=False).encode("utf-8"),
        file_name="strategies_filtered.csv",
        mime="text/csv"
    )

    # Details
    st.markdown("### Details")
    for _, r in fdf.sort_values("year", ascending=False).iterrows():
        ytxt = int(r["year"]) if pd.notna(r["year"]) else "—"
        with st.expander(f"📄 {r['title']} — {r['organisation']} ({ytxt})"):
            st.write(r["summary"] or "_No summary yet._")
            meta = st.columns(4)
            meta[0].write(f"**Org type:** {r['org_type']}")
            meta[1].write(f"**Country:** {r['country']}")
            meta[2].write(f"**Scope:** {r['scope']}")
            meta[3].write(f"**Source:** {r['source']}")
            if r["link"]:
                st.link_button("Open document", r["link"], use_container_width=False)

# =====================
# 👁️ Strategy Types — Ten Lenses (interactive)
# =====================
with tab_types:
    st.subheader("👁️ The Ten Lenses of Data Strategy")
    st.markdown("Each data strategy balances these ten trade‑offs. Use the sliders to **self‑assess** where your organisation sits today.")

    axes = [
        ("Abstraction Level", "Conceptual", "Logical / Physical"),
        ("Adaptability", "Living", "Fixed"),
        ("Ambition", "Essential", "Transformational"),
        ("Coverage", "Horizontal", "Breadth / Use‑case‑based"),
        ("Governance Structure", "Ecosystem / Federated", "Centralised"),
        ("Orientation", "Technology‑focused", "Value‑focused"),
        ("Motivation", "Compliance‑driven", "Innovation‑driven"),
        ("Access Philosophy", "Data‑democratised", "Controlled access"),
        ("Delivery Mode", "Incremental", "Big Bang"),
        ("Decision Model", "Data‑informed", "Data‑driven")
    ]

    st.markdown("#### Self‑assessment sliders")
    cols = st.columns(2)
    scores = {}
    for i, (dim, left, right) in enumerate(axes):
        with cols[i % 2]:
            scores[dim] = st.slider(f"{dim}", 0, 100, 50, format="%d%%", help=f"{left} ←→ {right}")
            st.caption(f"{left} ←── {scores[dim]}% → {right}")

    # Radar chart (0‑100) — normalised to 0..1 for the polar radius
    dims = [a[0] for a in axes]
    r_vals = [scores[d] / 100.0 for d in dims]
    fig_radar = go.Figure()
    fig_radar.add_trace(go.Scatterpolar(r=r_vals + [r_vals[0]], theta=dims + [dims[0]], fill='toself', name="Your profile"))
    fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0,1])), showlegend=False, title="Your strategic fingerprint")
    st.plotly_chart(fig_radar, use_container_width=True)

    # Bars per dimension for quick reading
    st.markdown("#### Per‑dimension balance")
    per_dim = pd.DataFrame({
        "Dimension": dims,
        "Score (0=left, 100=right)": [scores[d] for d in dims]
    })
    st.plotly_chart(px.bar(per_dim, x="Dimension", y="Score (0=left, 100=right)", title="Balance by lens").update_xaxes(tickangle=30), use_container_width=True)

    # Download self‑assessment JSON
    st.download_button(
        "Download my self‑assessment (JSON)",
        data=json.dumps(scores, indent=2).encode("utf-8"),
        file_name="strategy_ten_lenses_self_assessment.json",
        mime="application/json"
    )

    st.info("Tip: Use this tab in workshops. Ask teams to slide independently, then compare profiles to surface strategic tensions and priorities.")

# =====================
# ℹ️ About
# =====================
with tab_about:
    st.subheader("About this Explorer")
    st.markdown("""
The **Public Sector Data Strategy Explorer** brings together real-world strategies and frameworks, helping governments understand **how data strategy design varies across contexts**.  

It provides two main experiences:
- 🔎 **Explore** — browse and filter public-sector data strategies, view publication trends, and open source documents.  
- 👁️ **Strategy Types (Ten Lenses)** — an educational tool for exploring the **trade-offs** that shape how data strategies are designed.  
""")

    st.markdown("### 👁️ The Ten Lenses of Data Strategy")
    st.markdown("""
Each public-sector data strategy sits somewhere along these **ten dimensions of design**.  
There’s no “right” end — each choice represents a trade-off between stability and innovation, control and creativity, or vision and execution.
""")

    st.markdown("""
| # | Lens | Description | Public-Sector Example |
|---|------|--------------|----------------------|
| **1** | **Abstraction Level** | **Conceptual** focuses on high-level vision and principles, while **Logical / Physical** dives into data models, architecture, and governance. | A national “Data Vision 2030” is conceptual; a departmental “Data Architecture Blueprint” is logical/physical. |
| **2** | **Adaptability** | **Living** strategies evolve with emerging tech and policies; **Fixed** strategies define a stable long-term framework. | The UK’s AI White Paper is “living,” regularly updated; GDPR is “fixed.” |
| **3** | **Ambition** | **Essential** ensures foundations like quality and standards; **Transformational** drives innovation, AI, and automation. | NHS’s data governance reforms are essential; Estonia’s X-Road platform is transformational. |
| **4** | **Coverage** | **Horizontal** builds maturity across all functions; **Use-case-based** focuses on quick wins or exemplar projects. | A cross-government “data maturity” programme is horizontal; a transport analytics pilot is use-case-based. |
| **5** | **Governance Structure** | **Ecosystem / Federated** promotes shared ownership; **Centralised** enforces strong control. | The UK’s federated CDO network is ecosystem-based; Singapore’s Smart Nation is more centralised. |
| **6** | **Orientation** | **Technology-focused** emphasises data platforms and infrastructure; **Value-focused** prioritises policy outcomes and public value. | A cloud migration roadmap is technology-focused; an outcomes framework for service improvement is value-focused. |
| **7** | **Motivation** | **Compliance-driven** ensures legality, ethics, and security; **Innovation-driven** seeks to unlock new opportunities. | GDPR compliance is compliance-driven; data-sharing sandboxes are innovation-driven. |
| **8** | **Access Philosophy** | **Data-democratised** broadens access across teams; **Controlled access** enforces permissions and data minimisation. | Open-data portals embody democratisation; sensitive health datasets remain controlled. |
| **9** | **Delivery Mode** | **Incremental** builds iteratively through pilots; **Big Bang** aims for rapid, large-scale change. | Local councils testing data standards = incremental; national data strategy launches = big bang. |
| **10** | **Decision Model** | **Data-informed** blends evidence with judgement; **Data-driven** relies heavily on automated insight. | A policymaker weighing analytics with public feedback is data-informed; an automated fraud detection system is data-driven. |
""")

    st.markdown("""
---
### 💡 How to Use the Explorer
- Use the **Explore tab** to see real strategies by country, year, and organisation type.  
- Use the **Ten Lenses tab** in workshops or training to discuss how your organisation balances each dimension.  
- Compare results, export your self-assessment JSON, and evolve your strategy consciously.  

> “Every data strategy is a balancing act — between governance and growth, structure and experimentation, control and creativity.”
""")

