"""
LexiGuard - Sanctions & Adverse Media Terminal
Streamlit UI for explainable sanctions screening with institutional-grade design.
"""
import streamlit as st
import pandas as pd
import base64
from datetime import datetime
import re

from app.config import COLORS, FOOTER_TEXT
from app.ingest.ofac_loader import OFACLoader
from app.match.matcher import FuzzyMatcher
from app.media.rss import MediaIngester
from app.risk.scorer import RiskScorer
from app.audit.logger import AuditLogger
from app.config import DB_PATH
import json, datetime as dt, re, os
# ---- service singletons (shared across the app) ----
try:
    ofac_loader = OFACLoader()
except Exception:
    ofac_loader = None

try:
    ingester = MediaIngester()
except Exception:
    ingester = None

try:
    scorer = RiskScorer()
except Exception:
    scorer = None

try:
    auditor = AuditLogger()
except Exception:
    auditor = None

# ── MUST be the first Streamlit command and called only once ───────────
st.set_page_config(
    page_title="LexiGuard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)
# ───────────────────────────────────────────────────────────────────────

# Premium font pairing (Inter + IBM Plex Mono)
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;600&display=swap" rel="stylesheet">
""", unsafe_allow_html=True)

# Institutional CSS theme (visual only)
st.markdown("""
<style>
:root {
  --bg: {COLORS['primary']};
  --surface: {COLORS['secondary']};
  --accent: {COLORS['accent']};
  --muted: {COLORS['text_muted']};
  --border: {COLORS['border']};
  --success: {COLORS['success']};
  --warning: {COLORS['warning']};
  --danger: {COLORS['danger']};

  --accent-strong: color-mix(in srgb, var(--accent) 72%, black 8%);
  --glass: rgba(255,255,255,0.03);
  --glass-2: rgba(255,255,255,0.025);
  --focus-alpha: 0.18;

  --radius-lg: 16px;
  --radius-md: 10px;
  --radius-pill: 999px;

  --transition-fast: 180ms cubic-bezier(.2,.8,.2,1);
}

/* Global reset & typography */
html, body, .stApp {
  background: linear-gradient(180deg, var(--bg) 0%, rgba(0,0,0,0.7) 100%) !important;
  color: var(--surface);
  font-family: "Inter", system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  line-height: 1.48;
  font-size: 15px;
}

/* Main container sizing */
.main .block-container {
  max-width: 1280px;
  padding: 20px 28px 36px;
}

/* ================= Sidebar: frosted, fixed, premium ================= */
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, rgba(6,10,18,0.74), rgba(10,14,22,0.68));
  backdrop-filter: blur(16px) saturate(110%);
  -webkit-backdrop-filter: blur(16px) saturate(110%);
  border-right: 1px solid rgba(255,255,255,0.03);
  box-shadow: inset -1px 0 0 rgba(255,255,255,0.02);
  padding: 20px 18px !important;
  min-width: 300px;
  color: var(--surface);
}
[data-testid="stSidebar"] .css-1d391kg, 
[data-testid="stSidebar"] .block-container {
  padding-left: 0;
  padding-right: 0;
}

[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
  color: var(--surface) !important;
  font-family: "Inter", system-ui;
  letter-spacing: 0.2px;
  margin-bottom: 8px;
}
[data-testid="stSidebar"] h2 { font-size: 1.05rem; font-weight: 700; }
[data-testid="stSidebar"] label, [data-testid="stSidebar"] .css-1kb1vgj {
  color: var(--muted) !important;
  font-weight: 600;
  font-size: 0.92rem;
}

