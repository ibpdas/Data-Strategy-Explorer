# ---------------------------------------------------
# Public Sector Data Strategy Explorer (Full Version)
# Includes: Presets + Ten Lenses + Explainer
# ---------------------------------------------------

import os, glob, time, json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# --- Optional fuzzy search
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

# --- CSV file picker
csv_files = sorted([f for f in glob.glob("*.csv") if os.path.isfile(f)])
default_csv = "strategies.csv" if "strategies.csv" in csv_files else (csv_files[0] if csv_files else None)
if not csv_files:
    st.error("No CSV files found in this folder. Please add a CSV (e.g. strategies.csv).")
    st.stop()

with st.sidebar:
    st.subheader("Data source")
    csv_path = st.selectbox("CSV file", options=csv_files, index=csv_files.index(default_csv) if default_csv else 0)
    try:
        mtime = os.path.getmtime(csv_path)
        st.caption(f"📄 **{csv_path}** — last modified: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(mtime))}")
    except Exception:
        st.caption("📄 File time unknown.")
    if st.button("🔄 Reload data"):
        st.cache_data.clear()
        st.experimental_rerun()

@st.cache_data(show_spinner=False)
def load_data(path: str, modified_time: float):
    df = pd.read_csv(path).fillna("")
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    return df

try:
    df = load_data(csv_path, os.path.getmtime(csv_path))
except Exception as e:
    st.error(f"⚠️ {e}")
    st.stop()

# --- Tabs
tab_explore, tab_types, tab_about = st.tabs(["🔎 Explore", "👁️ Strategy Types", "ℹ️ About"])

# ====================================================
# 🔎 EXPLORE TAB
# ====================================================
with tab_explore:
    with st.sidebar:
        st.subheader("Filters")
        years = sorted(y for y in df["year"].dropna().unique())
        if years:
            yr = st.slider("Year range", min_value=int(min(years)), max_value=int(max(years)),
                           value=(int(min(years)), int(max(years))))
        else:
            yr = None
        org_types = sorted([v for v in df["org_type"].unique() if v != ""])
        org_type_sel = st.multiselect("Org type", org_types, default=org_types)
        countries = sorted([v for v in df["country"].unique() if v != ""])
        country_sel = st.multiselect("Country", countries, default=countries)
        scopes = sorted([v for v in df["scope"].unique() if v != ""])
        scope_sel = st.multiselect("Scope", scopes, default=scopes)
        q = st.text_input("Search title/org/summary")

    def fuzzy(df_in, q, limit=400):
        if not q: return df_in
        text = (df_in["title"] + " " + df_in["organisation"] + " " + df_in["summary"]).fillna("")
        if HAS_RAPIDFUZZ:
            matches = process.extract(q, text.tolist(), scorer=fuzz.WRatio, limit=len(text))
            keep = [i for _, s, i in matches if s >= 60]
            return df_in.iloc[keep].head(limit)
        else:
            mask = text.str.contains(q, case=False, na=False)
            return df_in[mask].head(limit)

    fdf = df.copy()
    if yr: fdf = fdf[fdf["year"].between(yr[0], yr[1])]
    if org_type_sel: fdf = fdf[fdf["org_type"].isin(org_type_sel)]
    if country_sel: fdf = fdf[fdf["country"].isin(country_sel)]
    if scope_sel: fdf = fdf[fdf["scope"].isin(scope_sel)]
    fdf = fuzzy(fdf, q)

    st.info(f"{len(fdf)} strategies shown")
    if not fdf.empty:
        col1, col2 = st.columns(2)
        by_year = fdf.groupby("year").size().reset_index(name="count").dropna()
        col1.plotly_chart(px.bar(by_year, x="year", y="count", title="Strategies by year"), use_container_width=True)
        by_country = fdf.groupby("country").size().reset_index(name="count").sort_values("count", ascending=False)
        col2.plotly_chart(px.bar(by_country.head(10), x="country", y="count", title="Top countries"), use_container_width=True)

        st.markdown("### Details")
        for _, r in fdf.iterrows():
            with st.expander(f"📄 {r['title']} — {r['organisation']} ({int(r['year']) if pd.notna(r['year']) else '—'})"):
                st.write(r["summary"])
                meta = st.columns(4)
                meta[0].write(f"**Org type:** {r['org_type']}")
                meta[1].write(f"**Country:** {r['country']}")
                meta[2].write(f"**Scope:** {r['scope']}")
                meta[3].write(f"**Source:** {r['source']}")
                if r["link"]:
                    st.link_button("Open", r["link"])

