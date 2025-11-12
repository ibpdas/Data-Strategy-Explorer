# ---------------------------
# Public Sector Data Strategy Explorer
# ---------------------------
import os
import re
from datetime import date
import pandas as pd
import plotly.express as px
from slugify import slugify
from rapidfuzz import fuzz, process
import streamlit as st

CSV_PATH = os.path.join("strategies.csv")

# ------------ Utilities
@st.cache_data(show_spinner=False)
def load_data(path=CSV_PATH):
    df = pd.read_csv(path).fillna("")
    # enforce minimal columns
    required = ["id","title","organisation","org_type","country","year","scope","link","themes","pillars","summary","source","date_added"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        st.warning(f"Missing expected columns: {missing}")
    # coerce types
    if "year" in df.columns:
        df["year"] = pd.to_numeric(df["year"], errors="coerce")
    return df

def tokenize_semicol(col):
    if not col: return []
    return [t.strip() for t in str(col).split(";") if t.strip()]

def fuzzy_filter(df, query, limit=100):
    if not query: return df
    query = query.strip()
    pool = (df["title"] + " " + df["organisation"] + " " + df["summary"]).tolist()
    matches = process.extract(query, pool, scorer=fuzz.WRatio, limit=len(pool))
    keep_idx = set([i for i, (_, score, i) in enumerate(matches) if score >= 60])
    return df.iloc[list(keep_idx)].head(limit)

def explode_semicol(df, col):
    # returns long form for themes/pillars charts
    long_rows = []
    for _, r in df.iterrows():
        items = tokenize_semicol(r.get(col, ""))
        if not items:
            long_rows.append({**r.to_dict(), col: "(none)"})
        else:
            for it in items:
                row = r.to_dict()
                row[col] = it
                long_rows.append(row)
    return pd.DataFrame(long_rows)

# ------------ App
st.set_page_config(page_title="Public Sector Data Strategy Explorer", layout="wide")
st.title("Public Sector Data Strategy Explorer")
st.caption("Compare UK public sector data strategies, spot patterns, and reuse what works.")

with st.sidebar:
    st.subheader("Filters")
    df = load_data()
    years = sorted([int(y) for y in df["year"].dropna().unique()]) if "year" in df else []
    min_y, max_y = (min(years), max(years)) if years else (2015, date.today().year)
    year_range = st.slider("Year range", min_value=min_y, max_value=max_y, value=(min_y, max_y), step=1)

    org_types = sorted(df["org_type"].unique())
    org_type_sel = st.multiselect("Organisation type", org_types, default=org_types)

    countries = sorted(df["country"].unique())
    country_sel = st.multiselect("Country", countries, default=countries)

    scopes = sorted(df["scope"].unique())
    scope_sel = st.multiselect("Scope", scopes, default=scopes)

    q = st.text_input("Search title, organisation, summary", "")

    st.markdown("---")
    st.markdown("**Data**")
    st.write(f"{len(df)} strategies")
    st.markdown("[Contribute via GitHub Issues](https://github.com/ibpdas/Public-Sector-Data-Strategy-Explorer-/issues)")

# apply filters
fdf = df.copy()
if "year" in fdf.columns:
    fdf = fdf[(fdf["year"] >= year_range[0]) & (fdf["year"] <= year_range[1])]
if org_type_sel:
    fdf = fdf[fdf["org_type"].isin(org_type_sel)]
if country_sel:
    fdf = fdf[fdf["country"].isin(country_sel)]
if scope_sel:
    fdf = fdf[fdf["scope"].isin(scope_sel)]

fdf = fuzzy_filter(fdf, q)

# ---------- KPIs
col_a, col_b, col_c, col_d = st.columns(4)
col_a.metric("Strategies", len(fdf))
col_b.metric("Org types", fdf["org_type"].nunique())
col_c.metric("Countries", fdf["country"].nunique())
yr_min = int(fdf["year"].min()) if len(fdf) and pd.notna(fdf["year"].min()) else "-"
yr_max = int(fdf["year"].max()) if len(fdf) and pd.notna(fdf["year"].max()) else "-"
col_d.metric("Year span", f"{yr_min}–{yr_max}")

# ---------- Charts
st.subheader("Patterns")
left, right = st.columns([2,2])

with left:
    if "year" in fdf.columns and len(fdf):
        by_year = fdf.groupby("year", dropna=True).size().reset_index(name="count")
        fig1 = px.bar(by_year, x="year", y="count", title="Strategies by year")
        st.plotly_chart(fig1, use_container_width=True)

with right:
    if "themes" in fdf.columns and len(fdf):
        themes_long = explode_semicol(fdf, "themes")
        by_theme = themes_long.groupby("themes").size().reset_index(name="count").sort_values("count", ascending=False)
        fig2 = px.treemap(by_theme, path=["themes"], values="count", title="Top themes")
        st.plotly_chart(fig2, use_container_width=True)

left2, right2 = st.columns([2,2])
with left2:
    if "org_type" in fdf.columns and len(fdf):
        by_org = fdf.groupby("org_type").size().reset_index(name="count").sort_values("count", ascending=False)
        fig3 = px.bar(by_org, x="org_type", y="count", title="Strategies by organisation type")
        st.plotly_chart(fig3, use_container_width=True)

with right2:
    if "pillars" in fdf.columns and len(fdf):
        pillars_long = explode_semicol(fdf, "pillars")
        by_pillar = pillars_long.groupby("pillars").size().reset_index(name="count").sort_values("count", ascending=False)
        fig4 = px.treemap(by_pillar, path=["pillars"], values="count", title="Pillars mentioned")
        st.plotly_chart(fig4, use_container_width=True)

st.markdown("---")

# ---------- Table + cards
st.subheader("Explorer")
st.caption("Click a title to open the official document in a new tab.")
st.dataframe(
    fdf[["title","organisation","org_type","country","year","scope","themes","pillars","source"]].sort_values(["year","organisation"], ascending=[False, True]),
    use_container_width=True,
    hide_index=True,
)

st.markdown("### Details")
for _, r in fdf.sort_values("year", ascending=False).iterrows():
    with st.expander(f"📄 {r['title']} — {r['organisation']} ({int(r['year']) if pd.notna(r['year']) else '—'})"):
        st.write(r["summary"] if r["summary"] else "_No summary yet._")
        meta_cols = st.columns(4)
        meta_cols[0].write(f"**Org type:** {r['org_type']}")
        meta_cols[1].write(f"**Country:** {r['country']}")
        meta_cols[2].write(f"**Scope:** {r['scope']}")
        meta_cols[3].write(f"**Source:** {r['source']}")
        st.write(f"**Themes:** {', '.join(tokenize_semicol(r['themes'])) or '—'}")
        st.write(f"**Pillars:** {', '.join(tokenize_semicol(r['pillars'])) or '—'}")
        if r["link"]:
            st.link_button("Open document", r["link"], use_container_width=False)

