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
  <div class="sub">Data Strategy Accelerator for public sector leaders.</div>
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
    r = list(values01) +
