# LexiGuard — Sanctions & Adverse Media Terminal

An explainable sanctions screening engine with institutional-grade UI built for compliance professionals, risk analysts, and financial institutions.

## What is LexiGuard?

LexiGuard is a **terminal-style sanctions and adverse media screening platform** that combines:

- **OFAC SDN matching** with fuzzy logic to catch name variations, transliterations, and aliases
- **Adverse media ingestion** from RSS feeds (Reuters, Economic Times) tagged for fraud, crime, PEP status, and sanctions
- **Explainable risk scoring** that breaks down composite risk into components: sanctions evidence, media signals, and PEP flags
- **Audit logging** with full query history and JSON export for compliance and regulatory reviews

### Why it Matters

1. **Compliance**: Meets OFAC and AML/KYC regulatory requirements
2. **Accuracy**: Fuzzy matching catches real-world name variations that exact matching misses
3. **Transparency**: Every match and risk decision is explained—critical for appeals and audit trails
4. **Institutional Design**: Bloomberg-terminal aesthetic with deep navy, copper accents, and minimal UI—built for power users

---

## Installation & Setup

### Prerequisites
- Python 3.11+
- pip

### Local Development

\`\`\`bash
# Clone the repository
git clone https://github.com/yourusername/lexiguard.git
cd lexiguard

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r docker/requirements.txt

# (Optional) Load OFAC data
python -c "from app.ingest.ofac_loader import OFACLoader; OFACLoader().load_data()"

# Run Streamlit app
streamlit run app/ui/app_streamlit.py
\`\`\`

The app will open at `http://localhost:8501`.

---

## Docker Deployment

\`\`\`bash
# Build Docker image
docker build -t lexiguard:latest .

# Run container
docker run -p 8501:8501 lexiguard:latest
\`\`\`

Access at `http://localhost:8501`.

---

## Project Structure

\`\`\`
lexiguard/
├── app/
│   ├── ui/
│   │   ├── app_streamlit.py          # Main Streamlit app
│   │   └── theme.toml                # Streamlit theme config
│   ├── ingest/
│   │   └── ofac_loader.py            # OFAC SDN downloader and loader
│   ├── match/
│   │   └── matcher.py                # Fuzzy matching engine
│   ├── media/
│   │   └── rss.py                    # RSS adverse media ingester
│   ├── risk/
│   │   └── scorer.py                 # Risk scoring engine
│   ├── audit/
│   │   └── logger.py                 # Audit logging system
│   └── config.py                     # Central config
├── tests/
│   ├── test_matcher.py               # Matcher unit tests
│   ├── test_scorer.py                # Scorer unit tests
│   └── test_audit.py                 # Audit logger tests
├── docker/
│   └── requirements.txt               # Python dependencies
├── Dockerfile                         # Docker configuration
├── README.md                          # This file
└── data/
    └── lexiguard.db                  # SQLite database (auto-created)
\`\`\`

---

## Core Modules

### 1. OFAC Data Ingestion (`app/ingest/ofac_loader.py`)

Downloads the official OFAC SDN CSV, normalizes names (transliteration, case, whitespace), and stores in SQLite for fast querying.

**Key Methods:**
- `load_data()` — Download and cache OFAC list
- `get_entities_by_country()` — Filter entities by country
- `get_all_entities()` — Retrieve all entities with limit

### 2. Fuzzy Matching Engine (`app/match/matcher.py`)

Matches query names against OFAC entities using token-set and partial ratio algorithms from `rapidfuzz`. Explains why a match occurred.

**Key Methods:**
- `match_name(query_name, country_filter)` — Fuzzy match with optional country filter
- `explain_tokens(match)` — Token-level breakdown of match
- `_explain_match()` — Human-readable explanation

**Match Scores:**
- 95+ = Exact/near-exact match
- 80-95 = Strong similarity with word reordering
- 75-80 = Moderate similarity

### 3. Adverse Media Ingestion (`app/media/rss.py`)

Fetches RSS feeds and tags articles by keyword (sanctions, fraud, crime, PEP, other). Stores in SQLite with full article text for name searching.

**Key Methods:**
- `ingest_feeds()` — Ingest all configured RSS sources
- `tag_content()` — Keyword-based classification
- `search_media()` — Search articles for entity names

**Tag Categories:**
- **Sanctions** — OFAC, embargo, blocked, restricted
- **PEP** — Government, official, minister, diplomat
- **Fraud** — Embezzlement, forgery, scheme, scam
- **Crime** — Arrest, convicted, indictment, criminal

### 4. Risk Scoring Engine (`app/risk/scorer.py`)

Calculates composite risk score from:
- **Sanctions matches** (60% weight) — Best match score
- **Adverse media** (30% weight) — Article tags + recency decay
- **PEP flag** (10% weight) — Politically exposed person indicator

**Risk Levels:**
- **HIGH** ≥ 75 — Immediate escalation
- **MEDIUM** 40-74 — Further investigation
- **LOW** < 40 — Cleared

### 5. Audit Logging System (`app/audit/logger.py`)

Records every screening query with:
- Subject name, DOB, country
- Number of sanctions and media matches
- Final risk level and score
- Full result JSON (exportable)

**Key Methods:**
- `log_screening()` — Log a query and results
- `get_audit_log()` — Retrieve recent logs
- `export_audit_log()` — Export as JSON for compliance

---

## UI Theme

### Color Palette

- **Primary**: `#0a0f14` (Charcoal Black) — Background
- **Secondary**: `#f5f5f5` (Soft White) — Foreground text
- **Accent**: `#caa472` (Antique Gold) — Buttons, highlights, metrics
- **Muted Text**: `#8a8a8a` — Descriptive or secondary text
- **Borders**: `#1a1a1a` — Card and sidebar dividers
- **Risk Levels**:
  - 🟢 **Low Risk**: `#4CAF50`
  - 🟡 **Medium Risk**: `#FFC107`
  - 🔴 **High Risk**: `#FF5252`

