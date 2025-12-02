# ---------------------------------------------------
# Think Studio – Data Strategy Accelerator
# ---------------------------------------------------
import os
import glob
import io
import time
import hashlib
import base64

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

# --- Optional: semantic embeddings (AI search) ---
try:
    from sentence_transformers import SentenceTransformer

    HAS_EMBED = True
except Exception:
    HAS_EMBED = False
    SentenceTransformer = None

APP_VERSION = "Think Studio ALPHA v3.2 - 2025-11-16"

# ---------------- PAGE CONFIG & THEME ----------------
st.set_page_config(
    page_title="Think Studio – Data Strategy Accelerator",
    layout="wide",
)

PRIMARY = "#1d70b8"  # GOV-style blue
DARK = "#0b0c0c"     # near-black
LIGHT = "#f3f2f1"    # light grey
ACCENT = "#28a197"   # teal
RED = "#d4351c"

st.markdown(
    f"""
<style>
/* Header bar */
.header-bar {{
  background:{DARK};
  border-bottom:8px solid {PRIMARY};
  padding:0.75rem 1rem;
  margin:-3rem -3rem 1rem -3rem;
}}
.header-bar h1 {{
  color:white; margin:0; font-size:1.6rem; font-weight:700;
  font-family:"Noto Sans","Helvetica Neue",Helvetica,Arial,sans-serif;
}}
.header-bar .sub {{
  color:#dcdcdc; font-size:0.95rem; margin-top:0.2rem;
}}

/* Body */
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

/* Info / warning panels */
.info-panel {{
  background:{LIGHT}; border-left:5px solid {PRIMARY};
  padding:1rem; margin:0.5rem 0 1rem 0;
}}
.warn {{
  background:#fef7f7; border-left:5px solid {RED};
  padding:0.6rem 0.8rem; margin:0.3rem 0; color:#6b0f0f;
}}
.badge {{
  display:inline-block; padding:2px 8px; border-radius:999px;
  background:{PRIMARY}15; color:{PRIMARY}; font-size:0.8rem; margin-right:6px;
}}
.kv {{
  display:inline-block; padding:2px 6px; border-radius:4px;
  background:{LIGHT}; border:1px solid #e5e5e5; margin-right:6px;
}}

/* Buttons */
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
  <h1>Think Studio</h1>
  <div class="sub">Data Strategy Accelerator for public sector leaders</div>
</div>
""",
    unsafe_allow_html=True,
)

# Plotly theme
pio.templates["govlook"] = pio.templates["simple_white"]
pio.templates["govlook"].layout.colorway = [
    PRIMARY,
    ACCENT,
    "#d4351c",
    "#f47738",
    "#00703c",
    "#4c2c92",
]
pio.templates["govlook"].layout.font.family = "Noto Sans"
pio.templates["govlook"].layout.font.color = DARK
pio.templates["govlook"].layout.title.font.size = 18
pio.templates.default = "govlook"

st.caption(f"Build: {APP_VERSION}")

# ---------------- DATA LOADING ----------------
REQUIRED = [
    "id",
    "title",
    "organisation",
    "org_type",
    "country",
    "year",
    "scope",
    "link",
    "summary",
    "source",
    "date_added",
]


def file_md5(path: str) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def bytes_md5(b: bytes) -> str:
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


# --- Load initial CSV (default or uploaded) ---
csv_files = sorted([f for f in glob.glob("*.csv") if os.path.isfile(f)])
default_csv = (
    "strategies.csv"
    if "strategies.csv" in csv_files
    else (csv_files[0] if csv_files else None)
)

if "uploaded_bytes" in st.session_state:
    content = st.session_state["uploaded_bytes"]
    df = load_data_from_bytes(content, bytes_md5(content), APP_VERSION)
elif default_csv:
    df = load_data_from_path(default_csv, file_md5(default_csv), APP_VERSION)
else:
    df = pd.DataFrame(columns=REQUIRED)

# ---------------- LENSES & MATURITY ----------------

# Government data maturity themes (CDDO)
MATURITY_THEMES = [
    (
        "Uses",
        "How you get value out of data. Making decisions, evidencing impact, improving services.",
    ),
    (
        "Data",
        "Technical aspects of managing data as an asset: collection, quality, cataloguing, interoperability.",
    ),
    (
        "Leadership",
        "How senior and business leaders engage with data: strategy, responsibility, oversight, investment.",
    ),
    (
        "Culture",
        "Attitudes to data across the organisation: awareness, openness, security, responsibility.",
    ),
    (
        "Tools",
        "The systems and tools you use to store, share and work with data.",
    ),
    (
        "Skills",
        "Data and analytical literacy across the organisation, including how people build and maintain those skills.",
    ),
]

# Official government levels 1–5
MATURITY_SCALE = {
    1: "Beginning",
    2: "Emerging",
    3: "Learning",
    4: "Developing",
    5: "Mastering",
}


def maturity_label(avg: float) -> str:
    """
    Map the average (1–5) to the nearest official maturity level.
    """
    idx = int(round(avg))
    idx = max(1, min(5, idx))
    return MATURITY_SCALE[idx]


# Ten Lenses
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


