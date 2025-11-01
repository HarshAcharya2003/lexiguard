"""
LexiGuard Configuration Module
Central configuration and constants for the sanctions screening engine.
"""
import os
from pathlib import Path

# Project structure
PROJECT_ROOT = Path(__file__).parent.parent
APP_DIR = PROJECT_ROOT / "app"
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "lexiguard.db"

# Create directories if they don't exist
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Color palette
COLORS = {
    "primary": "#0B1220",      # Deep navy background
    "secondary": "#E6EAF2",    # Refined off-white text
    "accent": "#BD9468",       # Copper accent
    "text_muted": "#9AA4B2",   # Muted grey
    "border": "#1A2433",       # Subtle panel/border
    "success": "#31C48D",
    "warning": "#F4B740",
    "danger": "#F97066",
}



# Risk thresholds
RISK_THRESHOLDS = {
    "HIGH": 75,
    "MEDIUM": 40,
    "LOW": 0,
}

# Fuzzy matching
FUZZY_MATCH_THRESHOLD = 80
FUZZY_PARTIAL_RATIO_THRESHOLD = 75

# OFAC data source
OFAC_URL = "https://www.treasury.gov/ofac/downloads/sdnlist.csv"
OFAC_CACHE_HOURS = 24

# RSS sources for adverse media
RSS_SOURCES = [
    {
        "name": "Reuters",
        "url": "https://www.reuters.com/finance",
        "category": "finance",
    },
    {
        "name": "Economic Times",
        "url": "https://economictimes.indiatimes.com/news",
        "category": "business",
    },
]

# Risk scoring weights
RISK_WEIGHTS = {
    "sanctions_match": 0.6,
    "adverse_media": 0.3,
    "pep_flag": 0.1,
}

# Media recency factor (days)
MEDIA_RECENCY_FACTOR = 30

# Audit settings
AUDIT_RETENTION_DAYS = 365

# Footer text
FOOTER_TEXT = "© 2025 LexiGuard — Created by Harsh Acharya"
