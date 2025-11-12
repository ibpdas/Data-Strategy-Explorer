# ---------------------------
# Public Sector Data Strategy Explorer — Theme‑Free (with Reload + Source Picker)
# ---------------------------
import os, glob
import time
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
    "link","archetypes","summary","source","date_added"
]

ARCH_HELP = {
    "foundational":"Building quality, governance, and standards",
    "transformational":"Driving innovation and change (e.g., AI, automation)",
    "collaborative":"Federated, cross‑government sharing and partnerships",
    "insight-led":"Evidence‑based decisions and analytics",
    "citizen-focused":"Trust, transparency, and service design"
}

st.set_page_config(page_title="Public Sector Data Strategy Explorer", layout="wide")
st.title("Public Sector Data Strategy Explorer")
st.caption("Theme‑free, archetypes‑only — with data‑source picker and reload switch.")

# --- Data source picker (any CSV in current folder)
csv_files = sorted([f for f in glob.glob("*.csv") if os.path.isfile(f)])
default_csv = "strategies.csv" if "strategies.csv" in csv_files else (csv_files[0] if csv_files else None)
if not csv_files:
    st.error("No CSV files found in the app folder. Please add a CSV (e.g., strategies.csv).")
    st.stop()

with st.sidebar:
    st.subheader("Data source")
    csv_path = st.selectbox("CSV file", options=csv_files, index=csv_files.index(default_csv) if default_csv else 0)
    # show file stats
    try:
        mtime = os.path.getmtime(csv_path)
        st.caption(f"📄 **{csv_path}** — last modified: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(mtime))}")
    except Exception:
        mtime = 0
        st.caption(f"📄 **{csv_path}** — last modified: unknown")

    reload_now = st.button("🔄 Reload data (clear cache)")
    if reload_now:
        st.cache_data.clear()
        st.experimental_rerun()

# --- Loader: cache keyed by (csv_path, mtime), so edits invalidate cache
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
    df = load_data(csv_path, mtime)
except Exception as e:
    st.error(f"⚠️ {e}")
    st.stop()

# --- Sidebar filters
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

    arch_all = ["foundational","transformational","collaborative","insight-led","citizen-focused"]
    arch_sel = st.multiselect("Archetype (any)", arch_all, default=[],
                              help="Filter strategies by any of the selected archetypes.")

    q = st.text_input("Search title, organisation, summary", "", help="Fuzzy search on title/organisation/summary.")
    st.markdown("---")
    debug = st.checkbox("Show debug info")

def toks(cell):
    if not cell: return []
    return [t.strip() for t in str(cell).split(";") if t.strip()]

def fuzzy_filter(df, query, limit=500):
    if not query:
        return df
    q = query.strip()
    hay = (df["title"] + " " + df["organisation"] + " " + df["summary"]).fillna("")
    if HAS_RAPIDFUZZ:
        matches = process.extract(q, hay.tolist(), scorer=fuzz.WRatio, limit=len(hay))
        keep_idx = [i for _, score, i in matches if score >= 60]
        if not keep_idx: return df.iloc[0:0]
        return df.iloc[keep_idx].head(limit)
    else:
        mask = hay.str.contains(q, case=False, na=False)
        return df[mask].head(limit)

# --- Apply filters
fdf = df.copy()
if year_range:
    fdf = fdf[(fdf["year"].between(year_range[0], year_range[1], inclusive="both")) | (fdf["year"].isna())]
if org_type_sel:
    fdf = fdf[fdf["org_type"].isin(org_type_sel)]
if country_sel:
    fdf = fdf[fdf["country"].isin(country_sel)]
if scope_sel:
    fdf = fdf[fdf["scope"].isin(scope_sel)]

if arch_sel:
    fdf = fdf[fdf["archetypes"].apply(lambda s: any(a in set(toks(s)) for a in arch_sel))]

fdf = fuzzy_filter(fdf, q)

# --- Debug
top_note = f"Loaded **{len(df)}** rows from **{csv_path}** (last modified {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(mtime))})."
st.info(top_note)
if debug:
    with st.expander("🔎 Debug"):
        st.write("Working directory:", os.getcwd())
        st.write("Files:", os.listdir("."))
        st.write("Rows loaded:", len(df), "| Rows after filters:", len(fdf))
        st.dataframe(df.head(), use_container_width=True)

if fdf.empty:
    st.warning("No results match your filters/search. Try clearing a filter or the search box.")
    st.stop()

# --- KPIs
c1, c2, c3, c4 = st.columns(4)
c1.metric("Strategies", len(fdf))
c2.metric("Org types", fdf["org_type"].nunique())
c3.metric("Countries", fdf["country"].nunique())
yr_min = int(fdf["year"].min()) if pd.notna(fdf["year"].min()) else "—"
yr_max = int(fdf["year"].max()) if pd.notna(fdf["year"].max()) else "—"
c4.metric("Year span", f"{yr_min}–{yr_max}")

# --- Archetype distribution
st.subheader("Archetypes snapshot")
a_long = []
for _, r in fdf.iterrows():
    for a in toks(r.get("archetypes", "")):
        a_long.append({"arch": a})
a_df = pd.DataFrame(a_long)
if not a_df.empty:
    left, right = st.columns([2,1])
    with left:
        by_arch = a_df.groupby("arch").size().reset_index(name="count").sort_values("count", ascending=False)
        fig = px.bar(by_arch, x="arch", y="count", title="Strategies by archetype")
        fig.update_xaxes(tickangle=20)
        st.plotly_chart(fig, use_container_width=True)
    with right:
        fig2 = px.pie(by_arch, names="arch", values="count", title="Share by archetype")
        st.plotly_chart(fig2, use_container_width=True)

st.markdown("---")
st.subheader("Explorer")
show_cols = ["title","organisation","org_type","country","year","scope","archetypes","source"]
st.dataframe(
    fdf[show_cols].sort_values(["year","organisation"], ascending=[False, True]),
    use_container_width=True, hide_index=True
)

st.download_button(
    "Download filtered CSV",
    data=fdf.to_csv(index=False).encode("utf-8"),
    file_name="strategies_filtered.csv",
    mime="text/csv"
)

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
        archs = toks(r.get("archetypes",""))
        if archs:
            st.write("**Archetypes:** " + ", ".join([f"{a} — {ARCH_HELP.get(a, '')}" for a in archs]))
        else:
            st.write("**Archetypes:** —")
        if r["link"]:
            st.link_button("Open document", r["link"], use_container_width=False)