def radar_trace(values01, dims, name, opacity=0.6, fill=True):
    r = list(values01) + [values01[0]]
    t = list(dims) + [dims[0]]
    return go.Scatterpolar(
        r=r, theta=t, name=name, fill="toself" if fill else None, opacity=opacity
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
    if "_biz_priority" not in st.session_state:
        st.session_state["_biz_priority"] = {
            "outcomes": [],
            "questions": "",
            "capabilities": [],
        }


# ---------------- SEARCH HELPERS ----------------
def simple_search(df_in: pd.DataFrame, query: str) -> pd.DataFrame:
    """
    Simple case-insensitive search over key text columns.
    """
    if not query:
        return df_in

    text_cols = [c for c in ["title", "organisation", "summary", "scope"] if c in df_in.columns]
    if not text_cols:
        return df_in

    text = df_in[text_cols[0]].astype(str)
    for col in text_cols[1:]:
        text = text + " " + df_in[col].astype(str)

    mask = text.str.contains(query, case=False, na=False)
    return df_in[mask]


@st.cache_resource(show_spinner=False)
def get_embedding_model():
    if not HAS_EMBED:
        return None
    return SentenceTransformer("all-MiniLM-L6-v2")


@st.cache_data(show_spinner=False)
def compute_strategy_embeddings(df_in: pd.DataFrame, app_version: str):
    if not HAS_EMBED:
        return None
    model = get_embedding_model()
    if model is None:
        return None

    text_cols = [c for c in ["title", "organisation", "summary", "scope", "country"] if c in df_in.columns]
    if not text_cols:
        return None

    texts = df_in[text_cols[0]].astype(str)
    for col in text_cols[1:]:
        texts = texts + " " + df_in[col].astype(str)

    embeddings = model.encode(
        texts.tolist(),
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    emb_df = pd.DataFrame(embeddings, index=df_in.index)
    return emb_df


def semantic_search(fdf: pd.DataFrame, emb_df: pd.DataFrame, query: str, top_k: int = 100) -> pd.DataFrame:
    """
    Semantic search using pre-computed embeddings.
    Respects current filtered subset fdf by aligning on index.
    """
    if not query or emb_df is None or fdf.empty:
        return fdf

    model = get_embedding_model()
    if model is None:
        return fdf

    q_emb = model.encode([query], convert_to_numpy=True, normalize_embeddings=True)[0]
    sub_emb = emb_df.loc[fdf.index].values
    sims = sub_emb @ q_emb

    order = np.argsort(-sims)
    order = order[: min(top_k, len(order))]
    result = fdf.iloc[order].copy()
    result["similarity"] = sims[order]
    return result


emb_df = compute_strategy_embeddings(df, APP_VERSION)

# ---------------- HINTS & CONFLICTS ----------------
def hint_for_lens(lens_name, maturity_avg, maturity_level_name=None):
    """
    Give contextual hints based on the organisation's overall maturity level.
    Uses government levels: Beginning, Emerging, Learning, Developing, Mastering.
    """
    level = maturity_level_name or maturity_label(maturity_avg)
    low = level in ("Beginning", "Emerging")
    mid = level in ("Learning", "Developing")
    high = level == "Mastering"

    if lens_name == "Governance Structure":
        if low:
            return "At Beginning or Emerging, stronger central coordination usually works best before moving to federated models."
        if mid:
            return "At Learning or Developing, you can gradually federate while keeping common standards and shared services."
        if high:
            return "At Mastering, federation can unlock autonomy, but guard against fragmentation with shared guardrails."
    if lens_name == "Delivery Mode":
        if low:
            return "Favour incremental delivery to build confidence and reduce risk; avoid a single big bang change."
        if mid:
            return "Blend incremental delivery with a few larger change packages where foundations are solid."
        if high:
            return "At Mastering, big bang change is possible, but only with strong programme discipline and clear benefits."
    if lens_name == "Access Philosophy":
        if low:
            return "Start with role based access to a small number of trusted datasets before opening up more widely."
        if mid:
            return "Broaden access with good catalogue and search, and keep tight controls around sensitive domains."
        if high:
            return "Push democratisation further, but make sure data protection and audit trails stay robust."
    if lens_name == "Decision Model":
        if low:
            return "Data informed decisions with clear human oversight are safest while skills and quality are still building."
        if mid:
            return "Increase automation in low risk areas and keep humans in the loop for high impact decisions."
        if high:
            return "Mastering organisations can rely more on data driven decisions, with strong monitoring and fallback plans."
    if lens_name == "Motivation":
        if low:
            return "Keep compliance at the core while you pilot innovation in tightly scoped sandboxes."
        if mid:
            return "Balance compliance and innovation; use proof of concepts to justify broader change."
        if high:
            return "At Mastering, innovation and compliance can reinforce each other through governance by design."
    if lens_name == "Ambition":
        if low:
            return "Focus on essentials such as data quality, governance and core platforms before promising transformational change."
        if mid:
            return "You can mix foundational work with some transformational strands where benefits are clear."
        if high:
            return "Aim for transformational impact but keep benefits and operating model changes clearly articulated."
    if lens_name == "Coverage":
        if low:
            return "Use a few high impact use cases to prove value while you build broader capabilities."
        if mid:
            return "Begin to spread capabilities horizontally to avoid islands of excellence."
        if high:
            return "Horizontal coverage makes sense, but choose a few flagship use cases to anchor the narrative."
    if lens_name == "Orientation":
        if low:
            return "Platform and tooling investments will dominate early; link them clearly to outcomes."
        if mid:
            return "Balance platform work with visible value; avoid technology for its own sake."
        if high:
            return "Keep value firmly in the lead, with platforms treated as enablers rather than ends."
    if lens_name == "Adaptability":
        if low:
            return "Keep a stable core with a small living layer; too much churn can confuse people."
        if mid:
            return "Treat the strategy as living and schedule periodic reviews and small course corrections."
        if high:
            return "Mastering organisations can iterate often, as long as changes are well governed and communicated."
    if lens_name == "Abstraction Level":
        if low:
            return "Keep the strategy concise and vision led, but quickly translate it into practical roadmaps and controls."
        if mid:
            return "Balance vision with enough logical detail to guide delivery teams."
        if high:
            return "You can afford a more detailed logical or physical description, but avoid over specifying too early."

    return ""


def conflict_for_target(lens_name, target_score, maturity_avg):
    """
    Flag misalignments between maturity and ambitious targets.
    target_score is 0–100 toward right label.
    """
    level = maturity_label(maturity_avg)
    low = level in ("Beginning", "Emerging")
    highish = level in ("Developing", "Mastering")  # treat Learning as middle

    # Low maturity: warn if target is very ambitious or risky
    if low:
        if lens_name == "Delivery Mode" and target_score >= 70:
            return "Big bang delivery at Beginning or Emerging maturity is high risk. Consider phased delivery."
        if lens_name == "Governance Structure" and target_score <= 30:
            return "Highly federated models at low maturity can fragment standards. Strengthen central controls first."
        if lens_name == "Access Philosophy" and target_score <= 30:
            return "Wide democratisation needs strong basics. Start with controlled, role based access."
        if lens_name == "Decision Model" and target_score >= 70:
            return "Highly data driven decisions need robust data quality, monitoring and skills."
        if lens_name == "Motivation" and target_score >= 70:
            return "Innovation first without guardrails can raise risk. Keep compliance in the loop."

    # Higher maturity: warn if overly conservative
    if highish:
        if lens_name == "Delivery Mode" and target_score <= 30:
            return "At Developing or Mastering, being too incremental may under deliver benefits."
        if lens_name == "Governance Structure" and target_score >= 80:
            return "Highly centralised models may slow teams at higher maturity. Consider selective federation."
        if lens_name == "Access Philosophy" and target_score >= 80:
            return "Excessive control may limit value realisation. Revisit openness where safe."

    return None


# ---------------- EXPLORE CHARTS ----------------
def render_explore_charts(fdf: pd.DataFrame):
    st.markdown("## Explore the strategic landscape")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Strategies", len(fdf))
    k2.metric("Countries", fdf["country"].nunique() if "country" in fdf.columns else 0)
    k3.metric("Org types", fdf["org_type"].nunique() if "org_type" in fdf.columns else 0)
    if "year" in fdf.columns and fdf["year"].notna().any():
        k4.metric("Year span", f"{int(fdf['year'].min())}-{int(fdf['year'].max())}")
    else:
        k4.metric("Year span", "n a")

    st.markdown("---")
    c1, c2 = st.columns(2)

    if "year" in fdf.columns and fdf["year"].notna().any():
        fig_hist = px.histogram(
            fdf[fdf["year"].notna()],
            x="year",
            color="scope" if "scope" in fdf.columns else None,
            nbins=max(10, min(40, fdf["year"].nunique())),
            title="Strategies by year",
        )
        fig_hist.update_layout(bargap=0.05)
        c1.plotly_chart(fig_hist, use_container_width=True)
    else:
        c1.info("No numeric 'year' values to chart. Check your CSV or filters.")

    if "org_type" in fdf.columns and fdf["org_type"].notna().any():
        top_org = (
            fdf.groupby("org_type")
            .size()
            .reset_index(name="count")
            .sort_values("count", ascending=False)
        )
        fig_org = px.bar(
            top_org,
            x="org_type",
            y="count",
            title="Composition by organisation type",
        )
        fig_org.update_xaxes(title=None, tickangle=20)
        c2.plotly_chart(fig_org, use_container_width=True)
    else:
        c2.info("No 'org_type' values to chart.")

    st.markdown("---")
    c3, c4 = st.columns(2)

    if all(col in fdf.columns for col in ["country", "org_type"]):
        if not fdf.empty:
            fig_tree = px.treemap(
                fdf.assign(_value=1),
                path=["country", "org_type", "organisation"],
                values="_value",
                title="Landscape by country, organisation type and organisation",
            )
            c3.plotly_chart(fig_tree, use_container_width=True)
        else:
            c3.info("No data for treemap.")
    else:
        c3.info("Need 'country' and 'org_type' columns for treemap.")

    if "country" in fdf.columns and fdf["country"].notna().any():
        by_ctry = fdf.groupby("country").size().reset_index(name="count")
        if not by_ctry.empty:
            fig_map = px.choropleth(
                by_ctry,
                locations="country",
                locationmode="country names",
                color="count",
                title="Global distribution of strategies (by country)",
                color_continuous_scale="Blues",
            )
            c4.plotly_chart(fig_map, use_container_width=True)
        else:
            c4.info("No country counts to map.")
    else:
        c4.info("No 'country' values to map.")

    st.markdown("---")
    c5, c6 = st.columns(2)
    if all(col in fdf.columns for col in ["country", "org_type"]):
        top_ctrys = (
            fdf.groupby("country").size().sort_values(ascending=False).head(12).index.tolist()
        )
        sub = fdf[fdf["country"].isin(top_ctrys)]
        if not sub.empty:
            fig_stack = px.bar(
                sub,
                x="country",
                color="org_type",
                title="Top countries by strategies (stacked by organisation type)",
            )
            fig_stack.update_xaxes(title=None)
            c5.plotly_chart(fig_stack, use_container_width=True)
        else:
            c5.info("No data for stacked bar.")
    else:
        c5.info("Need 'country' and 'org_type' for stacked bar.")

    needed = ["year", "organisation", "title"]
    if all(col in fdf.columns for col in needed) and fdf["year"].notna().any():
        sub = fdf[fdf["year"].notna()].copy()
        fig_scatter = px.scatter(
            sub,
            x="year",
            y="organisation",
            color="country" if "country" in sub.columns else None,
            hover_data=["title", "country", "scope"]
            if "scope" in sub.columns
            else ["title"],
            title="Timeline of strategies by organisation",
        )
        c6.plotly_chart(fig_scatter, use_container_width=True)
    else:
        c6.info("Need 'year', 'organisation' and 'title' columns for timeline.")

    st.markdown("---")
    if "scope" in fdf.columns and fdf["scope"].notna().any():
        by_scope = fdf["scope"].value_counts().reset_index()
        by_scope.columns = ["scope", "count"]
        fig_scope = px.pie(
            by_scope, names="scope", values="count", title="Strategy scope breakdown"
        )
        st.plotly_chart(fig_scope, use_container_width=True)


# ---------------- TABS SETUP ----------------
ensure_sessions()
tab_home, tab_explore, tab_diagnose, tab_shift, tab_actions, tab_research, tab_about = st.tabs(
    ["Home", "Explore", "Diagnose", "Shift", "Actions", "Research", "About"]
)

# ====================================================
# 🏠 HOME
# ====================================================
with tab_home:
    # Hero / intro
    st.markdown(
        """
<div class="info-panel">
  <strong>What Think Studio is:</strong> A micro lab for public sector data leaders
  to make <strong>business priorities</strong>, <strong>data maturity</strong> and
  <strong>strategic tensions</strong> explicit. It will not write your strategy for you,
  but it will help you have a better conversation about it.
</div>
""",
        unsafe_allow_html=True,
    )

    # Three core building blocks
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            """
<div class="card">
  <h3>Explore</h3>
  <p class="desc">
    Browse real public sector data, digital, analytics and AI strategies by
    <strong>year</strong>, <strong>country</strong>, <strong>organisation type</strong>
    and <strong>scope</strong>. Use this for context and inspiration, not as a complete
    global catalogue.
  </p>
</div>
""",
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            """
<div class="card">
  <h3>Diagnose and Shift</h3>
  <p class="desc">
    Use <strong>Diagnose</strong> to connect <strong>business priorities</strong> with your
    current <strong>data maturity</strong> and <strong>strategic tensions</strong>.
    Then use the <strong>Shift</strong> tab to see where you are trying to move, and which
    shifts deserve most attention.
  </p>
</div>
""",
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            """
<div class="card">
  <h3>Actions and Research</h3>
  <p class="desc">
    Turn your top shifts into a simple <strong>action log</strong> with impact estimates,
    and use the <strong>Research</strong> tab to connect your insights to wider strategy,
    skills and case study material.
  </p>
</div>
""",
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # Quick dataset snapshot
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Strategies loaded", len(df))
    k2.metric("Countries", df["country"].nunique() if "country" in df.columns else 0)
    k3.metric("Org types", df["org_type"].nunique() if "org_type" in df.columns else 0)
    k4.metric("Last updated", time.strftime("%Y-%m-%d", time.localtime()))

    st.markdown("---")

    # When it is / is not useful
    st.markdown("### When Think Studio is useful")
    st.markdown(
        """
Use Think Studio when you want to:

- **Prepare or refine a data strategy** and sense check whether your ambitions match your current maturity and business priorities.
- **Run a workshop** with leaders or delivery teams (for example 60 to 90 minutes) to surface assumptions and disagreements.
- **Turn vague direction into clearer shifts** and identify three to five practical changes in governance, delivery or access.
- **Support learning and development** using the Diagnose, Shift and Research tabs as structured prompts for discussion.
"""
    )

    st.markdown("### What Think Studio is not designed for")
    st.markdown(
        """
Think Studio is not intended to be:

- A formal or official assessment of organisational maturity.
- A complete and always up to date catalogue of all public sector data strategies.
- An automatic strategy generator or replacement for professional judgement.
- A benchmarking tool that compares your scores against other named organisations.

Treat the outputs as structured prompts for conversation and planning, not as a single source of truth.
"""
    )

    st.markdown("---")

    # Suggested journey
    st.markdown("### Suggested journey")
    st.markdown(
        """
1. **Explore** strategies by year, country, organisation type and scope to build a view of the landscape.  
2. **Diagnose** by clarifying business priorities, assessing data maturity and setting positions on key strategic tensions.  
3. **Shift** by reviewing the scale and direction of change you are aiming for and highlighting the most important shifts.  
4. **Actions** by turning those shifts into a small set of projects with indicative impact and ownership.  
5. **Research** to deepen your thinking and skills as a data strategist.
"""
    )

    st.markdown("---")

    # Community, openness, data / licensing
    st.markdown("### Community, openness and data use")
    st.markdown(
        """
- Think Studio is a **community learning project**, created and maintained as a facilitation and reflection tool for data strategists.  
- It does **not collect personal data** about users beyond what your hosting platform may collect by default.  
- All calculations are **visible and transparent**; there are no hidden scoring models or black box rankings.  
- Strategies are **curated from official, publicly available sources** (for example government publications),
  typically under the **Open Government Licence (OGL)** or equivalent open licences.  
- The underlying code is **open source**, so you can inspect, reuse or adapt it for your own context.
"""
    )

    # How people can contribute
    st.markdown("### How you can contribute")
    st.markdown(
        """
If you find Think Studio useful, you can help improve it by:

- Sharing links to **new or missing public data strategies**.
- Flagging **errors in the metadata** such as country, year or organisation type.
- Suggesting **better examples** for the strategic lenses or maturity themes.
- Sharing how you have used the tool in **workshops, training or strategy work**.

For now, the easiest way to contribute is via GitHub:

[Contribute a strategy or suggestion](https://github.com/ibpdas/Public-Sector-Data-Strategies/issues/new?assignees=&labels=enhancement%2Cresource&template=resource_submission.md&title=%F0%9F%92%A1+Strategy+Submission)
"""
    )

    # Personal note / provenance
    st.markdown(
        """
<small>
<strong>Think Studio – Data Strategy Accelerator</strong> was created by <strong>Bandhu Das</strong>, a public sector data strategist,
as a side project for learning, facilitation and skills development.  
Connect on LinkedIn: <a href="https://www.linkedin.com/in/bandhu-das" target="_blank">linkedin.com/in/bandhu-das</a>.  
</small>
""",
        unsafe_allow_html=True,
    )

# ====================================================
# 🔎 EXPLORE
# ====================================================
with tab_explore:
    with st.expander("Manage data (upload or reload)", expanded=False):
        uploaded = st.file_uploader(
            "Upload a strategies CSV", type=["csv"], key="uploader_main"
        )
        st.caption("CSV must include required columns such as id, title and organisation.")
        st.markdown("---")

        csv_files_local = sorted(
            [f for f in glob.glob("*.csv") if os.path.isfile(f)]
        )
        if csv_files_local:
            default_csv_local = (
                "strategies.csv"
                if "strategies.csv" in csv_files_local
                else csv_files_local[0]
            )
            sel = st.selectbox(
                "Or select a CSV from directory",
                options=csv_files_local,
                index=csv_files_local.index(default_csv_local),
            )
            if st.button("Load selected file"):
                st.session_state.pop("uploaded_bytes", None)
                st.cache_data.clear()
                try:
                    df_new = load_data_from_path(
                        sel, file_md5(sel), APP_VERSION
                    )
                    df = df_new
                    st.success(
                        f"Loaded {sel} ({len(df)} rows, MD5 {file_md5(sel)[:12]}...)"
                    )
                except Exception as e:
                    st.error(f"Error loading file: {e}")
        else:
            st.info("No CSV files found in directory. Upload one above.")

        cols_reload = st.columns(2)
        if cols_reload[0].button("Reload (clear cache)"):
            st.cache_data.clear()
            st.rerun()
        if cols_reload[1].button("Hard refresh (cache and state)"):
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
                st.success(f"Loaded uploaded CSV ({len(df_new)} rows)")
                st.rerun()
            except Exception as e:
                st.error(f"Upload error: {e}")

    with st.sidebar:
        st.subheader("Filters for Explore tab")
        years = sorted(y for y in df["year"].dropna().unique())
        if years:
            yr = st.slider(
                "Year range",
                int(min(years)),
                int(max(years)),
                (int(min(years)), int(max(years))),
            )
        else:
            yr = None

        org_types = sorted([v for v in df["org_type"].unique() if v != ""])
        org_type_sel = st.multiselect("Organisation type", org_types, default=org_types)

        countries = sorted([v for v in df["country"].unique() if v != ""])
        country_sel = st.multiselect("Country", countries, default=countries)

        scopes = sorted([v for v in df["scope"].unique() if v != ""])
        scope_sel = st.multiselect("Scope", scopes, default=scopes)

        q = st.text_input(
            "Search strategies (keyword or AI)",
            placeholder="For example 'Defra', 'data ethics', 'agriculture'",
        )

        search_mode = st.radio(
            "Search mode",
            options=["Keyword", "AI semantic"],
            index=1 if emb_df is not None else 0,
            help="Keyword search looks for exact text matches. AI semantic search finds similar strategies by meaning and may be imperfect.",
        )
        if emb_df is None and search_mode == "AI semantic":
            st.caption("Install 'sentence-transformers' to enable AI semantic search.")

    fdf = df.copy()
    if yr:
        fdf = fdf[fdf["year"].between(yr[0], yr[1])]
    if org_type_sel:
        fdf = fdf[fdf["org_type"].isin(org_type_sel)]
    if country_sel:
        fdf = fdf[fdf["country"].isin(country_sel)]
    if scope_sel:
        fdf = fdf[fdf["scope"].isin(scope_sel)]

    if q:
        if search_mode == "AI semantic" and emb_df is not None:
            st.caption("Semantic search active (AI based similarity).")
            fdf = semantic_search(fdf, emb_df, q, top_k=100)
        else:
            fdf = simple_search(fdf, q)
        st.caption(f"{len(fdf)} strategies match your query.")

    if fdf.empty:
        st.warning(
            f"No strategies match the current filters and search term: **{q or 'none'}**. "
            "Try broadening filters or removing the search text."
        )
    else:
        render_explore_charts(fdf)
        st.markdown("### Strategy details")
        for _, r in fdf.iterrows():
            year_str = int(r["year"]) if pd.notna(r["year"]) else "n a"
            label = f"{r['title']} — {r['organisation']} ({year_str})"
            if "similarity" in fdf.columns:
                label += f"  [similarity {r.get('similarity', 0):.2f}]"
            with st.expander(label):
                st.write(r["summary"] or "_No summary provided._")
                meta = st.columns(4)
                meta[0].write(f"**Organisation type:** {r['org_type']}")
                meta[1].write(f"**Country:** {r['country']}")
                meta[2].write(f"**Scope:** {r['scope']}")
                meta[3].write(f"**Source:** {r['source']}")
                if r["link"]:
                    st.link_button("Open document", r["link"])

# ====================================================
# 🔍 DIAGNOSE (Business priorities, Maturity, Tensions)
# ====================================================
with tab_diagnose:
    ensure_sessions()
    st.subheader("Diagnose")

    st.caption(
        "Use this page to connect your organisation's business priorities, "
        "current data maturity and strategic tensions."
    )

    # ------- Section 0: Business priorities -------
    st.markdown("### 1) Business priorities")

    st.caption(
        "Start with the outcomes and questions that matter most. This helps anchor the strategy "
        "in real business needs rather than generic best practice."
    )

    outcomes_options = [
        "Improve service performance",
        "Reduce operating costs",
        "Deliver statutory or regulatory outcomes",
        "Strengthen compliance and assurance",
        "Improve user or citizen experience",
        "Enable evidence based policy making",
        "Support operational resilience",
        "Improve cross organisation collaboration",
        "Unlock responsible AI and automation opportunities",
    ]
    capability_options = [
        "Trusted operational data",
        "Joined up customer or case view",
        "Real time metrics and monitoring",
        "Performance dashboards and reporting",
        "Predictive analytics or modelling",
        "Common data standards and catalogues",
        "Modern data platforms and architecture",
        "Skilled and confident data users",
    ]

    biz_state = st.session_state["_biz_priority"]

    selected_outcomes = st.multiselect(
        "Which outcomes are most important over the next one to three years",
        options=outcomes_options,
        default=biz_state.get("outcomes", []),
    )
    st.session_state["_biz_priority"]["outcomes"] = selected_outcomes

    key_questions = st.text_area(
        "What business questions do leaders keep asking that depend on better data",
        value=biz_state.get("questions", ""),
        placeholder="For example: Where are the biggest bottlenecks in our service, which users are most at risk, which interventions work best and for whom.",
    )
    st.session_state["_biz_priority"]["questions"] = key_questions

    selected_capabilities = st.multiselect(
        "Which capabilities does your data strategy need to enable",
        options=capability_options,
        default=biz_state.get("capabilities", []),
    )
    st.session_state["_biz_priority"]["capabilities"] = selected_capabilities

    st.markdown(
        """
_You can refer back to these priorities in the Shift and Actions tabs when you decide which projects to focus on._
"""
    )

    st.markdown("---")

    # ------- Section 1: Maturity -------
    st.markdown("### 2) Data maturity (self diagnosis)")

    st.caption(
        "Use the six themes in the Data Maturity Assessment for Government framework "
        "(Central Digital and Data Office) to rate where you are today."
    )
    st.markdown(
        "[Open the framework in a new tab]"
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

    # Overall maturity summary + gauge bar + radar
    m_scores = st.session_state["_maturity_scores"]
    m_avg = sum(m_scores.values()) / len(m_scores) if m_scores else 0
    current_level_name = maturity_label(m_avg)

    colA, colB = st.columns([1, 1])

    # LEFT: Gauge-style bar (0–5)
    with colA:
        st.metric("Overall maturity (average)", f"{m_avg:.1f} / 5")
        st.markdown(
            f"<span class='badge'>Level: {current_level_name}</span>",
            unsafe_allow_html=True,
        )

        gauge_df = pd.DataFrame({"Metric": ["Maturity"], "Score": [m_avg]})

        fig_bar = px.bar(
            gauge_df,
            x="Metric",
            y="Score",
            title="Overall maturity (1 to 5)",
            range_y=[0, 5],
        )
        fig_bar.update_traces(marker_color=PRIMARY)
        fig_bar.update_yaxes(
            tickvals=[1, 2, 3, 4, 5],
            ticktext=["Beginning", "Emerging", "Learning", "Developing", "Mastering"],
            title=None,
        )
        fig_bar.update_xaxes(title=None, showticklabels=False)
        fig_bar.update_layout(margin=dict(l=80, r=10, t=40, b=20))

        st.plotly_chart(fig_bar, use_container_width=True)

        st.markdown(
            "_The bar shows your current average position on the government maturity framework._"
        )

    # RIGHT: Radar (themes profile, 1–5 scale)
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
            title="Maturity profile across six themes (1 to 5 scale)",
        )
        st.plotly_chart(figm, use_container_width=True)

        st.markdown(
            "_The radar shows how that level is distributed across the six themes "
            "(Uses, Data, Leadership, Culture, Tools, Skills)._"
        )

    # Mini-report export for maturity
    maturity_rows = []
    for name, _ in MATURITY_THEMES:
        score = st.session_state["_maturity_scores"][name]
        maturity_rows.append(
            {
                "Theme": name,
                "Score (1 to 5)": score,
                "Level": MATURITY_SCALE[score],
            }
        )
    maturity_rows.append(
        {
            "Theme": "Overall (average)",
            "Score (1 to 5)": round(m_avg, 2),
            "Level": current_level_name,
        }
    )
    maturity_df = pd.DataFrame(maturity_rows)
    maturity_csv = maturity_df.to_csv(index=False).encode("utf-8")

    st.download_button(
        "Download maturity snapshot (CSV)",
        data=maturity_csv,
        file_name="maturity_snapshot.csv",
        mime="text/csv",
        help="Download your current maturity assessment for use in slide decks or programme plans.",
    )

    st.markdown("---")

    # ------- Section 2: Tensions -------
    st.markdown("### 3) Strategic tensions (current and target)")

    st.caption(
        "For each lens, 0 means the left label and 100 means the right label. "
        "Hints and warnings adapt to your maturity profile."
    )

    colL, colR = st.columns(2)

    # Current profile
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
                    help=f"{left_lbl} to {right_lbl}",
                    key=f"cur_{dim}",
                )
                st.caption(
                    f"{left_lbl} ← {st.session_state['_current_scores'][dim]}% → {right_lbl}"
                )

    # Target profile + hints/conflicts
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
                    help=f"{left_lbl} to {right_lbl}",
                    key=f"tgt_{dim}",
                )
                st.caption(
                    f"{left_lbl} ← {st.session_state['_target_scores'][dim]}% → {right_lbl}"
                )

                hint = hint_for_lens(dim, m_avg, current_level_name)
                if hint:
                    st.markdown(
                        f"<div class='info-panel'><strong>Hint:</strong> {hint}</div>",
                        unsafe_allow_html=True,
                    )

                warn = conflict_for_target(
                    dim, st.session_state["_target_scores"][dim], m_avg
                )
                if warn:
                    st.markdown(
                        f"<div class='warn'>⚠️ {warn}</div>",
                        unsafe_allow_html=True,
                    )

    # Twin radar: current vs target
    dims = [a[0] for a in AXES]
    cur01 = [st.session_state["_current_scores"][d] / 100 for d in dims]
    tgt01 = [st.session_state["_target_scores"][d] / 100 for d in dims]
    fig = go.Figure()
    fig.add_trace(radar_trace(cur01, dims, "Current", opacity=0.6))
    fig.add_trace(radar_trace(tgt01, dims, "Target", opacity=0.5))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
        title="Current and target fingerprints across ten strategic lenses",
    )
    st.plotly_chart(fig, use_container_width=True)

