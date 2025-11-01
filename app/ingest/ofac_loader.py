# app/ingest/ofac_loader.py
from __future__ import annotations
import io, re
from pathlib import Path
from typing import Optional, Sequence
import pandas as pd
import requests
from app.config import DB_PATH

# ---- Endpoints to try, in order (OFAC keeps moving) ----
OFAC_URLS = [
    "https://files.ofac.treasury.gov/sanctions/SDN.csv",                 # current prod
    "https://sanctionslist.ofac.treasury.gov/SDN.csv",                   # new subdomain (DNS rollout)
    "https://ofac.treasury.gov/media/57671/download?inline",             # media CDN
    "https://www.treasury.gov/ofac/downloads/sdn.csv",                   # legacy
]

# ---- Minimal built-in fallback for offline/demo ----
SAMPLE_SDN_CSV = """sdn_name,program,sdn_type,dob,country,citizenship,nationality,remarks
PUTIN, VLADIMIR VLADIMIROVICH,RUSSIA-EO14024,Individual,1952-10-07,RUSSIA,RUSSIA,RUSSIAN,Demo row for matching
KIM, JONG UN,NPWMD,Individual,1984-01-08,KOREA, NORTH,KOREA, NORTH,Demo row for matching
LUKASHENKO, ALEKSANDR GRIGORYEVICH,BELARUS,Individual,1954-08-30,BELARUS,BELARUS,BELARUSIAN,Demo row for matching
ISLAMIC REVOLUTIONARY GUARD CORPS (IRGC),IRAN,Entity,,IRAN,IRAN,IRAN,Demo row for matching
ROSNEFT OIL COMPANY,RUSSIA-EO14024,Entity,,RUSSIA,RUSSIA,RUSSIAN,Demo row for matching
"""

# Ensure data dir exists
Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)

# ---------- CSV loader with multi-source + local + built-in fallback ----------
def load_ofac_csv(local_path: Optional[str] = None) -> pd.DataFrame:
    """
    Returns a DataFrame with the SDN CSV.
    1) If local_path exists -> use it.
    2) Else try official OFAC URLs (in order).
    3) Else use built-in SAMPLE_SDN_CSV so demo keeps working.
    Also auto-fixes headerless/garbled CSV by promoting a header row when needed.
    """
    text: str

    # 1) local file
    if local_path and Path(local_path).exists():
        text = Path(local_path).read_text(encoding="utf-8", errors="ignore")
        return _parse_with_header_fallback(text)

    # 2) official endpoints
    for url in OFAC_URLS:
        try:
            text = _http_get_text(url)
            df = _parse_with_header_fallback(text)
            if df.shape[1] >= 4:
                return df
        except Exception:
            continue  # try next

    # 3) built-in sample (guarantees demo works)
    return pd.read_csv(io.StringIO(SAMPLE_SDN_CSV), dtype=str, keep_default_na=False)

def _http_get_text(url: str) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18 Safari/605.1.15",
        "Accept": "text/csv,*/*;q=0.8",
        "Connection": "keep-alive",
    }
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    return r.text

def _parse_with_header_fallback(text: str) -> pd.DataFrame:
    # First attempt: normal CSV
    try:
        df = pd.read_csv(io.StringIO(text), dtype=str, keep_default_na=False, encoding="utf-8-sig")
        if df.shape[1] > 2:
            return df
    except Exception:
        pass

    # Fallback: headerless—find header row heuristically
    raw = pd.read_csv(io.StringIO(text), dtype=str, keep_default_na=False, header=None, encoding="utf-8-sig")
    header_hint = re.compile(r"(sdn|name|program|type|dob|date|country|national|citizen|remark)", re.I)
    header_idx = None
    for i in range(min(15, len(raw))):
        row_vals = [str(x or "") for x in raw.iloc[i].tolist()]
        if any(header_hint.search(v) for v in row_vals):
            header_idx = i
            break
    if header_idx is None:
        header_idx = 0
    header = [str(x or "").strip() for x in raw.iloc[header_idx].tolist()]
    body = raw.iloc[header_idx + 1:].copy()
    body.columns = header
    body = body.loc[:, (body != "").any(axis=0)]
    return body.reset_index(drop=True)
import re

