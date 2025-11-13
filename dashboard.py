
# ---------------------------------------------------
# Public Sector Data Strategy Explorer — GOV-look Theme
# v1.8 – 2025-11-12 14:10 (govlook)
# ---------------------------------------------------
import os, glob, time, io, json, hashlib
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

try:
    from rapidfuzz import fuzz, process
    HAS_RAPIDFUZZ = True
except Exception:
    HAS_RAPIDFUZZ = False

APP_VERSION = "v1.8 – 2025-11-12 14:10 (govlook)"

st.set_page_config(page_title="Public Sector Data Strategy Explorer", layout="wide")

# ---------------- THEME (inspired by UK public-service digital design) ----------------
PRIMARY = "#1d70b8"   # blue
DARK = "#0b0c0c"      # near-black
LIGHT = "#f3f2f1"     # light grey
ACCENT = "#28a197"    # teal

st.markdown(f"""
<style>
/* Header bar */
.header-bar {{
  background:{DARK};
  border-bottom:8px solid {PRIMARY};
  padding:0.75rem 1rem;
  margin:-3rem -3rem 1rem -3rem; /* stretch to edges */
}}
.header-bar h1 {{
  color:white; margin:0; font-size:1.6rem; font-weight:700;
  font-family:"Noto Sans","Helvetica Neue",Helvetica,Arial,sans-serif;
}}
.header-bar .sub {{
  color:#dcdcdc; font-size:0.95rem; margin-top:0.2rem;
}}

/* Body defaults */
body, .block-container {{
  color:{DARK};
  font-family:"Noto Sans","Helvetica Neue",Helvetica,Arial,sans-serif;
}}
a, a:visited {{ color:{PRIMARY}; }}
a:hover {{ color:#003078; }}

/* Cards */
.card {{
  background:white; border:1px solid #e5e5e5; border-radius:8px;
  padding:16px; box-shadow:0 1px 2px rgba(0,0,0,0.03); height:100%;
}}
.card h3 {{ margin-top:0; }}
.card .desc {{ color:#505a5f; font-size:0.95rem; }}

/* Info panel */
.info-panel {{
  background:{LIGHT}; border-left:5px solid {PRIMARY}; padding:1rem; margin:0.5rem 0 1rem 0;
}}

/* Buttons and inputs */
.stButton>button {{
  background:{PRIMARY}; color:white; border-radius:0; border:none; font-weight:600;
}}
.stButton>button:hover {{ background:#003078; }}

/* Footer */
.footer {{
  color:#505a5f; font-size:0.85rem; text-align:center; margin-top:1.2rem;
}}
</style>
<div class="header-bar">
  <h1>Public Sector Data Strategy Explorer</h1>
  <div class="sub">Design better data strategies, faster — balance tensions, align leadership, and plan change.</div>
</div>
""", unsafe_allow_html=True)

# Plotly theme
pio.templates["govlook"] = pio.templates["simple_white"]
pio.templates["govlook"].layout.colorway = [PRIMARY, ACCENT, "#d4351c", "#f47738", "#00703c", "#4c2c92"]
pio.templates["govlook"].layout.font.family = "Noto Sans"
pio.templates["govlook"].layout.font.color = DARK
pio.templates["govlook"].layout.title.font.size = 18
pio.templates.default = "govlook"

# Version tag (small)
st.caption(f"Build: {APP_VERSION}")

REQUIRED = [
    "id","title","organisation","org_type","country","year","scope",
    "link","summary","source","date_added"
]

def file_md5(path:str)->str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def bytes_md5(b: bytes)->str:
    return hashlib.md5(b).hexdigest()

@st.cache_data(show_spinner=False)
def load_data_from_path(path: str, file_hash: str, app_version: str):
    df = pd.read_csv(path).fillna("")
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    return df

@st.cache_data(show_spinner=False)
def load_data_from_bytes(content: bytes, file_hash: str, app_version: str):
    df = pd.read_csv(io.BytesIO(content)).fillna("")
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    return df