# ====================================================
# 🧭 SHIFT (from positions to priority shifts)
# ====================================================
with tab_shift:
    st.subheader("Shift")

    st.caption(
        "This page compares current and target positions across the lenses and highlights the biggest shifts. "
        "Use it to decide where to focus first."
    )

    ensure_sessions()
    dims = [a[0] for a in AXES]
    current = st.session_state.get("_current_scores", {d: 50 for d in dims})
    target = st.session_state.get("_target_scores", {d: 50 for d in dims})
    m_scores = st.session_state.get("_maturity_scores", {k: 3 for k, _ in MATURITY_THEMES})
    m_avg = sum(m_scores.values()) / len(m_scores) if m_scores else 0
    level_name = maturity_label(m_avg)
    biz_state = st.session_state.get("_biz_priority", {})

    # Context summary
    st.markdown("### 1) Quick context")

    outcomes = biz_state.get("outcomes", [])
    questions = biz_state.get("questions", "")
    capabilities = biz_state.get("capabilities", [])

    with st.expander("Business priorities snapshot", expanded=False):
        if outcomes:
            st.markdown("**Top outcomes selected:**")
            for o in outcomes:
                st.markdown(f"- {o}")
        else:
            st.markdown("_No outcomes selected yet in the Diagnose tab._")

        if questions.strip():
            st.markdown("**Key questions leaders are asking:**")
            st.markdown(questions)
        else:
            st.markdown("_No key questions recorded yet in the Diagnose tab._")

        if capabilities:
            st.markdown("**Capabilities your strategy needs to enable:**")
            for c in capabilities:
                st.markdown(f"- {c}")
        else:
            st.markdown("_No capabilities selected yet in the Diagnose tab._")

    st.markdown("---")

    # Core gap analysis
    st.markdown("### 2) Gap by lens")

    rows = []
    for d, left_lbl, right_lbl in AXES:
        diff = target[d] - current[d]
        mag = abs(diff)
        direction = (
            f"toward **{right_lbl}**"
            if diff > 0
            else (f"toward **{left_lbl}**" if diff < 0 else "no change")
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

    # Narrative summary
    moves_left = sum(1 for v in gap_df["Change needed"] if v < 0)
    moves_right = sum(1 for v in gap_df["Change needed"] if v > 0)
    zero_moves = sum(1 for v in gap_df["Change needed"] if v == 0)

    st.markdown(
        f"At overall maturity level **{level_name}** (average {m_avg:.1f} out of 5), "
        f"you are planning to move **{moves_left} lens or lenses toward the left**, "
        f"**{moves_right} toward the right**, and leaving **{zero_moves} unchanged**."
    )

    st.dataframe(
        gap_df[["Lens", "Current", "Target", "Change needed", "Direction", "Conflict"]],
        use_container_width=True,
    )

    bar = px.bar(
        gap_df.sort_values("Change needed"),
        x="Change needed",
        y="Lens",
        orientation="h",
        title="Signed change needed (negative means move left, positive means move right)",
    )
    color_series = gap_df["Conflict"].map({True: RED, False: PRIMARY})
    bar.data[0].marker.color = color_series
    st.plotly_chart(bar, use_container_width=True)

    # Priority list and seed for Actions
    TOP_N = 3
    top = gap_df.head(TOP_N)
    st.markdown(f"### 3) Priority shifts (top {TOP_N})")

    if len(top):
        bullets = []
        for _, row in top.iterrows():
            d = row["Lens"]
            diff = row["Change needed"]
            note = row["Conflict note"]
            left_lbl = [a[1] for a in AXES if a[0] == d][0]
            right_lbl = [a[2] for a in AXES if a[0] == d][0]
            if diff > 0:
                line = f"- **{d}**: shift toward **{right_lbl}** (change of +{int(diff)} points)"
            elif diff < 0:
                line = f"- **{d}**: shift toward **{left_lbl}** (change of {int(diff)} points)"
            else:
                line = f"- **{d}**: no change"
            if note:
                line += f"  \n  <span class='warn'>⚠️ {note}</span>"
            bullets.append(line)
        st.markdown("\n".join(bullets), unsafe_allow_html=True)

        # Seed actions table for Actions tab
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
            "Current and target are identical, so there are no shifts. "
            "Adjust the sliders in the Diagnose tab to see gaps."
        )

    st.markdown(
        "_Use this view live in workshops to agree which shifts you want to act on first._"
    )