/* Inputs: premium, accessible, rounded */
.stTextInput input,
.stTextArea textarea,
.stDateInput input,
.stNumberInput input,
.st-time-input input,
.stSelectbox div[data-baseweb="select"] > div,
.stMultiSelect div[data-baseweb="select"] > div {
  background: linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01));
  border: 1px solid var(--border) !important;
  color: var(--surface) !important;
  border-radius: var(--radius-md) !important;
  padding: 10px 12px !important;
  min-height: 44px;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.02);
  transition: box-shadow var(--transition-fast), transform var(--transition-fast), border-color var(--transition-fast);
  outline: none !important;
  font-size: 14px;
}
.stTextInput input::placeholder,
.stDateInput input::placeholder,
.stTextArea textarea::placeholder {
  color: rgba(255,255,255,0.18) !important;
  opacity: 1;
}
.stTextInput input:focus,
.stDateInput input:focus,
.stTextArea textarea:focus,
.stSelectbox div[role="combobox"]:focus-within {
  border-color: var(--accent) !important;
  box-shadow: 0 6px 26px rgba(0,0,0,0.5), 0 0 0 4px color-mix(in srgb, var(--accent) var(--focus-alpha), transparent);
  transform: translateY(-1px);
}

/* Larger hit area for inputs */
.stTextInput, .stNumberInput, .stDateInput, .stSelectbox, .stTextArea {
  padding: 4px 0;
}

/* ================= Buttons: pill, gradient, hover glow ================= */
.stButton>button {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  justify-content: center;
  background: linear-gradient(160deg, var(--accent), color-mix(in srgb, var(--accent) 70%, #fff 8%));
  border: none !important;
  color: rgba(10,12,16,0.98) !important;
  border-radius: var(--radius-pill) !important;
  padding: 10px 16px !important;
  font-weight: 700 !important;
  letter-spacing: 0.2px;
  box-shadow: 0 10px 30px rgba(0,0,0,0.55), 0 6px 18px color-mix(in srgb, var(--accent) 20%, transparent);
  transition: transform var(--transition-fast), box-shadow var(--transition-fast), filter var(--transition-fast);
  min-height: 44px;
  cursor: pointer;
}
[data-testid="stSidebar"] .stButton>button {
  padding: 14px 18px !important;
  min-height: 52px;
  font-size: 15px;
}
.stButton>button:hover {
  transform: translateY(-2px) scale(1.01);
  box-shadow: 0 18px 44px rgba(0,0,0,0.62), 0 0 30px rgba(0,0,0,0.12), 0 8px 28px color-mix(in srgb, var(--accent) 30%, transparent);
  filter: saturate(1.05);
}
.stButton>button:active {
  transform: translateY(1px);
  box-shadow: 0 6px 14px rgba(0,0,0,0.6);
  transform: translateY(1px) scale(0.998);
}
.stButton>button[title*="Download"], .stButton>button[title*="Export"], .stButton>button:has(svg[data-icon="download"]) {
  background: linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01));
  color: var(--surface) !important;
  border: 1px solid var(--border);
  box-shadow: none;
}
.stButton>button svg, .stButton>button img {
  height: 18px;
  width: 18px;
  opacity: 0.98;
}

/* ================= Metrics: cardified, large numeric ================= */
div[data-testid="stMetric"] {
  background: linear-gradient(180deg, rgba(255,255,255,0.022), rgba(255,255,255,0.01));
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 12px 14px;
  box-shadow: 0 6px 22px rgba(0,0,0,0.55);
  transition: transform var(--transition-fast), box-shadow var(--transition-fast), border-color var(--transition-fast);
  font-family: "IBM Plex Mono", "Inter", monospace;
  color: var(--surface);
}
div[data-testid="stMetric"]:hover {
  transform: translateY(-3px);
  border-color: var(--accent);
  box-shadow: 0 18px 48px rgba(0,0,0,0.6), 0 0 28px rgba(201,168,106,0.06);
}
div[data-testid="stMetric"] .css-1b3d0te, 
div[data-testid="stMetric"] .stMetricValue {
  color: var(--muted);
  font-weight: 600;
  font-size: 0.92rem;
}
div[data-testid="stMetric"] .stMetricDelta, div[data-testid="stMetric"] .stMetricValue {
  font-family: "IBM Plex Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
  font-variant-numeric: tabular-nums lining-nums;
  font-size: 1.5rem;
  color: var(--surface);
  font-weight: 800;
}
div[data-testid="stMetric"] .stMetricDelta.positive { color: var(--success); }
div[data-testid="stMetric"] .stMetricDelta.negative { color: var(--danger); }