# ---------------- Load initial dataframe ----------------
csv_files = sorted([f for f in glob.glob('*.csv') if os.path.isfile(f)])
default_csv = "strategies.csv" if "strategies.csv" in csv_files else (csv_files[0] if csv_files else None)

if "uploaded_bytes" in st.session_state:
    content = st.session_state["uploaded_bytes"]
    df = load_data_from_bytes(content, bytes_md5(content), APP_VERSION)
elif default_csv:
    df = load_data_from_path(default_csv, file_md5(default_csv), APP_VERSION)
else:
    df = pd.DataFrame(columns=REQUIRED)

# ---------------- Model: Ten Lenses ----------------
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
    ("Decision Model", "Data-informed", "Data-driven")
]
DIMENSIONS = [a[0] for a in AXES]

def radar_trace(values01, dims, name, opacity=0.6, fill=True):
    r = list(values01) + [values01[0]]
    t = list(dims) + [dims[0]]
    return go.Scatterpolar(r=r, theta=t, name=name, fill='toself' if fill else None, opacity=opacity)

def ensure_sessions():
    if "_current_scores" not in st.session_state:
        st.session_state["_current_scores"] = {d:50 for d in DIMENSIONS}
    if "_target_scores" not in st.session_state:
        st.session_state["_target_scores"] = {d:50 for d in DIMENSIONS}

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

# ---------------- Explore charts ----------------
def render_explore_charts(fdf: pd.DataFrame):
    st.markdown("## Explore — landscape & patterns")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Strategies", len(fdf))
    k2.metric("Countries", fdf["country"].nunique() if "country" in fdf.columns else 0)
    k3.metric("Org types", fdf["org_type"].nunique() if "org_type" in fdf.columns else 0)
    if "year" in fdf.columns and fdf["year"].notna().any():
        k4.metric("Year span", f"{int(fdf['year'].min())}–{int(fdf['year'].max())}")
    else:
        k4.metric("Year span", "—")
    st.markdown("---")
    c1, c2 = st.columns(2)
    if "year" in fdf.columns and fdf["year"].notna().any():
        fig_hist = px.histogram(fdf[fdf["year"].notna()], x="year", color="scope" if "scope" in fdf.columns else None,
                                nbins=max(10, min(40, fdf["year"].nunique())), title="Strategies by year")
        fig_hist.update_layout(bargap=0.05)
        c1.plotly_chart(fig_hist, use_container_width=True)
    else:
        c1.info("No numeric 'year' values to chart.")
    if "org_type" in fdf.columns and fdf["org_type"].notna().any():
        top_org = fdf.groupby("org_type").size().reset_index(name="count").sort_values("count", ascending=False)
        fig_org = px.bar(top_org, x="org_type", y="count", title="Composition by organisation type")
        fig_org.update_xaxes(title=None, tickangle=20)
        c2.plotly_chart(fig_org, use_container_width=True)
    else:
        c2.info("No 'org_type' values to chart.")
    st.markdown("---")
    c3, c4 = st.columns(2)
    if all(col in fdf.columns for col in ["country","org_type"]):
        if not fdf.empty:
            fig_tree = px.treemap(fdf.assign(_value=1), path=["country","org_type","organisation"], values="_value",
                                  title="Landscape by country → org type → organisation")
            c3.plotly_chart(fig_tree, use_container_width=True)
        else:
            c3.info("No data for treemap.")
    else:
        c3.info("Need 'country' and 'org_type' for treemap.")
    if "country" in fdf.columns and fdf["country"].notna().any():
        by_ctry = fdf.groupby("country").size().reset_index(name="count")
        if not by_ctry.empty:
            fig_map = px.choropleth(by_ctry, locations="country", locationmode="country names", color="count",
                                    title="Global distribution of strategies (by country)", color_continuous_scale="Blues")
            c4.plotly_chart(fig_map, use_container_width=True)
        else:
            c4.info("No country counts to map.")
    else:
        c4.info("No 'country' values to map.")
    st.markdown("---")
    c5, c6 = st.columns(2)
    if all(col in fdf.columns for col in ["country","org_type"]):
        top_ctrys = fdf.groupby("country").size().sort_values(ascending=False).head(12).index.tolist()
        sub = fdf[fdf["country"].isin(top_ctrys)]
        if not sub.empty:
            fig_stack = px.bar(sub, x="country", color="org_type", title="Top countries by strategies (stacked by org type)")
            fig_stack.update_xaxes(title=None)
            c5.plotly_chart(fig_stack, use_container_width=True)
        else:
            c5.info("No data for stacked bar.")
    else:
        c5.info("Need 'country' and 'org_type' for stacked bar.")
    needed = ["year","organisation","title"]
    if all(col in fdf.columns for col in needed) and fdf["year"].notna().any():
        sub = fdf[fdf["year"].notna()].copy()
        fig_scatter = px.scatter(sub, x="year", y="organisation", color="country" if "country" in sub.columns else None,
                                 hover_data=["title","country","scope"] if "scope" in sub.columns else ["title"],
                                 title="Timeline of strategies by organisation")
        c6.plotly_chart(fig_scatter, use_container_width=True)
    else:
        c6.info("Need 'year', 'organisation', and 'title' for timeline scatter.")
    st.markdown("---")
    if "scope" in fdf.columns and fdf["scope"].notna().any():
        by_scope = fdf["scope"].value_counts().reset_index()
        by_scope.columns = ["scope","count"]
        fig_scope = px.pie(by_scope, names="scope", values="count", title="Strategy scope breakdown")
        st.plotly_chart(fig_scope, use_container_width=True)