def _clean_name(t: str) -> str:
    """
    Heuristics to extract an entity/person name from remark-heavy cells.
    - Strip leading 'Secondary sanctions risk: ...;' and similar prefixes.
    - If 'Linked To:' exists, prefer the trailing entity name.
    - If very long and has ';', keep the first plausible segment.
    - Collapse spaces and keep uppercase (OFAC style).
    """
    if not t:
        return ""
    s = str(t).strip()

    # Remove common boilerplate prefixes up to the first ';'
    s = re.sub(r"^(Secondary sanctions risk:.*?;)\s*", "", s, flags=re.I)

    # If it says "Linked To: NAME." keep the NAME portion
    m = re.search(r"Linked To:\s*([^.;]+)", s, flags=re.I)
    if m:
        s = m.group(1).strip()

    # If it's still very long, pick the first semicolon-separated chunk
    if len(s) > 120 and ";" in s:
        first = s.split(";", 1)[0].strip()
        # Keep the shorter if the first part looks like a name
        if len(first) >= 3:
            s = first

    # Normalize whitespace, keep OFAC caps style
    s = re.sub(r"\s+", " ", s).strip()
    return s.upper()


# ---------- Normalization + store ----------
def normalize_and_store(df: pd.DataFrame) -> int:
    import sqlite3

    # normalize headers
    df = df.rename(columns=lambda c: str(c).strip().lower().replace(" ", "_").replace("-", "_"))

    # choose name column or synthesize per-row best
    if "sdn_name" in df.columns:
        name_series = df["sdn_name"].astype(str).str.strip()
        name_series = name_series.apply(_clean_name)

    else:
        name_like = [c for c in df.columns if "name" in c]
        if name_like:
            def best(row):
                bestv = ""
                for c in name_like:
                    v = str(row.get(c, "") or "").strip()
                    if len(v) > len(bestv):
                        bestv = v
                return bestv
            name_series = df.apply(best, axis=1).astype(str).str.strip()
            name_series = name_series.apply(_clean_name)

        else:
            # worst case: pick most "lettery" cell per row (handles weird spreadsheets)
            def lettery(row):
                bestv = ""
                bests = -1
                for v in row.values:
                    t = str(v or "")
                    score = sum(ch.isalpha() for ch in t) + t.count(",") + t.count("'")
                    if score > bests:
                        bests = score; bestv = t
                return bestv.strip()
            name_series = df.apply(lettery, axis=1).astype(str).str.strip()
            name_series = name_series.apply(_clean_name)


    def series(*cands):
        for c in [x.strip().lower().replace(" ", "_").replace("-", "_") for x in cands]:
            if c in df.columns:
                return df[c].astype(str)
        return pd.Series([""] * len(df))

    norm = pd.DataFrame({
        "name":        name_series,
        "program":     series("program", "program_list"),
        "sdn_type":    series("sdn_type", "type"),
        "dob":         series("dob", "date_of_birth", "date_of_birth_list"),
        "country":     series("country", "primary_country", "nationality", "citizenship_country"),
        "citizenship": series("citizenship"),
        "nationality": series("nationality"),
        "remarks":     series("remarks", "comment"),
    })
    for c in norm.columns:
        norm[c] = norm[c].fillna("").astype(str).str.strip()

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS sanctions_entities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            program TEXT,
            sdn_type TEXT,
            dob TEXT,
            country TEXT,
            citizenship TEXT,
            nationality TEXT,
            remarks TEXT
        );
        DELETE FROM sanctions_entities;
    """)
    cur.executemany("""
        INSERT INTO sanctions_entities
        (name, program, sdn_type, dob, country, citizenship, nationality, remarks)
        VALUES (?,?,?,?,?,?,?,?)
    """, [
        (
            r["name"], r["program"], r["sdn_type"], r["dob"],
            r["country"], r["citizenship"], r["nationality"], r["remarks"]
        )
        for _, r in norm.iterrows()
    ])
    con.commit()
    con.close()
    return len(norm)

if __name__ == "__main__":
    df = load_ofac_csv()        # tries URLs -> local -> built-in sample
    n = normalize_and_store(df)
    print(f"✅ Stored {n:,} rows into {DB_PATH}")
# --- Backward-compat shim so old UI imports keep working ---
# --- Backward-compat shim for UI expecting a class interface ---
class OFACLoader:
    """Shim class so old UI code using OFACLoader() still works."""

    @staticmethod
    def load_data(local_path: str | None = None):
        """Return the DataFrame from OFAC SDN CSV."""
        return load_ofac_csv(local_path)

    @staticmethod
    def load(local_path: str | None = None):
        """Alias for load_data, for flexibility."""
        return load_ofac_csv(local_path)

    @staticmethod
    def normalize_and_store(df):
        """Normalize and store DF into the SQLite database."""
        return globals()["normalize_and_store"](df)

    @staticmethod
    def ensure_db(local_path: str | None = None):
        """Ensure DB exists and is populated."""
        df = load_ofac_csv(local_path)
        return globals()["normalize_and_store"](df)
