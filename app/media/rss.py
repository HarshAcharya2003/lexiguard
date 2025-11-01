"""
RSS Media Ingestion Module
Fetches and tags adverse media from RSS feeds for sanctions and fraud screening.
"""
import sqlite3
import re
from datetime import datetime
import feedparser
from app.config import DB_PATH, RSS_SOURCES


class MediaIngester:
    """Ingests and processes adverse media from RSS feeds."""

    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self.keywords = {
            "sanctions": [
                "sanctions",
                "embargo",
                "blocked",
                "SDN",
                "OFAC",
                "restricted",
            ],
            "pep": ["government", "official", "minister", "diplomat", "president"],
            "fraud": ["fraud", "embezzlement", "forgery", "scheme", "scam"],
            "crime": [
                "arrest",
                "convicted",
                "charged",
                "indictment",
                "crime",
                "criminal",
            ],
        }
        self.init_db()

    def init_db(self):
        """Initialize media database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS adverse_media (
                id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT,
                url TEXT,
                published_date TIMESTAMP,
                ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                tags TEXT
            )
        """
        )

        conn.commit()
        conn.close()

    def ingest_feeds(self):
        """Ingest all configured RSS feeds."""
        for source in RSS_SOURCES:
            self.ingest_feed(source["url"], source["name"])

    def ingest_feed(self, feed_url, source_name):
        """Ingest a single RSS feed."""
        try:
            feed = feedparser.parse(feed_url)
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            for entry in feed.entries[:50]:  # Limit to recent 50
                try:
                    article_id = entry.get("id", entry.get("link", ""))
                    if not article_id:
                        continue

                    title = entry.get("title", "")
                    content = entry.get("summary", "")
                    url = entry.get("link", "")
                    pub_date = entry.get("published", "")

                    # Tag the article
                    tags = self.tag_content(title, content)

                    cursor.execute(
                        """
                        INSERT OR IGNORE INTO adverse_media
                        (id, source, title, content, url, published_date, tags)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            article_id,
                            source_name,
                            title,
                            content,
                            url,
                            pub_date,
                            ",".join(tags),
                        ),
                    )

                except Exception as e:
                    print(f"Error processing entry: {e}")
                    continue

            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error ingesting feed {feed_url}: {e}")

    def tag_content(self, title, content):
        """Categorize content by keyword matching."""
        full_text = f"{title} {content}".lower()
        tags = []

        for category, keywords in self.keywords.items():
            for keyword in keywords:
                if re.search(rf"\b{keyword}\b", full_text):
                    tags.append(category)
                    break

        return tags if tags else ["other"]

    def search_media(self, query_name):
        """Search adverse media for mentions of a name."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Search in title and content
        cursor.execute(
            """
            SELECT id, source, title, content, url, published_date, tags
            FROM adverse_media
            WHERE title LIKE ? OR content LIKE ?
            ORDER BY published_date DESC
            LIMIT 20
        """,
            (f"%{query_name}%", f"%{query_name}%"),
        )

        results = cursor.fetchall()
        conn.close()

        media_items = []
        for row in results:
            media_items.append(
                {
                    "id": row[0],
                    "source": row[1],
                    "title": row[2],
                    "content": row[3],
                    "url": row[4],
                    "published_date": row[5],
                    "tags": row[6].split(",") if row[6] else [],
                }
            )

        return media_items

    def get_recent_media(self, hours=24, limit=20):
        """Get recent media entries."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, source, title, content, url, published_date, tags
            FROM adverse_media
            WHERE ingested_at > datetime('now', '-' || ? || ' hours')
            ORDER BY published_date DESC
            LIMIT ?
        """,
            (hours, limit),
        )

        results = cursor.fetchall()
        conn.close()

        return [
            {
                "id": row[0],
                "source": row[1],
                "title": row[2],
                "tags": row[6].split(",") if row[6] else [],
            }
            for row in results
        ]