# ---------------- Tabs ----------------
ensure_sessions()
tab_home, tab_explore, tab_lenses, tab_journey, tab_about = st.tabs(
    ["Home", "Explore", "Lenses", "Journey", "About"]
)

# ====================================================
# 🏠 HOME (introductory, non-clickable cards)
# ====================================================
with tab_home:
    st.markdown(f"""
<div class="info-panel">
<strong>Purpose:</strong> Compare and calibrate public‑sector data strategies. Explore trends, test trade‑offs with the Ten Lenses, and plan your journey from current to target.
</div>
""", unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"""
<div class="card">
<h3>Explore</h3>
<p class="desc">See patterns in real strategies — by year, country, organisation type and scope. Maps, timelines and composition views give fast context.</p>
</div>
""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
<div class="card">
<h3>Lenses</h3>
<p class="desc">Define your <strong>current</strong> vs <strong>target</strong> profile across ten strategic tensions — governance, ambition, access, and more — using clear sliders.</p>
</div>
""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
<div class="card">
<h3>Journey</h3>
<p class="desc">Compare profiles to see direction and magnitude of change. Prioritise the top shifts and turn them into actions and milestones.</p>
</div>
""", unsafe_allow_html=True)

    st.markdown("---")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Rows loaded", len(df))
    k2.metric("Countries", df["country"].nunique() if "country" in df.columns else 0)
    k3.metric("Org types", df["org_type"].nunique() if "org_type" in df.columns else 0)
    k4.metric("Last updated", time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))

