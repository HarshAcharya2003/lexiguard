"""
Audit Logging System
Records all screening queries and results for compliance and auditability.
"""
import sqlite3
import json
from datetime import datetime
from app.config import DB_PATH, AUDIT_RETENTION_DAYS


class AuditLogger:
    """Logs screening queries and results for audit trail."""

    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        """Initialize audit database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_name TEXT NOT NULL,
                query_dob TEXT,
                query_country TEXT,
                sanctions_matches INTEGER,
                media_matches INTEGER,
                risk_level TEXT,
                risk_score REAL,
                query_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                result_json TEXT
            )
        """
        )

        conn.commit()
        conn.close()

    def log_screening(
        self,
        query_name,
        query_dob,
        query_country,
        sanctions_matches,
        media_matches,
        risk_level,
        risk_score,
        full_result,
    ):
        """Log a screening query and its results."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        result_json = json.dumps(full_result, default=str)

        cursor.execute(
            """
            INSERT INTO audit_logs
            (query_name, query_dob, query_country, sanctions_matches, media_matches,
             risk_level, risk_score, result_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                query_name,
                query_dob,
                query_country,
                len(sanctions_matches),
                len(media_matches),
                risk_level,
                risk_score,
                result_json,
            ),
        )

        conn.commit()
        conn.close()

    def get_audit_log(self, limit=100):
        """Retrieve audit log entries."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, query_name, query_dob, query_country, sanctions_matches,
                   media_matches, risk_level, risk_score, query_timestamp
            FROM audit_logs
            ORDER BY query_timestamp DESC
            LIMIT ?
        """,
            (limit,),
        )

        results = cursor.fetchall()
        conn.close()

        return [
            {
                "id": row[0],
                "query_name": row[1],
                "query_dob": row[2],
                "query_country": row[3],
                "sanctions_matches": row[4],
                "media_matches": row[5],
                "risk_level": row[6],
                "risk_score": row[7],
                "query_timestamp": row[8],
            }
            for row in results
        ]

    def get_audit_entry(self, log_id):
        """Retrieve detailed audit entry."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT result_json FROM audit_logs WHERE id = ?", (log_id,))
        result = cursor.fetchone()
        conn.close()

        if result:
            return json.loads(result[0])
        return None

    def export_audit_log(self, format="json"):
        """Export audit log in specified format."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, query_name, query_dob, query_country, sanctions_matches,
                   media_matches, risk_level, risk_score, query_timestamp, result_json
            FROM audit_logs
            ORDER BY query_timestamp DESC
        """
        )

        rows = cursor.fetchall()
        conn.close()

        if format == "json":
            data = [
                {
                    "id": row[0],
                    "query_name": row[1],
                    "query_dob": row[2],
                    "query_country": row[3],
                    "sanctions_matches": row[4],
                    "media_matches": row[5],
                    "risk_level": row[6],
                    "risk_score": row[7],
                    "query_timestamp": row[8],
                    "result": json.loads(row[9]),
                }
                for row in rows
            ]
            return json.dumps(data, indent=2, default=str)

        return None

    def cleanup_old_logs(self):
        """Remove audit logs older than retention period."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            DELETE FROM audit_logs
            WHERE query_timestamp < datetime('now', '-' || ? || ' days')
        """,
            (AUDIT_RETENTION_DAYS,),
        )

        conn.commit()
        conn.close()