# ====================================================
# ✅ ACTIONS
# ====================================================
with tab_actions:
    st.subheader("Actions and projects")

    st.caption(
        "Turn your priority shifts into a concrete project log. "
        "Describe the project, estimate impact, assign owners and timelines, then export to CSV."
    )

    ensure_sessions()
    actions_df = st.session_state.get("_actions_df", pd.DataFrame())

    if actions_df.empty:
        st.info(
            "No priority shifts have been generated yet. "
            "Go to the Shift tab to calculate gaps and priorities."
        )
    else:

        # Add project and impact columns if missing
        project_and_impact_cols = [
            "Project description",
            "Project type",
            "Data maturity theme",
            "Impact type",
            "Est annual financial impact (£)",
            "Users affected (volume)",
            "Confidence (1 to 5)",
            "Impact notes",
        ]

        for col in project_and_impact_cols:
            if col not in actions_df.columns:
                actions_df[col] = ""

        # Remove old columns that are no longer helpful in view
        for col in ["Lens", "Direction"]:
            if col in actions_df.columns:
                actions_df = actions_df.drop(columns=[col])

        # Preset options for "Project type"
        project_type_options = [
            "Data product",
            "Data pipeline",
            "Data platform or tooling",
            "Standards or governance",
            "Operational analytics",
            "Policy data service",
            "Data quality uplift",
            "API or integration",
            "Skills or capability",
        ]

        # Preset options for "Data maturity theme"
        maturity_theme_options = [
            "Governance",
            "Architecture",
            "Tools",
            "Skills",
            "Community",
        ]

        # Preset options for "Impact type"
        impact_type_options = [
            "Financial efficiency",
            "User productivity",
            "Data quality improvement",
            "Risk reduction",
            "Environmental or policy outcomes",
            "Citizen experience",
            "Delivery unblocker",
        ]

        # Reorder columns so Project description sits right after Priority
        preferred_order = [
            "Priority",
            "Project description",
            "Project type",
            "Data maturity theme",
            "Impact type",
            "Est annual financial impact (£)",
            "Users affected (volume)",
            "Confidence (1 to 5)",
            "Impact notes",
        ]
        existing_cols = list(actions_df.columns)
        ordered_cols = [c for c in preferred_order if c in existing_cols] + [
            c for c in existing_cols if c not in preferred_order
        ]
        actions_df = actions_df[ordered_cols]

        st.caption(
            "Use rough estimates. The goal in workshops is focus and alignment, not precision."
        )

        with st.expander("How to describe projects and impact", expanded=False):
            st.markdown(
                """
**Project description**
- Describe a concrete piece of work, for example:
  - "Build shared land use data service for policy teams"
  - "Retire legacy register and migrate to common platform"
  - "Standardise reference data for water quality reporting"

**Project type**
- Classify the work, for example data product, pipeline, platform, standards or governance.

**Data maturity theme**
- Map the project to a primary theme such as governance, architecture, tools, skills or community.

**Impact fields**
- **Impact type**: choose one that best describes the benefit.
- **Est annual financial impact (£)**: rough one year saving or benefit if this works.
- **Users affected (volume)**: staff, partners or service users touched.
- **Confidence (1 to 5)**: 1 is very uncertain, 5 is very confident.
- **Impact notes**: one sentence that explains your estimate.
                """
            )

        # Editable project and action log
        st.markdown("### Project and action log")

        edited = st.data_editor(
            actions_df,
            num_rows="dynamic",
            use_container_width=True,
            key="actions_editor",
            column_config={
                "Project type": st.column_config.SelectboxColumn(
                    "Project type",
                    options=project_type_options,
                    help="What kind of project or work item is this.",
                ),
                "Data maturity theme": st.column_config.SelectboxColumn(
                    "Data maturity theme",
                    options=maturity_theme_options,
                    help="Primary data maturity theme this project supports.",
                ),
                "Impact type": st.column_config.SelectboxColumn(
                    "Impact type",
                    options=impact_type_options,
                    help="Choose the type of impact this project will create.",
                ),
                "Est annual financial impact (£)": st.column_config.NumberColumn(
                    "Est annual financial impact (£)",
                    help="Estimated one year financial benefit or saving.",
                ),
                "Users affected (volume)": st.column_config.NumberColumn(
                    "Users affected (volume)",
                    help="Approx number of users or service cases touched.",
                ),
                "Confidence (1 to 5)": st.column_config.NumberColumn(
                    "Confidence (1 to 5)",
                    min_value=1,
                    max_value=5,
                    step=1,
                    help="Your level of certainty in the impact estimate.",
                ),
            },
        )

        # Save edited
        st.session_state["_actions_df"] = edited

        # Impact dashboard
        st.markdown("### Impact dashboard")

        impact_df = edited.copy()

        numeric_cols = [
            "Est annual financial impact (£)",
            "Users affected (volume)",
            "Confidence (1 to 5)",
        ]
        for col in numeric_cols:
            if col in impact_df.columns:
                impact_df[col] = pd.to_numeric(impact_df[col], errors="coerce")

        total_financial = impact_df.get(
            "Est annual financial impact (£)", pd.Series(dtype="float")
        ).sum(skipna=True)
        total_users = impact_df.get(
            "Users affected (volume)", pd.Series(dtype="float")
        ).sum(skipna=True)
        avg_conf = impact_df.get(
            "Confidence (1 to 5)", pd.Series(dtype="float")
        ).mean(skipna=True)

        k1, k2, k3 = st.columns(3)
        k1.metric("Total estimated annual impact (£)", f"{total_financial:,.0f}")
        k2.metric("Users affected (total)", f"{int(total_users):,}")
        k3.metric(
            "Average confidence",
            f"{avg_conf:.1f}" if pd.notna(avg_conf) else "n a",
        )

        if "Impact type" in impact_df.columns:
            impact_by_type = (
                impact_df.groupby("Impact type", dropna=True)
                .agg({"Est annual financial impact (£)": "sum"})
                .reset_index()
            )

            if not impact_by_type.empty:
                st.bar_chart(
                    impact_by_type.set_index("Impact type")[
                        ["Est annual financial impact (£)"]
                    ]
                )
                st.caption("Bars show where financial impact is concentrated.")
            else:
                st.caption(
                    "Impact chart will appear once impact types and values are filled in."
                )
        else:
            st.caption("Add an Impact type column to see impact by category.")

        # Quick prioritisation view
        st.markdown("### Quick prioritisation view")

        view_df = edited.copy()

        f1, f2, f3 = st.columns(3)

        project_types_present = sorted(
            [p for p in project_type_options if p in view_df["Project type"].unique()]
        )
        project_type_filter = f1.selectbox(
            "Filter by project type",
            ["All"] + project_types_present,
            index=0,
        )

        impact_types_present = sorted(
            [i for i in impact_type_options if i in view_df["Impact type"].unique()]
        )
        impact_type_filter = f2.selectbox(
            "Filter by impact type",
            ["All"] + impact_types_present,
            index=0,
        )

        sort_by = f3.selectbox(
            "Sort by",
            [
                "Est annual financial impact (£)",
                "Users affected (volume)",
                "Confidence (1 to 5)",
            ],
            index=0,
        )

        if project_type_filter != "All":
            view_df = view_df[view_df["Project type"] == project_type_filter]

        if impact_type_filter != "All":
            view_df = view_df[view_df["Impact type"] == impact_type_filter]

        view_df[sort_by] = pd.to_numeric(view_df[sort_by], errors="coerce")
        view_df = view_df.sort_values(sort_by, ascending=False)

        st.dataframe(view_df, use_container_width=True)
        st.caption(
            "Use this view live to focus on the projects with the biggest potential impact."
        )

        # Export
        csv_bytes = edited.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download actions as CSV",
            data=csv_bytes,
            file_name="data_strategy_projects_and_actions.csv",
            mime="text/csv",
        )

        st.markdown(
            "> This table can feed directly into programme plans, OKRs or a delivery roadmap."
        )