# ====================================================
# 👁️ STRATEGY TYPES TAB
# ====================================================
with tab_types:
    st.subheader("👁️ The Ten Lenses of Data Strategy")
    st.markdown("Each data strategy balances ten design tensions — from governance and access to innovation and delivery.")

    axes = [
        ("Abstraction Level", "Conceptual", "Logical / Physical"),
        ("Adaptability", "Living", "Fixed"),
        ("Ambition", "Essential", "Transformational"),
        ("Coverage", "Horizontal", "Use-case-based"),
        ("Governance Structure", "Ecosystem / Federated", "Centralised"),
        ("Orientation", "Technology-focused", "Value-focused"),
        ("Motivation", "Compliance-driven", "Innovation-driven"),
        ("Access Philosophy", "Data-democratised", "Controlled access"),
        ("Delivery Mode", "Incremental", "Big Bang"),
        ("Decision Model", "Data-informed", "Data-driven")
    ]
    dims = [a[0] for a in axes]

    # --- Preset profiles
    PRESETS = {
        "Foundational": {"Abstraction Level":100,"Adaptability":100,"Ambition":0,"Coverage":0,"Governance Structure":100,
                         "Orientation":0,"Motivation":0,"Access Philosophy":100,"Delivery Mode":10,"Decision Model":30},
        "Transformational": {"Abstraction Level":20,"Adaptability":10,"Ambition":100,"Coverage":60,"Governance Structure":20,
                             "Orientation":80,"Motivation":100,"Access Philosophy":30,"Delivery Mode":70,"Decision Model":90},
        "Collaborative": {"Abstraction Level":30,"Adaptability":20,"Ambition":50,"Coverage":20,"Governance Structure":10,
                          "Orientation":60,"Motivation":60,"Access Philosophy":20,"Delivery Mode":30,"Decision Model":40},
        "Insight-led": {"Abstraction Level":60,"Adaptability":40,"Ambition":60,"Coverage":40,"Governance Structure":50,
                        "Orientation":70,"Motivation":60,"Access Philosophy":40,"Delivery Mode":40,"Decision Model":70},
        "Citizen-focused": {"Abstraction Level":40,"Adaptability":40,"Ambition":50,"Coverage":40,"Governance Structure":30,
                            "Orientation":100,"Motivation":40,"Access Philosophy":20,"Delivery Mode":40,"Decision Model":40}
    }

    # --- Explainer function
    def render_preset_lens_explainer():
        st.markdown("### 🔗 How the Presets Map to the Ten Lenses")
        st.caption("Presets are not prescriptions; they represent consistent patterns across the Ten Lenses that express distinct data-strategy philosophies.")
        with st.expander("Show full explanation"):
            st.markdown("""
#### 🧱 Foundational — *“Build the plumbing”*
Control, compliance, consistency.
- Logical/Physical, Fixed, Essential, Horizontal, Centralised, Tech-focused, Compliance-driven, Controlled, Incremental, Data-informed

#### 🚀 Transformational — *“Accelerate and innovate”*
Ambition, AI, public value at scale.
- Conceptual, Living, Transformational, Use-case-based, Federated, Value-focused, Innovation-driven, Democratised, Big Bang, Data-driven

#### 🤝 Collaborative — *“Connect the ecosystem”*
Federation, interoperability, shared ownership.
- Semi-conceptual, Living, Moderate, Horizontal, Federated, Value-focused, Balanced, Democratised, Incremental, Data-informed

#### 📊 Insight-led — *“Evidence before action”*
Analytics, learning, performance.
- Logical, Semi-living, Moderate, Targeted, Mixed, Value-focused, Balanced, Semi-open, Incremental, Data-driven

#### 👥 Citizen-focused — *“Ethics, trust, service outcomes”*
Human-centred, transparent, responsible.
- Conceptual, Living, Balanced, Horizontal, Federated, Value-focused, Balanced, Democratised, Incremental, Data-informed
""")

    render_preset_lens_explainer()

    # --- Sliders for self-assessment
    if "_ten_scores" not in st.session_state:
        st.session_state["_ten_scores"] = {d:50 for d in dims}

    cols = st.columns(2)
    for i, (dim, left, right) in enumerate(axes):
        with cols[i % 2]:
            st.session_state["_ten_scores"][dim] = st.slider(
                f"{dim}", 0, 100, st.session_state["_ten_scores"][dim],
                format="%d%%", help=f"{left} ←→ {right}")
            st.caption(f"{left} ←── {st.session_state['_ten_scores'][dim]}% → {right}")

    # --- Radar overlay with presets
    st.markdown("### Compare with Presets")
    chosen = st.multiselect("Overlay presets", list(PRESETS.keys()), default=["Foundational","Transformational"])
    fig = go.Figure()
    user = [st.session_state["_ten_scores"][d]/100 for d in dims]
    fig.add_trace(go.Scatterpolar(r=user+[user[0]], theta=dims+[dims[0]], fill='toself', name="You"))
    for name in chosen:
        p = [PRESETS[name][d]/100 for d in dims]
        fig.add_trace(go.Scatterpolar(r=p+[p[0]], theta=dims+[dims[0]], fill='toself', name=name, opacity=0.5))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0,1])), title="Strategic Fingerprint")
    st.plotly_chart(fig, use_container_width=True)

    st.download_button("Download My Profile (JSON)",
                       data=json.dumps(st.session_state["_ten_scores"], indent=2).encode("utf-8"),
                       file_name="data_strategy_self_assessment.json")

# ====================================================
# ℹ️ ABOUT TAB
# ====================================================
with tab_about:
    st.subheader("About this Explorer")
    st.markdown("""
This open educational tool helps policymakers and analysts understand **how public-sector data strategies differ** —
in ambition, structure, and approach.

- 🔎 **Explore** — browse strategies by country, organisation, and year  
- 👁️ **Strategy Types** — understand the *Ten Lenses* and experiment with archetypes  
- ℹ️ **About** — conceptual foundations, examples, and guidance  
""")

    st.markdown("### 📘 The Ten Lenses Framework")
    st.markdown("""
Each data strategy sits somewhere across these ten design choices:
1. **Abstraction Level:** Conceptual ↔ Logical/Physical  
2. **Adaptability:** Living ↔ Fixed  
3. **Ambition:** Essential ↔ Transformational  
4. **Coverage:** Horizontal ↔ Use-case-based  
5. **Governance:** Federated ↔ Centralised  
6. **Orientation:** Technology-focused ↔ Value-focused  
7. **Motivation:** Compliance-driven ↔ Innovation-driven  
8. **Access:** Democratised ↔ Controlled  
9. **Delivery:** Incremental ↔ Big Bang  
10. **Decision Model:** Data-informed ↔ Data-driven
""")

    st.markdown("""
---
> *“Every data strategy is a balancing act — between governance and growth, structure and experimentation, control and creativity, efficiency and sustailability.”*
""")
