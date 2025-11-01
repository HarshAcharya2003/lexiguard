"""
Risk Scoring Engine
Calculates composite risk scores from sanctions and media evidence.
"""
import sqlite3
from datetime import datetime, timedelta
from app.config import DB_PATH, RISK_WEIGHTS, MEDIA_RECENCY_FACTOR, RISK_THRESHOLDS


class RiskScorer:
    """Calculates risk scores for screening results."""

    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path

    def score_screening(self, sanctions_matches, media_results, pep_flag=False):
        """
        Calculate composite risk score.
        Returns score (0-100) and risk level (HIGH/MEDIUM/LOW).
        """
        sanctions_score = self._score_sanctions(sanctions_matches)
        media_score = self._score_media(media_results)
        pep_score = 20 if pep_flag else 0

        # Weighted average
        composite_score = (
            sanctions_score * RISK_WEIGHTS["sanctions_match"]
            + media_score * RISK_WEIGHTS["adverse_media"]
            + pep_score * RISK_WEIGHTS["pep_flag"]
        )

        composite_score = min(100, max(0, composite_score))

        risk_level = self._determine_risk_level(composite_score)

        return {
            "composite_score": round(composite_score, 2),
            "risk_level": risk_level,
            "sanctions_score": round(sanctions_score, 2),
            "media_score": round(media_score, 2),
            "pep_score": round(pep_score, 2),
            "breakdown": {
                "sanctions": {
                    "weight": RISK_WEIGHTS["sanctions_match"],
                    "score": round(sanctions_score, 2),
                },
                "media": {
                    "weight": RISK_WEIGHTS["adverse_media"],
                    "score": round(media_score, 2),
                },
                "pep": {"weight": RISK_WEIGHTS["pep_flag"], "score": round(pep_score, 2)},
            },
        }

    def _score_sanctions(self, matches):
        """Score based on sanctions matches."""
        if not matches:
            return 0

        # Best match score scaled to 0-100
        best_match = max(m["match_score"] for m in matches)
        return best_match

    def _score_media(self, media_items):
        """Score based on adverse media evidence."""
        if not media_items:
            return 0

        # Weight by source tier and recency
        score = 0
        for media in media_items:
            base_score = 30

            # Boost for high-risk tags
            high_risk_tags = {"sanctions", "crime", "fraud"}
            if any(tag in high_risk_tags for tag in media.get("tags", [])):
                base_score = 50

            # Apply recency decay
            recency_factor = self._recency_decay(media.get("published_date"))
            score += base_score * recency_factor

        # Cap at 100
        return min(100, score / len(media_items) if media_items else 0)

    def _recency_decay(self, date_str):
        """Calculate decay factor based on publication date."""
        if not date_str:
            return 0.5

        try:
            pub_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            days_old = (datetime.utcnow() - pub_date).days
            decay = 1 - (days_old / MEDIA_RECENCY_FACTOR)
            return max(0.1, min(1.0, decay))
        except:
            return 0.5

    def _determine_risk_level(self, score):
        """Determine risk level from numerical score."""
        if score >= RISK_THRESHOLDS["HIGH"]:
            return "HIGH"
        elif score >= RISK_THRESHOLDS["MEDIUM"]:
            return "MEDIUM"
        else:
            return "LOW"

    def generate_risk_explanation(self, risk_data):
        """Generate human-readable risk explanation."""
        level = risk_data["risk_level"]
        score = risk_data["composite_score"]

        if level == "HIGH":
            return f"High-risk profile (score: {score}/100). Immediate escalation recommended."
        elif level == "MEDIUM":
            return f"Medium-risk profile (score: {score}/100). Further investigation advised."
        else:
            return f"Low-risk profile (score: {score}/100). Screening completed."
