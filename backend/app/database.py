"""SQLite storage for image names, paths, extracted OCR text, Phase 3 visual object metadata, and Phase 3B visual region embeddings."""

import json
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
                has_visual_objects INTEGER DEFAULT 0,
                visual_metadata TEXT DEFAULT '{}',
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
        if "has_visual_objects" not in columns:
            conn.execute("ALTER TABLE images ADD COLUMN has_visual_objects INTEGER DEFAULT 0")
        if "entities_json" not in columns:
            conn.execute("ALTER TABLE images ADD COLUMN entities_json TEXT DEFAULT '{}'")
        if "file_size_bytes" not in columns:
            conn.execute("ALTER TABLE images ADD COLUMN file_size_bytes INTEGER DEFAULT 0")
        if "image_width" not in columns:
            conn.execute("ALTER TABLE images ADD COLUMN image_width INTEGER DEFAULT 0")
        if "image_height" not in columns:
            conn.execute("ALTER TABLE images ADD COLUMN image_height INTEGER DEFAULT 0")
        if "file_format" not in columns:
            conn.execute("ALTER TABLE images ADD COLUMN file_format TEXT DEFAULT ''")
        if "file_modified_at" not in columns:
            conn.execute("ALTER TABLE images ADD COLUMN file_modified_at TEXT DEFAULT ''")
        if "exif_created_at" not in columns:
            conn.execute("ALTER TABLE images ADD COLUMN exif_created_at TEXT DEFAULT ''")
        if "primary_date" not in columns:
            conn.execute("ALTER TABLE images ADD COLUMN primary_date TEXT DEFAULT ''")
        if "sha256_hash" not in columns:
            conn.execute("ALTER TABLE images ADD COLUMN sha256_hash TEXT DEFAULT ''")
        if "phash" not in columns:
            conn.execute("ALTER TABLE images ADD COLUMN phash TEXT DEFAULT ''")
        if "is_duplicate" not in columns:
            conn.execute("ALTER TABLE images ADD COLUMN is_duplicate INTEGER DEFAULT 0")
        if "canonical_image_id" not in columns:
            conn.execute("ALTER TABLE images ADD COLUMN canonical_image_id INTEGER DEFAULT NULL")
        if "duplicate_similarity" not in columns:
            conn.execute("ALTER TABLE images ADD COLUMN duplicate_similarity REAL DEFAULT 0.0")
        if "duplicate_match_type" not in columns:
            conn.execute("ALTER TABLE images ADD COLUMN duplicate_match_type TEXT DEFAULT ''")
        if "blip_caption" not in columns:
            conn.execute("ALTER TABLE images ADD COLUMN blip_caption TEXT DEFAULT ''")
        if "qr_payload" not in columns:
            conn.execute("ALTER TABLE images ADD COLUMN qr_payload TEXT DEFAULT ''")
        if "stego_payload" not in columns:
            conn.execute("ALTER TABLE images ADD COLUMN stego_payload TEXT DEFAULT ''")

        # Indexes for fast lookup
        conn.execute("CREATE INDEX IF NOT EXISTS idx_images_phash ON images(phash)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_images_sha256 ON images(sha256_hash)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_images_canonical ON images(canonical_image_id)")

        # Phase 3B: Visual Regions & Embeddings Table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS visual_regions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                image_id INTEGER NOT NULL,
                image_name TEXT NOT NULL,
                region_source TEXT NOT NULL,
                location_desc TEXT NOT NULL,
                bbox_json TEXT NOT NULL,
                norm_bbox_json TEXT NOT NULL,
                embedding_blob BLOB NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(image_id) REFERENCES images(id)
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_visual_regions_image_id ON visual_regions(image_id)")

        # Phase 4 Step 6: Cross-Image Relationships Table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS image_relationships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_image_id INTEGER NOT NULL,
                target_image_id INTEGER NOT NULL,
                relationship_type TEXT NOT NULL,
                confidence_score REAL NOT NULL,
                evidence TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(source_image_id) REFERENCES images(id) ON DELETE CASCADE,
                FOREIGN KEY(target_image_id) REFERENCES images(id) ON DELETE CASCADE,
                UNIQUE(source_image_id, target_image_id, relationship_type, evidence)
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_relationships_source ON image_relationships(source_image_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_relationships_target ON image_relationships(target_image_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_relationships_type ON image_relationships(relationship_type)")
        conn.commit()


def _parse_row(row: sqlite3.Row | None) -> dict | None:
    if row is None:
        return None
    d = dict(row)
    # Parse visual_metadata if it is a JSON string
    v_raw = d.get("visual_metadata", "{}")
    if isinstance(v_raw, str):
        try:
            d["visual_metadata"] = json.loads(v_raw) if v_raw else {}
        except Exception:
            d["visual_metadata"] = {}

    # Parse entities_json if present
    e_raw = d.get("entities_json", "{}")
    if isinstance(e_raw, str):
        try:
            d["entities"] = json.loads(e_raw) if e_raw else {}
        except Exception:
            d["entities"] = {}
    return d


def save_image(
    image_name: str,
    image_path: str,
    extracted_text: str,
    original_ocr_text: str = "",
    cleaned_text: str = "",
    category: str = "",
    has_visual_objects: int = 0,
    visual_metadata: str | dict = "{}",
    entities: str | dict = "{}",
) -> dict:
    created_at = datetime.now(timezone.utc).isoformat()
    orig = original_ocr_text or extracted_text
    cleaned = cleaned_text or extracted_text
    v_meta_str = json.dumps(visual_metadata) if isinstance(visual_metadata, dict) else (visual_metadata or "{}")
    ent_str = json.dumps(entities) if isinstance(entities, dict) else (entities or "{}")

    with _connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO images (
                image_name, image_path, extracted_text, original_ocr_text, 
                cleaned_text, category, has_visual_objects, visual_metadata, entities_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(image_path) DO UPDATE SET
                image_name = excluded.image_name,
                extracted_text = excluded.extracted_text,
                original_ocr_text = excluded.original_ocr_text,
                cleaned_text = excluded.cleaned_text,
                category = excluded.category,
                has_visual_objects = excluded.has_visual_objects,
                visual_metadata = excluded.visual_metadata,
                entities_json = excluded.entities_json,
                created_at = excluded.created_at
            """,
            (image_name, image_path, extracted_text, orig, cleaned, category, has_visual_objects, v_meta_str, ent_str, created_at),
        )
        conn.commit()
        row_id = cursor.lastrowid
        if row_id == 0:
            row = conn.execute(
                "SELECT id FROM images WHERE image_path = ?", (image_path,)
            ).fetchone()
            row_id = row["id"]

    return get_image_by_id(row_id)


def update_image_entities(image_id: int, entities: dict | str) -> None:
    """Updates entities_json for a specific image row."""
    ent_str = json.dumps(entities) if isinstance(entities, dict) else (entities or "{}")
    with _connect() as conn:
        conn.execute("UPDATE images SET entities_json = ? WHERE id = ?", (ent_str, image_id))
        conn.commit()


def get_image_entities(image_id: int) -> dict:
    """Retrieves parsed entities dictionary for an image ID."""
    with _connect() as conn:
        row = conn.execute("SELECT entities_json FROM images WHERE id = ?", (image_id,)).fetchone()
        if row and row["entities_json"]:
            try:
                return json.loads(row["entities_json"])
            except Exception:
                return {}
    return {}


def update_image_metadata(
    image_id: int,
    file_size_bytes: int = 0,
    image_width: int = 0,
    image_height: int = 0,
    file_format: str = "",
    file_modified_at: str = "",
    exif_created_at: str = "",
    primary_date: str = "",
) -> None:
    """Updates technical file and temporal metadata for an image."""
    with _connect() as conn:
        conn.execute(
            """
            UPDATE images SET
                file_size_bytes = COALESCE(NULLIF(?, 0), file_size_bytes),
                image_width = COALESCE(NULLIF(?, 0), image_width),
                image_height = COALESCE(NULLIF(?, 0), image_height),
                file_format = COALESCE(NULLIF(?, ''), file_format),
                file_modified_at = COALESCE(NULLIF(?, ''), file_modified_at),
                exif_created_at = COALESCE(NULLIF(?, ''), exif_created_at),
                primary_date = COALESCE(NULLIF(?, ''), primary_date)
            WHERE id = ?
            """,
            (file_size_bytes, image_width, image_height, file_format, file_modified_at, exif_created_at, primary_date, image_id),
        )
        conn.commit()


def update_multimodal_payloads(
    image_id: int,
    blip_caption: str = "",
    qr_payload: str = "",
    stego_payload: str = "",
) -> None:
    """Updates BLIP caption, QR payload, and Steganography text for an image."""
    with _connect() as conn:
        conn.execute(
            """
            UPDATE images SET
                blip_caption = COALESCE(NULLIF(?, ''), blip_caption),
                qr_payload = COALESCE(NULLIF(?, ''), qr_payload),
                stego_payload = COALESCE(NULLIF(?, ''), stego_payload)
            WHERE id = ?
            """,
            (blip_caption, qr_payload, stego_payload, image_id),
        )
        conn.commit()


def update_image_duplicates(
    image_id: int,
    sha256_hash: str = "",
    phash: str = "",
    is_duplicate: int = 0,
    canonical_image_id: int | None = None,
    duplicate_similarity: float = 0.0,
    duplicate_match_type: str = "",
) -> None:
    """Updates duplicate detection metadata for an image."""
    with _connect() as conn:
        conn.execute(
            """
            UPDATE images SET
                sha256_hash = COALESCE(NULLIF(?, ''), sha256_hash),
                phash = COALESCE(NULLIF(?, ''), phash),
                is_duplicate = ?,
                canonical_image_id = ?,
                duplicate_similarity = ?,
                duplicate_match_type = ?
            WHERE id = ?
            """,
            (sha256_hash, phash, is_duplicate, canonical_image_id, duplicate_similarity, duplicate_match_type, image_id),
        )
        conn.commit()


def get_image_by_id(image_id: int) -> dict | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM images WHERE id = ?", (image_id,)).fetchone()
    return _parse_row(row)


def list_images() -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM images ORDER BY created_at DESC"
        ).fetchall()
    return [_parse_row(row) for row in rows if row is not None]


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
    return [_parse_row(row) for row in rows if row is not None]


def search_by_visual(has_objects: bool = True) -> list[dict]:
    """Retrieve all documents that contain detected visual sub-objects."""
    val = 1 if has_objects else 0
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM images
            WHERE has_visual_objects = ?
            ORDER BY created_at DESC
            """,
            (val,),
        ).fetchall()
    return [_parse_row(row) for row in rows if row is not None]


# -----------------------------------------------------------------------------
# Phase 3B Visual Regions & Embeddings Storage Helpers
# -----------------------------------------------------------------------------
def save_visual_regions(image_id: int, image_name: str, regions: list[dict]) -> None:
    """Stores multiple visual region bounding boxes and embedding vectors for an image."""
    created_at = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        # Clear existing regions for this image_id
        conn.execute("DELETE FROM visual_regions WHERE image_id = ?", (image_id,))
        for r in regions:
            conn.execute(
                """
                INSERT INTO visual_regions (
                    image_id, image_name, region_source, location_desc,
                    bbox_json, norm_bbox_json, embedding_blob, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    image_id,
                    image_name,
                    r["source"],
                    r["location_desc"],
                    json.dumps(r["bbox"]),
                    json.dumps(r["normalized_bbox"]),
                    r["embedding_blob"],
                    created_at,
                ),
            )
        conn.commit()


def get_all_visual_regions() -> list[dict]:
    """Retrieves all visual regions with embeddings and associated image paths."""
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT vr.*, img.image_path, img.extracted_text, img.category
            FROM visual_regions vr
            JOIN images img ON vr.image_id = img.id
            """
        ).fetchall()

    results = []
    for r in rows:
        d = dict(r)
        d["bbox"] = json.loads(d["bbox_json"]) if d.get("bbox_json") else {}
        d["normalized_bbox"] = json.loads(d["norm_bbox_json"]) if d.get("norm_bbox_json") else {}
        results.append(d)
    return results


# -----------------------------------------------------------------------------
# Phase 4 Step 6: Cross-Image Relationships Storage Helpers
# -----------------------------------------------------------------------------
def save_relationship(
    source_image_id: int,
    target_image_id: int,
    relationship_type: str,
    confidence_score: float,
    evidence: str,
    bidirectional: bool = True,
) -> None:
    """
    Saves a cross-image relationship record.
    If bidirectional is True, stores both (source, target) and (target, source).
    """
    created_at = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO image_relationships (
                source_image_id, target_image_id, relationship_type,
                confidence_score, evidence, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (source_image_id, target_image_id, relationship_type, confidence_score, evidence, created_at),
        )
        if bidirectional and source_image_id != target_image_id:
            conn.execute(
                """
                INSERT OR IGNORE INTO image_relationships (
                    source_image_id, target_image_id, relationship_type,
                    confidence_score, evidence, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (target_image_id, source_image_id, relationship_type, confidence_score, evidence, created_at),
            )
        conn.commit()


def get_related_images(image_id: int) -> list[dict]:
    """
    Retrieves all related images for a given image_id, joined with image metadata.
    """
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT 
                r.id AS relationship_id,
                r.source_image_id,
                r.target_image_id,
                r.relationship_type,
                r.confidence_score,
                r.evidence,
                r.created_at AS relationship_created_at,
                i.image_name,
                i.image_path,
                i.category,
                i.is_duplicate,
                i.canonical_image_id
            FROM image_relationships r
            JOIN images i ON r.target_image_id = i.id
            WHERE r.source_image_id = ?
            ORDER BY r.confidence_score DESC, r.id ASC
            """,
            (image_id,),
        ).fetchall()
    return [dict(r) for r in rows if r is not None]


def get_all_relationships() -> list[dict]:
    """Retrieves all stored cross-image relationships."""
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM image_relationships
            ORDER BY id ASC
            """
        ).fetchall()
    return [dict(r) for r in rows if r is not None]


def delete_relationships_for_image(image_id: int) -> None:
    """Removes all relationships where image_id is source or target."""
    with _connect() as conn:
        conn.execute(
            "DELETE FROM image_relationships WHERE source_image_id = ? OR target_image_id = ?",
            (image_id, image_id),
        )
        conn.commit()


def clear_all_relationships() -> None:
    """Clears all relationships from image_relationships."""
    with _connect() as conn:
        conn.execute("DELETE FROM image_relationships")
        conn.commit()