/* ================= DataFrame / Table polish ================= */
.stDataFrame, .element-container .stDataFrame {
  background: linear-gradient(180deg, rgba(255,255,255,0.018), rgba(255,255,255,0.01));
  border-radius: 12px;
  border: 1px solid var(--border);
  padding: 8px;
  box-shadow: 0 10px 28px rgba(0,0,0,0.52);
  overflow: auto;
  font-size: 13px;
}
.stDataFrame table {
  border-collapse: collapse;
  width: 100%;
  font-family: "IBM Plex Mono", monospace;
}
.stDataFrame thead th {
  position: sticky;
  top: 0;
  z-index: 4;
  background: linear-gradient(180deg, rgba(10,14,20,0.9), rgba(8,12,18,0.9));
  color: var(--surface);
  border-bottom: 1px solid var(--border);
  padding: 10px 12px;
  text-align: left;
  font-weight: 700;
  font-size: 13px;
}
.stDataFrame tbody tr {
  transition: background var(--transition-fast), transform var(--transition-fast);
}
.stDataFrame tbody tr:nth-child(odd) {
  background: rgba(255,255,255,0.008);
}
.stDataFrame tbody tr:nth-child(even) {
  background: rgba(255,255,255,0.006);
}
.stDataFrame tbody tr:hover {
  background: linear-gradient(90deg, rgba(201,168,106,0.04), rgba(201,168,106,0.02));
  transform: translateY(-1px);
}
.stDataFrame td, .stDataFrame th {
  padding: 8px 12px;
  border-bottom: 1px solid rgba(255,255,255,0.02);
  color: var(--surface);
  font-variant-numeric: tabular-nums lining-nums;
}
.stDataFrame td, .stDataFrame th { white-space: nowrap; }
.stDataFrame::-webkit-scrollbar, .element-container::-webkit-scrollbar {
  height: 8px; width: 8px;
}
.stDataFrame::-webkit-scrollbar-thumb, .element-container::-webkit-scrollbar-thumb {
  background: linear-gradient(180deg, rgba(30,40,54,0.9), rgba(18,26,38,0.9));
  border-radius: 8px;
  border: 1px solid rgba(255,255,255,0.02);
}

/* ================= Charts: chrome, mono labels, tooltip ================= */
.element-container canvas, .element-container svg, .stPlotlyChart, .stAltairChart {
  background: transparent !important;
  border-radius: var(--radius-lg);
  padding: 12px;
}
.element-container:has(canvas), .element-container:has(svg),
.stPlotlyChart, .stAltairChart {
  background: linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01));
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 12px;
  box-shadow: 0 12px 34px rgba(0,0,0,0.56);
}
.element-container svg text,
.stPlotlyChart text,
.stAltairChart text {
  font-family: "IBM Plex Mono", monospace !important;
  fill: var(--surface) !important;
  font-size: 12px;
}
.stPlotlyChart .hoverlayer, .stPlotlyChart .hovertext, .stPlotlyChart .tooltip {
  background: linear-gradient(180deg, rgba(20,26,34,0.98), rgba(12,16,22,0.98)) !important;
  color: var(--surface) !important;
  border: 1px solid var(--border) !important;
  box-shadow: 0 8px 30px rgba(0,0,0,0.6) !important;
  font-family: "IBM Plex Mono", monospace !important;
  font-size: 12px !important;
}

/* ================= Badges / chips ================= */
.chip, .badge, .stBadge, .stMarkdown b.chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  border-radius: 999px;
  background: linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01));
  color: var(--surface);
  border: 1px solid rgba(255,255,255,0.03);
  font-size: 12px;
}

/* ================= Footer ================= */
footer, .footer {
  text-align: center;
  color: var(--muted);
  font-size: 13px;
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid rgba(255,255,255,0.02);
}
.footer a {
  color: var(--accent);
  text-decoration: none;
  font-weight: 600;
}