# ====================================================
# 📚 RESEARCH (skills, frameworks, case studies)
# ====================================================
with tab_research:
    st.subheader("Research and skills")

    st.markdown(
        """
Use this page to reflect on your own skills as a data strategist and explore frameworks and case studies
that inform data strategy work in the public sector.
"""
    )

    st.markdown("### 1) Skills self assessment")

    st.caption(
        "For each behaviour, pick the statement that feels most like you today. "
        "This is for reflection only; nothing is stored or shared beyond your session."
    )

    LEVEL_LABELS = [
        "1 – Early awareness",
        "2 – Practising",
        "3 – Confident and consistent",
        "4 – Leading and coaching others",
    ]

    BEHAVIOUR_SKILLS = {
        "Seeing the big picture": [
            "Connect data work to policy outcomes and citizen impact.",
            "Balance short term delivery with long term strategic positioning.",
        ],
        "Leadership and communicating": [
            "Tell compelling data stories for senior, non technical audiences.",
            "Frame trade offs and tensions in clear, human language.",
        ],
        "Delivering at pace": [
            "Shape lean, test and learn delivery plans for data initiatives.",
            "Balance experimentation with delivery discipline and governance.",
        ],
        "Changing and improving": [
            "Prototype new uses of AI and data safely and responsibly.",
            "Spot opportunities to simplify, standardise and reuse.",
        ],
        "Collaborating and partnering": [
            "Broker alignment across digital, data, policy and operations teams.",
            "Work with external partners such as academia, vendors or other departments.",
        ],
        "Developing self and others": [
            "Build data literacy and confidence in others.",
            "Coach teams to think in terms of value, not just tools.",
        ],
        "Data skills (technical and analytical)": [
            "Work with analytical teams on methods, limitations and assumptions.",
            "Understand enough of data architecture or engineering to ask the right questions.",
        ],
    }

    if "_skills_matrix" not in st.session_state:
        st.session_state["_skills_matrix"] = {}

    skills_data = []

    for behaviour, skills in BEHAVIOUR_SKILLS.items():
        st.markdown(f"#### {behaviour}")
        cols = st.columns(2)
        for i, skill in enumerate(skills):
            with cols[i % 2]:
                key = f"skill_{behaviour}_{i}"
                current_val = st.session_state["_skills_matrix"].get(
                    key, LEVEL_LABELS[1]
                )
                selected = st.selectbox(
                    skill,
                    LEVEL_LABELS,
                    index=LEVEL_LABELS.index(current_val)
                    if current_val in LEVEL_LABELS
                    else 1,
                    key=key,
                )
                st.session_state["_skills_matrix"][key] = selected
                skills_data.append(
                    {
                        "Behaviour": behaviour,
                        "Skill": skill,
                        "Level": selected,
                        "Level_num": int(selected.split("–")[0].strip())
                        if "–" in selected
                        else int(selected.split("-")[0].strip()),
                    }
                )

    st.markdown("---")

    if skills_data:
        skills_df = pd.DataFrame(skills_data)

        summary = (
            skills_df.groupby("Behaviour")["Level_num"]
            .mean()
            .reset_index()
            .rename(columns={"Level_num": "Average level"})
        )

        c1, c2 = st.columns([1, 1])

        with c1:
            st.markdown("### 2) Summary by behaviour")
            st.dataframe(summary, use_container_width=True)

        with c2:
            st.markdown("### 3) Heatmap view")
            heat = skills_df.pivot_table(
                index="Behaviour",
                columns="Skill",
                values="Level_num",
                aggfunc="mean",
            )

            fig_heat = px.imshow(
                heat,
                text_auto=True,
                aspect="auto",
                color_continuous_scale="Blues",
                origin="upper",
                labels=dict(color="Level"),
                title="Skills heatmap (1 = early awareness, 4 = leading or coaching)",
            )
            st.plotly_chart(fig_heat, use_container_width=True)

        csv_skills = skills_df.drop(columns=["Level_num"]).to_csv(
            index=False
        ).encode("utf-8")
        st.download_button(
            "Download skills self assessment (CSV)",
            data=csv_skills,
            file_name="data_strategist_skills_self_assessment.csv",
            mime="text/csv",
        )

    st.markdown("---")

    # Frameworks and case studies
    st.subheader("Frameworks and case studies")
    st.markdown(
        "Selected readings that inform strategic thinking and skills development for data leaders."
    )

    resources = [
        (
            "OECD – Data Governance (Policy Sub Issue)",
            "Policy and governance principles for managing data across its lifecycle.",
            "https://www.oecd.org/en/topics/sub-issues/data-governance.html",
        ),
        (
            "UK Government – Data Quality Framework (case studies)",
            "Government approach to improving reliability and usability of data.",
            "https://www.gov.uk/government/publications/the-government-data-quality-framework/the-government-data-quality-framework-case-studies",
        ),
        (
            "NAO – Improving Government Data: A Guide for Senior Leaders",
            "Practical guidance on leadership, culture and maturity.",
            "https://www.nao.org.uk/wp-content/uploads/2022/07/Improving-government-data-a-guide-for-senior-leaders.pdf",
        ),
        (
            "OECD – A Data Driven Public Sector (2019)",
            "International maturity model for strategic data use in government.",
            "https://www.oecd.org/content/dam/oecd/en/publications/reports/2019/05/a-data-driven-public-sector_1c183670/09ab162c-en.pdf",
        ),
        (
            "IMF – Overarching Strategy on Data and Statistics (2018)",
            "Global strategy for standards, access and capacity building.",
            "https://www.imf.org/-/media/Files/Publications/PP/2018/pp020918-overarching-strategy-on-data-and-statistics-at-the-fund-in-the-digital-age.ashx",
        ),
        (
            "UK – National Data Strategy Monitoring and Evaluation Framework",
            "Indicator suite to monitor progress and maturity across pillars.",
            "https://www.gov.uk/government/publications/national-data-strategy-monitoring-and-evaluation-update/national-data-strategy-monitoring-and-evaluation-framework",
        ),
        (
            "OECD – Measuring the Value of Data and Data Flows (2022)",
            "How data creates economic and social value, and approaches to valuation.",
            "https://www.oecd-ilibrary.org/economics/measuring-the-value-of-data-and-data-flows_2561fe7e-en",
        ),
        (
            "HM Treasury – Public Value Framework (2019)",
            "Assessing how public spending generates measurable value.",
            "https://assets.publishing.service.gov.uk/media/5c883c32ed915d50b3195be3/public_value_framework_and_supplementary_guidance_web.pdf",
        ),
        (
            "Frontier Economics – The Value of Data Assets (2021)",
            "Estimating the economic value of data assets and use in the UK.",
            "https://assets.publishing.service.gov.uk/media/6399f93d8fa8f50de138f220/Frontier_Economics_-_value_of_data_assets_-_Dec_2021.pdf",
        ),
        (
            "OECD – Measuring Data as an Asset (2021)",
            "Methods linking data maturity to national accounts and productivity.",
            "https://www.oecd-ilibrary.org/economics/measuring-data-as-an-asset_b840fb01-en",
        ),
    ]

    def render_resource_cards(resources, cols_per_row=3):
        for i in range(0, len(resources), cols_per_row):
            row_items = resources[i : i + cols_per_row]
            cols = st.columns(len(row_items))
            for col, (title, desc, url) in zip(cols, row_items):
                with col:
                    st.markdown(
                        f"""
                        <div style="
                            background-color: #1e293b;
                            border-radius: 12px;
                            padding: 16px 16px 14px 16px;
                            margin-bottom: 12px;
                            box-shadow: 0 4px 12px rgba(15, 23, 42, 0.35);
                            border: 1px solid rgba(148, 163, 184, 0.4);
                        ">
                            <div style="font-weight: 600; font-size: 0.95rem; color: #e5e7eb; margin-bottom: 6px;">
                                {title}
                            </div>
                            <div style="font-size: 0.85rem; color: #cbd5f5; margin-bottom: 10px;">
                                {desc}
                            </div>
                            <a href="{url}" target="_blank" style="
                                display: inline-flex;
                                align-items: center;
                                gap: 6px;
                                font-size: 0.85rem;
                                font-weight: 500;
                                color: #38bdf8;
                                text-decoration: none;
                            ">
                                <span>Open resource</span>
                                <span style="font-size: 0.9rem;">↗</span>
                            </a>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

    render_resource_cards(resources)

# ====================================================
# ℹ️ ABOUT
# ====================================================
with tab_about:
    st.subheader("About Think Studio")

    # Guiding belief
    st.markdown(
        """
<div class="info-panel">
  <strong>Guiding belief:</strong> In data strategy, best practices often fall short.
  Every organisation has its own pressures, incentives, risks and rhythms of delivery.
  Strong strategies require a grounded understanding of business priorities and the
  constraints people actually face. Think Studio is designed to make those conversations easier.
</div>
""",
        unsafe_allow_html=True,
    )

    # Why it exists
    st.markdown("### Why Think Studio was created")

    st.markdown(
        """
Over the last few years I found myself having the same conversations with colleagues across government:
how to turn broad ambitions about data into something that fits real delivery pressures, governance,
funding cycles and skills.

Developing a data strategy is not the same as delivering a single data product. It sits at the intersection
of policy, operations, technology, people and culture. Many leaders are asked to own this space while also
running busy portfolios and teams.
"""
    )

    st.markdown(
        """
I built Think Studio as a side project to help those conversations. It grew out of many one to one discussions
with colleagues, combined with my own practice and experimentation.
"""
    )

    # Personal background
    st.markdown("### A bit about me")

    st.markdown(
        """
I started my career in finance and public spending. Over time I moved closer to data, first through forecasting
and analytical work, then into data leadership roles. Experimenting with data science and machine learning as a
head of forecasting shifted how I thought about both risk and opportunity.

More recently I have focused on data strategy, governance and capability building in central government.
Think Studio was developed while I was also working on AI policy and using AI agents for research and design
as part of an AI fellowship at Imperial College.
"""
    )

    # What this is and is not
    st.markdown("### What Think Studio is and what it is not")

    st.markdown(
        """
Think Studio is:

- A learning and facilitation aid for public sector data leaders and teams.
- A way to structure conversations about business priorities, maturity and strategic tensions.
- A lightweight way to move from insight to a first cut set of actions and projects.

Think Studio is not:

- An official government product or an endorsed maturity assessment.
- A benchmarking tool for comparing named organisations.
- A substitute for organisational governance, professional judgement or detailed analysis.
"""
    )

    # How it works at a high level
    st.markdown("### How it works at a high level")

    st.markdown(
        """
Think Studio combines four main elements:

1. **Explore** a curated set of public sector data, digital, analytics and AI strategies to understand the landscape.  
2. **Diagnose** by clarifying business priorities, self assessing maturity and setting positions on key tensions.  
3. **Shift** by making the size and direction of change explicit and identifying the most important moves.  
4. **Actions and Research** by translating shifts into projects with indicative impact and connecting them to skills and frameworks.

All calculations are simple and transparent. There are no hidden models or external benchmarks.
"""
    )

    # How to contribute
    st.markdown("### Collaboration and reuse")

    st.markdown(
        """
You are welcome to reuse or adapt the ideas and code for your own context.

If you want to contribute you can:

- Suggest new or updated strategies for the Explore dataset.
- Propose improvements to the lenses, questions or copy.
- Share how you have used Think Studio in practice, including what did and did not work.

The easiest way to start is through the GitHub repository or by contacting me on LinkedIn.
"""
    )

    st.markdown(
        """
<small>
Think Studio is a personal project created in my own time. Any views or design choices here should not be taken
as representing the official position of any department or organisation.
</small>
""",
        unsafe_allow_html=True,
    )

# ---------------- Footer ----------------
st.markdown(
    """
---
<div class="footer">
<p>Think Studio is a community learning project. It collects no personal data.
All strategy documents are drawn from publicly available sources under the Open Government Licence.</p>

<p>
<img src="https://img.shields.io/badge/Open%20Source-Yes-1d70b8" height="22">
<img src="https://img.shields.io/badge/Content-OGL%20v3.0-0b0c0c" height="22">
<img src="https://img.shields.io/badge/No%20Personal%20Data%20Collected-✓-28a197" height="22">
<img src="https://img.shields.io/badge/Community%20Project-Open%20Collaboration-f47738" height="22">
<img src="https://img.shields.io/badge/Built%20with-Streamlit-FF4B4B" height="22">
</p>
</div>
""",
    unsafe_allow_html=True,
)