# ====================================================
# 🔎 EXPLORE
# ====================================================
with tab_explore:
    with st.expander("Data source & reload", expanded=False):
        uploaded = st.file_uploader("Upload a strategies CSV", type=["csv"], key="uploader_main")
        st.caption("CSV must include required columns.")

        st.markdown("---")
        csv_files_local = sorted([f for f in glob.glob('*.csv') if os.path.isfile(f)])
        if csv_files_local:
            default_csv_local = "strategies.csv" if "strategies.csv" in csv_files_local else csv_files_local[0]
            sel = st.selectbox("Or select a CSV from directory", options=csv_files_local, index=csv_files_local.index(default_csv_local))
            if st.button("Load selected file"):
                st.session_state.pop("uploaded_bytes", None)
                st.cache_data.clear()
                try:
                    df_new = load_data_from_path(sel, file_md5(sel), APP_VERSION)
                    df = df_new
                    st.success(f"Loaded {sel} — {len(df)} rows (MD5 {file_md5(sel)[:12]}…)")
                except Exception as e:
                    st.error(f"⚠️ {e}")
        else:
            st.info("No CSV files found in directory. Upload one above.")

        cols = st.columns(2)
        if cols[0].button("Reload (clear cache)"):
            st.cache_data.clear()
            st.rerun()
        if cols[1].button("Hard refresh (cache + state)"):
            st.cache_data.clear()
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()

        if uploaded is not None:
            content = uploaded.read()
            try:
                df_new = load_data_from_bytes(content, bytes_md5(content), APP_VERSION)
                st.session_state["uploaded_bytes"] = content
                st.cache_data.clear()
                st.success(f"Loaded uploaded CSV — {len(df_new)} rows")
                st.rerun()
            except Exception as e:
                st.error(f"Upload error: {e}")

    with st.sidebar:
        st.subheader("Filters")
        years = sorted(y for y in df["year"].dropna().unique())
        if years:
            yr = st.slider("Year range", int(min(years)), int(max(years)), (int(min(years)), int(max(years))))
        else:
            yr = None
        org_types = sorted([v for v in df["org_type"].unique() if v != ""])
        org_type_sel = st.multiselect("Org type", org_types, default=org_types)
        countries = sorted([v for v in df["country"].unique() if v != ""])
        country_sel = st.multiselect("Country", countries, default=countries)
        scopes = sorted([v for v in df["scope"].unique() if v != ""])
        scope_sel = st.multiselect("Scope", scopes, default=scopes)
        q = st.text_input("Search title/org/summary")

    fdf = df.copy()
    if 'yr' in locals() and yr:
        fdf = fdf[fdf["year"].between(yr[0], yr[1])]
    if 'org_type_sel' in locals() and org_type_sel:
        fdf = fdf[fdf["org_type"].isin(org_type_sel)]
    if 'country_sel' in locals() and country_sel:
        fdf = fdf[fdf["country"].isin(country_sel)]
    if 'scope_sel' in locals() and scope_sel:
        fdf = fdf[fdf["scope"].isin(scope_sel)]
    if 'q' in locals() and q:
        fdf = fuzzy(fdf, q)

    st.info(f"{len(fdf)} strategies shown")
    if not fdf.empty:
        render_explore_charts(fdf)
        st.markdown("### Details")
        for _, r in fdf.iterrows():
            with st.expander(f"{r['title']} — {r['organisation']} ({int(r['year']) if pd.notna(r['year']) else '—'})"):
                st.write(r["summary"] or "_No summary provided._")
                meta = st.columns(4)
                meta[0].write(f"**Org type:** {r['org_type']}")
                meta[1].write(f"**Country:** {r['country']}")
                meta[2].write(f"**Scope:** {r['scope']}")
                meta[3].write(f"**Source:** {r['source']}")
                if r["link"]:
                    st.link_button("Open document", r["link"])