/* ================= Focus and accessibility ================= */
:focus {
  outline: none;
  box-shadow: 0 0 0 4px color-mix(in srgb, var(--accent) var(--focus-alpha), transparent), 0 8px 26px rgba(0,0,0,0.6);
  border-radius: 8px;
}
.stApp, .stApp * {
  color-scheme: dark;
}
@media (prefers-reduced-motion: reduce) {
  * {
    transition: none !important;
    animation: none !important;
    transform: none !important;
  }
}
@media (max-width: 1100px) {
  .main .block-container { padding-left: 18px; padding-right: 18px; max-width: 980px; }
  [data-testid="stSidebar"] { min-width: 260px; }
  .stButton>button { padding: 10px 12px !important; }
}
@media (max-width: 820px) {
  .main .block-container { padding-left: 12px; padding-right: 12px; }
  [data-testid="stSidebar"] { position: relative; width: 100% !important; border-right: none; border-bottom: 1px solid rgba(255,255,255,0.02); }
}

/* Small utilities */
.muted { color: var(--muted) !important; }
.accent { color: var(--accent) !important; }
.card {
  background: linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01));
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 14px;
  box-shadow: 0 8px 26px rgba(0,0,0,0.52);
}
</style>
""", unsafe_allow_html=True)


# ---------------------- UI helpers -----------------------
def render_logo():
    return f"""
    <svg width="64" height="64" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="LexiGuard">
      <defs>
        <linearGradient id="g" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stop-color="#BD9468"/>
          <stop offset="100%" stop-color="#A3784D"/>
        </linearGradient>
      </defs>
      <rect width="64" height="64" rx="14" fill="#0F172A"/>
      <circle cx="32" cy="32" r="29" fill="none" stroke="url(#g)" stroke-width="1.5"/>
      <text x="32" y="42" text-anchor="middle" font-size="28" font-weight="700"
            font-family="IBM Plex Mono, monospace" fill="url(#g)">LG</text>
    </svg>
    """


def render_header():
    c1, c2, c3 = st.columns([1, 4, 1])
    with c1:
        st.markdown(render_logo(), unsafe_allow_html=True)
    with c2:
        st.title("LexiGuard — Sanctions & Adverse Media Terminal")
    with c3:
        st.caption(f"Data: OFAC SDN • {datetime.now().strftime('%Y-%m-%d %H:%M')}")

def render_sidebar_input():
    st.sidebar.markdown("### Screening Query")
    name = st.sidebar.text_input("Subject Name", placeholder="Enter full name or entity name")
    dob = st.sidebar.text_input("Date of Birth (Optional)", placeholder="YYYY/MM/DD")
    country = st.sidebar.selectbox("Country", ["Any","USA","UK","Canada","India","China","Russia","UAE","Singapore","Other"])
    st.sidebar.markdown("---")
    c1, c2 = st.sidebar.columns(2)
    with c1:
        run = st.button("🔍 Run Screening", use_container_width=True)
    with c2:
        export = st.button("📊 Export Audit", use_container_width=True)
    return name, dob, country, run, export

# ---------------------- Core workflow --------------------
def perform_screening(query_name: str, query_dob: str, query_country: str):
    """
    Deterministic matching that works with OFAC naming style (LAST, FIRST ...):
      1) ensure DB exists,
      2) token-AND SQL search (each token must appear somewhere in name),
      3) rank with RapidFuzz if present,
      4) compute risk, log, return payload.
    """
    import sqlite3

    q_raw = (query_name or "").strip()
    if not q_raw:
        st.warning("Please enter a subject name.")
        return None

    with st.spinner("🔄 Screening in progress..."):
        # 0) prepare data
        # 0) prepare data (ensure OFAC DB exists)
        loader = globals().get("ofac_loader") or OFACLoader()
        loader.ensure_db()


        # 1) token-AND SQL search
        q_up = q_raw.upper()
        tokens = [t for t in re.split(r"[^A-Z0-9]+", q_up) if t]
        if not tokens:
            st.info("No usable tokens from input.")
            return None

        where_parts = ["UPPER(name) LIKE ?"] * len(tokens)
        params = [f"%{t}%" for t in tokens]

        ctry = None if (not query_country or query_country == "Any") else query_country.strip().upper()
        if ctry:
            where_sql = " AND ".join(where_parts) + " AND UPPER(country)=?"
            params.append(ctry)
        else:
            where_sql = " AND ".join(where_parts)

        sql = (
            "SELECT name, COALESCE(country,'') "
            "FROM sanctions_entities "
            f"WHERE name <> '' AND {where_sql} "
            "LIMIT 100"
        )

        con = sqlite3.connect(DB_PATH); cur = con.cursor()
        cur.execute(sql, params)
        rows = cur.fetchall()
        con.close()

        # 2) if empty, try OR fallback
        if not rows:
            or_sql = " OR ".join(["UPPER(name) LIKE ?"] * len(tokens))
            or_params = [f"%{t}%" for t in tokens]
            if ctry:
                or_sql = f"({or_sql}) AND UPPER(country)=?"
                or_params.append(ctry)
            sql2 = (
                "SELECT name, COALESCE(country,'') "
                "FROM sanctions_entities "
                f"WHERE name <> '' AND {or_sql} "
                "LIMIT 100"
            )
            con = sqlite3.connect(DB_PATH); cur = con.cursor()
            cur.execute(sql2, or_params)
            rows = cur.fetchall()
            con.close()

        # 3) rank with RapidFuzz (optional)
        matches = []
        if rows:
            try:
                from rapidfuzz import fuzz
                scored = []
                for nm, c in rows:
                    score = int(fuzz.token_set_ratio(q_up, (nm or "").upper()))
                    scored.append((score, nm, c))
                scored.sort(reverse=True)
                for score, nm, c in scored[:10]:
                    matches.append({
                        "entity_name": nm, "country": c or "",
                        "match_score": score,
                        "explanation": f"Token-AND SQL + RapidFuzz token_set_ratio = {score}"
                    })
            except Exception:
                for nm, c in rows[:10]:
                    matches.append({
                        "entity_name": nm, "country": c or "",
                        "match_score": 100,
                        "explanation": "Token-AND SQL (no RapidFuzz)"
                    })

        # 4) adverse media (best-effort)
        try:
            media_results = ingester.search_media(q_raw) or []
        except Exception:
            media_results = []

        # 5) risk scoring (fallback safe)
        pep_flag = (query_country in ["USA","UK","Canada"])
        try:
            risk_data = scorer.score_screening(matches, media_results, pep_flag)
        except Exception:
            sanc_part = max([m["match_score"] for m in matches], default=0) * 0.7 / 100.0 * 100
            media_part = min(len(media_results), 5) * 5.0
            pep_part = 10.0 if pep_flag else 0.0
            composite = round(sanc_part + media_part + pep_part)
            level = "HIGH" if composite >= 70 else ("MEDIUM" if composite >= 40 else "LOW")
            risk_data = {
                "risk_level": level,
                "composite_score": composite,
                "breakdown": {
                    "sanctions": {"weight": 0.7, "score": round(sanc_part)},
                    "media": {"weight": 0.2, "score": round(media_part)},
                    "pep": {"weight": 0.1, "score": round(pep_part)},
                },
            }

        payload = {
            "query_name": q_raw,
            "query_dob": str(query_dob or ""),
            "query_country": query_country or "Any",
            "sanctions_matches": matches,
            "media_results": media_results,
            "risk_data": risk_data,
            "timestamp": datetime.utcnow().isoformat(),
        }

        try:
            auditor.log_screening(
                q_raw, str(query_dob or ""), query_country or "Any",
                matches, media_results,
                risk_data["risk_level"], risk_data["composite_score"], payload
            )
        except Exception:
            pass

        return payload

# ---------------------- Rendering ------------------------
def render_results(result):
    if not result:
        return
    st.markdown("### Screening Results")
    risk = result["risk_data"]
    lvl = risk["risk_level"]
    icon = {"HIGH":"🔴","MEDIUM":"🟡","LOW":"🟢"}.get(lvl,"🟢")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"### {icon} Risk Level")
        st.markdown(f"<h2 style='color:{COLORS['accent']};'>{lvl}</h2>", unsafe_allow_html=True)
        st.metric("Score", f"{risk['composite_score']}/100")
    with c2:
        st.markdown("### Sanctions Matches")
        st.metric("Count", len(result["sanctions_matches"]))
        for m in result["sanctions_matches"][:3]:
            st.write(f"**{m['entity_name']}** ({m['match_score']}%) — {m['country']}")
    with c3:
        st.markdown("### Adverse Media")
        st.metric("Count", len(result["media_results"]))
        for a in result["media_results"][:3]:
            tags = ", ".join(a.get("tags", []))
            st.write(f"**{a.get('source','')}**: {a.get('title','')[:50]}… ({tags})")

    st.markdown("---")
    st.markdown("### Detailed Findings")
    if result["sanctions_matches"]:
        st.markdown("#### Sanctions Matches")
        s_df = pd.DataFrame(result["sanctions_matches"])
        keep = [c for c in ["entity_name","country","match_score","explanation"] if c in s_df.columns]
        st.dataframe(s_df[keep], use_container_width=True)
    if result["media_results"]:
        st.markdown("#### Adverse Media")
        m_df = pd.DataFrame(result["media_results"])
        keep = [c for c in ["source","title","tags","published_date"] if c in m_df.columns]
        st.dataframe(m_df[keep], use_container_width=True)
    st.markdown("#### Risk Score Breakdown")
    bd = risk["breakdown"]
    bd_df = pd.DataFrame({
        "Component": ["Sanctions","Media","PEP"],
        "Weight":    [bd["sanctions"]["weight"], bd["media"]["weight"], bd["pep"]["weight"]],
        "Score":     [bd["sanctions"]["score"],  bd["media"]["score"],  bd["pep"]["score"]],
    })
    st.bar_chart(bd_df.set_index("Component"))

def render_footer():
    st.markdown("---")
    st.markdown(f"<div class='footer'>{FOOTER_TEXT}</div>", unsafe_allow_html=True)

# ---------------------- Entry ----------------------------
def main():
    render_header()
    name, dob, country, run, export = render_sidebar_input()

    if run:
        result = perform_screening(name, dob, country)
    # remember for export
        st.session_state["last_result"] = result
        st.session_state["last_query"] = {
        "subject_name": name,
        "dob": dob,
        "country": country
        }
        render_results(result)


    if export:
        res = st.session_state.get("last_result")
        meta = st.session_state.get("last_query", {})

        if not res:
            st.warning("Run a screening first, then export.")
        else:
            try:
                os.makedirs("exports", exist_ok=True)

                subject_name = meta.get("subject_name") or ""
                dob = meta.get("dob") or ""
                country = meta.get("country") or "Any"

                total_score = res["risk_data"]["composite_score"]
                sanctions_score = res["risk_data"]["breakdown"]["sanctions"]["score"]
                media_score = res["risk_data"]["breakdown"]["media"]["score"]
                pep_score = res["risk_data"]["breakdown"]["pep"]["score"]
                matches = res.get("sanctions_matches", [])
                media_hits = res.get("media_results", [])

                ofac_date_str = datetime.utcnow().strftime("%Y-%m-%d")
                safe_name = re.sub(r"[^A-Za-z0-9_-]+", "_", (subject_name or "subject"))
                ts = datetime.now().strftime("%Y%m%d-%H%M%S")

                report = {
                    "subject": subject_name,
                    "dob": dob,
                    "country": country,
                    "score": total_score,
                    "components": {
                        "sanctions": sanctions_score,
                        "pep": pep_score,
                        "media": media_score
                    },
                    "sanctions_matches": matches,
                    "media_hits": media_hits,
                    "generated_at": datetime.utcnow().isoformat(),
                    "ofac_snapshot_date": ofac_date_str,
                }

                path = f"exports/audit_{safe_name}_{ts}.json"
                with open(path, "w") as f:
                    json.dump(report, f, indent=2, default=str)

                st.success(f"Audit exported: {path}")
                st.download_button(
                    label="Download Audit Report (JSON)",
                    data=json.dumps(report, indent=2),
                    file_name=f"audit_{safe_name}_{ts}.json",
                    mime="application/json",
                )
            except Exception as e:
                st.error(f"Audit export failed: {e}")


    render_footer()

if __name__ == "__main__":
    main()
