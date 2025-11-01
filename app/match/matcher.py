# app/match/matcher.py
import sqlite3
from typing import List, Dict, Optional
from rapidfuzz import fuzz, process
from app.config import DB_PATH
from app.ingest.ofac_loader import OFACLoader  # to self-heal DB if empty

def _fetch_rows(country: Optional[str]) -> list[tuple[str, str]]:
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    if country and country.strip().upper() != "ANY":
        cur.execute(
            "SELECT name, country FROM sanctions_entities WHERE name <> '' AND UPPER(country)=?",
            (country.strip().upper(),),
        )
    else:
        cur.execute("SELECT name, country FROM sanctions_entities WHERE name <> ''")
    rows = cur.fetchall()
    con.close()
    return rows

def fuzzy_match(name_query: str, country: Optional[str] = None, top_n: int = 5, threshold: int = 70) -> List[Dict]:
    """
    Fuzzy match against sanctions_entities.name with self-healing DB and SQL fallback.
    """
    if not name_query or not name_query.strip():
        return []
    q = name_query.strip().upper()

    rows = _fetch_rows(country)
    if not rows:
        # self-heal: build DB and try again
        OFACLoader.ensure_db(None)
        rows = _fetch_rows(country)
        if not rows:
            return []

    names = [r[0] for r in rows]
    idx_map = {i: rows[i] for i in range(len(rows))}

    # RapidFuzz first (robust to order/extra tokens)
    extracted = process.extract(q, names, scorer=fuzz.token_set_ratio, limit=max(top_n, 10))
    results: List[Dict] = []
    for match_name, score, idx in extracted:
        if score >= threshold:
            nm, ctry = idx_map[idx]
            results.append({"name": match_name, "score": int(score), "country": (ctry or "")})
        if len(results) >= top_n:
            break

    # If nothing, fall back to SQL LIKE (guarantees hits for obvious queries)
    if not results:
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()
        like = f"%{q}%"
        if country and country.strip().upper() != "ANY":
            cur.execute(
                "SELECT name, country FROM sanctions_entities WHERE UPPER(name) LIKE ? AND UPPER(country)=? LIMIT ?",
                (like, country.strip().upper(), top_n),
            )
        else:
            cur.execute(
                "SELECT name, country FROM sanctions_entities WHERE UPPER(name) LIKE ? LIMIT ?",
                (like, top_n),
            )
        rows = cur.fetchall()
        con.close()
        for nm, ctry in rows:
            results.append({"name": nm, "score": 100, "country": ctry or ""})
    return results

class FuzzyMatcher:
    def __init__(self, threshold: int = 70):
        self.threshold = threshold
    def match(self, query: str, country: Optional[str] = None, top_n: int = 5) -> List[Dict]:
        return fuzzy_match(query, country=country, top_n=top_n, threshold=self.threshold)
    def search(self, query: str, country: Optional[str] = None, top_n: int = 5) -> List[Dict]:
        return self.match(query, country=country, top_n=top_n)