### Fonts

- **Primary Font**: `Inter` — clean, modern, legible  
- **Headers**: `Space Grotesk` — geometric professional tone  
- **Code / Metrics**: `JetBrains Mono` — precision technical font  

### Design Style

Minimal shadows, subtle motion, no rounded edges.  
Feels like a private financial terminal, not a student prototype.

- Dark matte background  
- Subtle gold accents for data highlights  
- Monospace numerics for risk scores  
- Terminal-style sidebar with crisp separators  
- Consistent alignment and whitespace grid  

### Logo (Cosmetic)

The LexiGuard logo is defined in `render_logo()` inside `app/ui/app_streamlit.py`.  
It renders the **“LG” shield emblem** in antique gold over a dark circular frame.  
You can safely tweak only SVG fill colors — no functional code changes.


---

## Running Tests

\`\`\`bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app tests/

# Run specific test file
pytest tests/test_matcher.py -v
\`\`\`

---

## Configuration

Edit `app/config.py` to customize:

\`\`\`python
# OFAC data refresh frequency (hours)
OFAC_CACHE_HOURS = 24

# Fuzzy match thresholds
FUZZY_MATCH_THRESHOLD = 80
FUZZY_PARTIAL_RATIO_THRESHOLD = 75

# Risk thresholds
RISK_THRESHOLDS = {
    "HIGH": 75,
    "MEDIUM": 40,
    "LOW": 0,
}

# RSS sources for adverse media
RSS_SOURCES = [...]

# Risk scoring weights
RISK_WEIGHTS = {
    "sanctions_match": 0.6,
    "adverse_media": 0.3,
    "pep_flag": 0.1,
}
\`\`\`

---

## How to Use

### 1. **Run a Screening**
   - Enter subject name (e.g., "Vladimir Putin")
   - (Optional) Select date of birth and country
   - Click **"🔍 Run Screening"**

### 2. **Interpret Results**
   - **Risk Level**: HIGH/MEDIUM/LOW with color-coded indicator
   - **Risk Score**: 0-100 composite score with breakdown
   - **Sanctions Matches**: Name matches from OFAC SDN list
   - **Adverse Media**: Recent articles mentioning the subject
   - **Match Explanation**: Why each match was triggered

### 3. **Export Audit Trail**
   - Click **"📊 Export Audit"** to download JSON log
   - Use for compliance reviews, appeals, regulatory submissions

---
## Project Structure

lexiguard/
├── app/
│   ├── ui/                  # Streamlit UI
│   ├── ingest/              # OFAC loader
│   ├── match/               # Fuzzy matching
│   ├── media/               # Adverse media ingestion
│   ├── risk/                # Risk scoring
│   ├── audit/               # Audit logging
│   └── config.py            # Configuration
├── docker/                  # Dependencies
├── Dockerfile
└── data/                    # SQLite DB
 
---
## UI Theme 

Primary: #111d2b (Deep Navy)
Accent: #bd9468 (Copper)
Secondary: #fbf3da (Cream)
Fonts: Didact Gothic, Perandory
Aesthetic: Professional, Bloomberg-style terminal

---
## Legal Disclaimer

LexiGuard is a non-commercial educational prototype developed for research and demonstration purposes only.
It uses publicly available OFAC data and does not provide certified compliance, legal, or risk advice.
Do not use this tool for real-world client screening or regulatory submissions.
Use responsibly and verify all information independently.

---
## Acknowledgments

**Created by**: Harsh Acharya  
**Version**: 0.1.1  
**Year**: 2025

---

## License

This project is provided for educational and institutional use.

---

## Support

For issues or questions, please file an issue or reach out to the development team.
