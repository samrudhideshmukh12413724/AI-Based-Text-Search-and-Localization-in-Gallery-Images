"""SQLite storage for image names, paths, and extracted OCR text."""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
DB_PATH = ROOT_DIR / "database" / "images.db"


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                image_name TEXT NOT NULL,
                image_path TEXT NOT NULL UNIQUE,
                extracted_text TEXT NOT NULL,
                original_ocr_text TEXT DEFAULT '',
                cleaned_text TEXT DEFAULT '',
                category TEXT DEFAULT '',
                created_at TEXT NOT NULL
            )
            """
        )
        # Migrate existing tables if columns are missing
        columns = [col[1] for col in conn.execute("PRAGMA table_info(images)").fetchall()]
        if "original_ocr_text" not in columns:
            conn.execute("ALTER TABLE images ADD COLUMN original_ocr_text TEXT DEFAULT ''")
        if "cleaned_text" not in columns:
            conn.execute("ALTER TABLE images ADD COLUMN cleaned_text TEXT DEFAULT ''")
        if "category" not in columns:
            conn.execute("ALTER TABLE images ADD COLUMN category TEXT DEFAULT ''")
        conn.commit()


def save_image(
    image_name: str,
    image_path: str,
    extracted_text: str,
    original_ocr_text: str = "",
    cleaned_text: str = "",
    category: str = "",
) -> dict:
    created_at = datetime.now(timezone.utc).isoformat()
    orig = original_ocr_text or extracted_text
    cleaned = cleaned_text or extracted_text
    with _connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO images (image_name, image_path, extracted_text, original_ocr_text, cleaned_text, category, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(image_path) DO UPDATE SET
                image_name = excluded.image_name,
                extracted_text = excluded.extracted_text,
                original_ocr_text = excluded.original_ocr_text,
                cleaned_text = excluded.cleaned_text,
                category = excluded.category,
                created_at = excluded.created_at
            """,
            (image_name, image_path, extracted_text, orig, cleaned, category, created_at),
        )
        conn.commit()
        row_id = cursor.lastrowid
        if row_id == 0:
            row = conn.execute(
                "SELECT id FROM images WHERE image_path = ?", (image_path,)
            ).fetchone()
            row_id = row["id"]

    return get_image_by_id(row_id)


def get_image_by_id(image_id: int) -> dict | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM images WHERE id = ?", (image_id,)).fetchone()
    return dict(row) if row else None


def list_images() -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM images ORDER BY created_at DESC"
        ).fetchall()
    return [dict(row) for row in rows]


def search_by_keyword(query: str) -> list[dict]:
    pattern = f"%{query.strip().lower()}%"
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM images
            WHERE LOWER(extracted_text) LIKE ? OR LOWER(image_name) LIKE ?
            ORDER BY created_at DESC
            """,
            (pattern, pattern),
        ).fetchall()
    return [dict(row) for row in rows]