# ====================================================
# 👁️ LENSES (SET PROFILES)
# ====================================================
with tab_lenses:
    st.subheader("Set your profiles across the Ten Lenses")
    st.caption("0 = left label • 100 = right label. Left column = Current, Right = Target.")

    ensure_sessions()
    colL, colR = st.columns(2)

    with colL:
        st.markdown("#### Current profile")
        cols = st.columns(2)
        for i, (dim, left_lbl, right_lbl) in enumerate(AXES):
            with cols[i % 2]:
                st.session_state["_current_scores"][dim] = st.slider(
                    f"{dim} (current)", 0, 100, st.session_state["_current_scores"][dim],
                    format="%d%%", help=f"{left_lbl} ←→ {right_lbl}"
                )
                st.caption(f"{left_lbl} ←── {st.session_state['_current_scores'][dim]}% → {right_lbl}")
        st.download_button("Download current (JSON)",
                           data=json.dumps(st.session_state["_current_scores"], indent=2).encode("utf-8"),
                           file_name="current_profile.json", mime="application/json")

    with colR:
        st.markdown("#### Target profile")
        cols = st.columns(2)
        for i, (dim, left_lbl, right_lbl) in enumerate(AXES):
            with cols[i % 2]:
                st.session_state["_target_scores"][dim] = st.slider(
                    f"{dim} (target)", 0, 100, st.session_state["_target_scores"][dim],
                    format="%d%%", help=f"{left_lbl} ←→ {right_lbl}"
                )
                st.caption(f"{left_lbl} ←── {st.session_state['_target_scores'][dim]}% → {right_lbl}")
        st.download_button("Download target (JSON)",
                           data=json.dumps(st.session_state["_target_scores"], indent=2).encode("utf-8"),
                           file_name="target_profile.json", mime="application/json")

    dims = [a[0] for a in AXES]
    cur01 = [st.session_state["_current_scores"][d]/100 for d in dims]
    tgt01 = [st.session_state["_target_scores"][d]/100 for d in dims]
    fig = go.Figure()
    fig.add_trace(radar_trace(cur01, dims, "Current", opacity=0.6))
    fig.add_trace(radar_trace(tgt01, dims, "Target", opacity=0.5))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0,1])), title="Current vs Target — strategic fingerprints")
    st.plotly_chart(fig, use_container_width=True)

# ====================================================
# 🧭 JOURNEY (COMPARE)
# ====================================================
with tab_journey:
    st.subheader("Journey — compare and prioritise")
    st.caption("Signed change: negative = move toward LEFT label; positive = move toward RIGHT label.")

    dims = [a[0] for a in AXES]
    current = st.session_state.get("_current_scores", {d:50 for d in dims})
    target = st.session_state.get("_target_scores", {d:50 for d in dims})

    rows = []
    for d, left_lbl, right_lbl in AXES:
        diff = target[d] - current[d]
        mag = abs(diff)
        direction = f"→ **{right_lbl}**" if diff>0 else (f"→ **{left_lbl}**" if diff<0 else "—")
        rows.append({"Lens": d, "Current": current[d], "Target": target[d], "Change needed": diff, "Magnitude": mag, "Direction": direction})
    gap_df = pd.DataFrame(rows).sort_values("Magnitude", ascending=False)

    st.markdown("#### Gap by lens (largest first)")
    st.dataframe(gap_df[["Lens","Current","Target","Change needed","Direction"]], use_container_width=True)

    bar = px.bar(gap_df.sort_values("Change needed"), x="Change needed", y="Lens", orientation="h",
                 title="Signed change needed (− move left • + move right)")
    st.plotly_chart(bar, use_container_width=True)

    top = gap_df.head(3)
    if len(top):
        st.markdown("#### Priority shifts (top 3)")
        bullets = []
        for _, row in top.iterrows():
            d = row["Lens"]; diff = row["Change needed"]
            left_lbl = [a[1] for a in AXES if a[0]==d][0]
            right_lbl = [a[2] for a in AXES if a[0]==d][0]
            if diff > 0:
                bullets.append(f"- **{d}**: shift toward **{right_lbl}** (+{int(diff)} pts)")
            elif diff < 0:
                bullets.append(f"- **{d}**: shift toward **{left_lbl}** ({int(diff)} pts)")
        st.markdown("\n".join(bullets))
    else:
        st.info("Current and target are identical — no change required.")

# ====================================================
# ℹ️ ABOUT — your provided content
# ====================================================
with tab_about:

    import streamlit as st
    import plotly.graph_objects as go
    import pandas as pd

    def render_about_tab_full(container, AXES):
        with container:
            st.subheader("About this Explorer")

            # --- Purpose & Audience
            st.markdown("""
### 🎯 Purpose
Help public bodies **design, communicate, and iterate** their data strategy by making
the **key tensions** explicit, comparing **current vs target**, and turning gaps into **prioritised actions**.

The **Public Sector Data Strategy Explorer** helps you understand **how data strategies differ** — in scope, ambition, and governance.  
It combines a searchable dataset of real strategies with a conceptual framework called **The Ten Lenses of Data Strategy**.
""")

            st.markdown("""
### 👥 Who it's for
- **CDOs / Heads of Data** — set direction and align leadership  
- **Policy & Operations leaders** — frame trade-offs and agree priorities  
- **Analysts & Data teams** — translate strategy into delivery  
- **PMOs / Transformation** — track progress and course-correct
""")

            # --- How to use
            st.markdown("""
### 🛠️ How to use this tool
1) **Explore** the landscape of strategies (by year, country, org type) for context.  
2) **Set profiles** using the **Ten Lenses** sliders to define **Current** and **Target** positions.  
3) **Compare** in the **Journey** tab to see directional gaps (left/right) and magnitudes.  
4) **Prioritise** the top shifts and convert them into actions (owners, timelines, measures).  
5) **Re-assess regularly** — treat your strategy as a **living** thing.
""")

            # --- Explanation & Public-Sector Examples (Ten Lenses)
            st.markdown("### 🔍 Explanation and Public-Sector Examples")
            st.markdown("""
| # | Lens | Description | Example |
|---|------|-------------|----------------------|
| **1** | **Abstraction Level** | **Conceptual** strategies define vision and principles; **Logical / Physical** specify architecture and governance. | A national “Data Vision 2030” is conceptual; a departmental “Data Architecture Strategy” is logical/physical. |
| **2** | **Adaptability** | **Living** evolves with new tech and policy; **Fixed** provides a stable framework. | The UK's AI white paper is living; GDPR is fixed. |
| **3** | **Ambition** | **Essential** ensures foundations; **Transformational** drives innovation and automation. | DVLA data sharing are essential; Estonia’s X-Road is transformational. |
| **4** | **Coverage** | **Horizontal** builds maturity across all functions; **Use-case-based** targets exemplar projects. | Government data maturity based maturity improvements vs a use case specific pilot. |
| **5** | **Governance Structure** | **Ecosystem / Federated** encourages collaboration; **Centralised** ensures uniform control. | Federated, domain and strength based vs a centralised decision making approach. |
| **6** | **Orientation** | **Technology-focused** emphasises platforms; **Value-focused** prioritises outcomes and citizens. | A cloud migration roadmap vs a policy-impact dashboard. |
| **7** | **Motivation** | **Compliance-driven** manages risk; **Innovation-driven** creates opportunity. | Privacy by design vs data sharing trusts sandboxes. |
| **8** | **Access Philosophy** | **Democratised** broadens data access; **Controlled** enforces permissions. | Open environmental data portals vs restricted health datasets. |
| **9** | **Delivery Mode** | **Incremental** iterates and tests; **Big Bang** transforms at once. | Local pilots vs national-scale reform. |
| **10** | **Decision Model** | **Data-informed** blends human judgment; **Data-driven** relies on analytics/automation. | Evidence-based policymaking vs automated fraud detection. |
""")

            st.markdown("---")

            # --- FAQs
            st.markdown("""
### ❓ FAQs
**Is one side of a lens better?**  
No — positions reflect context and risk appetite. The goal is **conscious balance**.

**What if Current and Target are far apart?**  
That’s good information: pick **three shifts** to start; avoid Big-Bang unless mandated.

**How do we decide left vs right?**  
Use the **Lenses** tab — each lens includes when to lean left/right and a concrete example.
""")

            # --- Closing tip
            st.markdown("> **“Every data strategy is a balancing act — between governance and growth, structure and experimentation, control and creativity.”**")

    render_about_tab_full(tab_about, AXES)

# ---------------- Footer ----------------
st.markdown("""
---
<div class="footer">
This prototype is created for learning and exploration. It is not an official service.
</div>
""", unsafe_allow_html=True)
