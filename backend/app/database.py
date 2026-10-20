"""SQLite storage for image names, paths, extracted OCR text, Phase 3 visual object metadata, and Phase 3B visual region embeddings."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
DB_PATH = ROOT_DIR / "database" / "images.db"


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=15.0)
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                hashed_password TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
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
        user_columns = [col[1] for col in conn.execute("PRAGMA table_info(users)").fetchall()]
        if "is_admin" not in user_columns:
            conn.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0")
        conn.execute("UPDATE users SET is_admin = 1 WHERE id = 1 OR username = 'alice'")

        columns = [col[1] for col in conn.execute("PRAGMA table_info(images)").fetchall()]
        if "user_id" not in columns:
            conn.execute("ALTER TABLE images ADD COLUMN user_id INTEGER DEFAULT 1")
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
        if "ocr_boxes_json" not in columns:
            conn.execute("ALTER TABLE images ADD COLUMN ocr_boxes_json TEXT DEFAULT '[]'")
        if "indexing_status" not in columns:
            conn.execute("ALTER TABLE images ADD COLUMN indexing_status TEXT DEFAULT 'completed'")
        if "is_demo" not in columns:
            conn.execute("ALTER TABLE images ADD COLUMN is_demo INTEGER DEFAULT 0")

        # Indexes for fast lookup
        conn.execute("CREATE INDEX IF NOT EXISTS idx_images_user_id ON images(user_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_images_is_demo ON images(is_demo)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_images_indexing_status ON images(indexing_status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_images_phash ON images(phash)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_images_sha256 ON images(sha256_hash)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_images_canonical ON images(canonical_image_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_images_name ON images(image_name)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_images_created ON images(created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_images_category ON images(category)")

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

    # Ensure indexing_status and is_demo fields exist
    d["indexing_status"] = d.get("indexing_status") or "completed"
    d["is_demo"] = int(d.get("is_demo") or 0)
    return d


# =============================================================================
# In-Memory Database Caching Engine (sub-millisecond retrieval)
# =============================================================================
_cached_images: list[dict] | None = None
_cached_images_by_id: dict[int, dict] | None = None
_cached_visual_regions: list[dict] | None = None


def invalidate_cache() -> None:
    """Invalidates in-memory caches on database mutations."""
    global _cached_images, _cached_images_by_id, _cached_visual_regions
    _cached_images = None
    _cached_images_by_id = None
    _cached_visual_regions = None


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
    user_id: int = 1,
    qr_payload: str = "",
    is_demo: int | None = None,
) -> dict:
    created_at = datetime.now(timezone.utc).isoformat()
    orig = original_ocr_text or extracted_text
    cleaned = cleaned_text or extracted_text
    v_meta_str = json.dumps(visual_metadata) if isinstance(visual_metadata, dict) else (visual_metadata or "{}")
    ent_str = json.dumps(entities) if isinstance(entities, dict) else (entities or "{}")
    demo_val = 1 if (is_demo is True or is_demo == 1 or (is_demo is None and user_id == 1)) else 0

    with _connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO images (
                image_name, image_path, extracted_text, original_ocr_text, 
                cleaned_text, category, has_visual_objects, visual_metadata, entities_json, created_at, user_id, qr_payload, is_demo
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(image_path) DO UPDATE SET
                image_name = excluded.image_name,
                extracted_text = excluded.extracted_text,
                original_ocr_text = excluded.original_ocr_text,
                cleaned_text = excluded.cleaned_text,
                category = excluded.category,
                has_visual_objects = excluded.has_visual_objects,
                visual_metadata = excluded.visual_metadata,
                entities_json = excluded.entities_json,
                created_at = excluded.created_at,
                user_id = excluded.user_id,
                qr_payload = CASE WHEN excluded.qr_payload != '' THEN excluded.qr_payload ELSE images.qr_payload END,
                is_demo = excluded.is_demo
            """,
            (image_name, image_path, extracted_text, orig, cleaned, category, has_visual_objects, v_meta_str, ent_str, created_at, user_id, qr_payload, demo_val),
        )
        conn.commit()
        invalidate_cache()
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
        invalidate_cache()


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
        invalidate_cache()


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
        invalidate_cache()


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
        invalidate_cache()


def _assemble_searchable_text(row: dict) -> str:
    ent = row.get("entities") or {}
    urls_str = " ".join(ent.get("urls", [])) if isinstance(ent, dict) else ""
    v_meta = row.get("visual_metadata") or {}
    if isinstance(v_meta, str):
        try:
            v_meta = json.loads(v_meta)
        except Exception:
            v_meta = {}

    vis_tokens = []
    has_vis = bool(row.get("has_visual_objects")) or (isinstance(v_meta, dict) and v_meta.get("detected"))
    has_qr = bool(row.get("qr_payload") and row.get("qr_payload").strip())
    if has_vis or has_qr or (isinstance(v_meta, dict) and v_meta.get("type") == "qr_code"):
        vis_tokens.extend(["qr", "qrcode", "qr_code", "barcode", "visual_object"])

    if isinstance(v_meta, dict):
        if v_meta.get("type"):
            vis_tokens.append(str(v_meta.get("type")))
        for obj in v_meta.get("objects", []):
            if isinstance(obj, dict):
                vis_tokens.append(str(obj.get("label", "")))
                vis_tokens.append(str(obj.get("type", "")))
                vis_tokens.append(str(obj.get("data", "")))

    vis_str = " ".join(t for t in vis_tokens if t)
    cat_str = str(row.get("category", ""))
    return f"{row.get('extracted_text', '')} {row.get('cleaned_text', '')} {row.get('blip_caption', '')} {row.get('qr_payload', '')} {row.get('stego_payload', '')} {urls_str} {vis_str} {cat_str}".strip()


def _load_all_images_to_cache() -> None:
    global _cached_images, _cached_images_by_id
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM images ORDER BY created_at DESC").fetchall()
    parsed = []
    by_id = {}
    for r in rows:
        if r is not None:
            d = _parse_row(r)
            d["searchable_text"] = _assemble_searchable_text(d)
            parsed.append(d)
            by_id[d["id"]] = d
    _cached_images = parsed
    _cached_images_by_id = by_id


def get_image_by_id(image_id: int, user_id: int | None = None) -> dict | None:
    global _cached_images_by_id
    if _cached_images_by_id is None:
        _load_all_images_to_cache()
    if _cached_images_by_id is not None and image_id in _cached_images_by_id:
        row = _cached_images_by_id[image_id]
        if user_id is None or row.get("user_id", 1) == user_id:
            return row
        return None

    with _connect() as conn:
        if user_id is not None:
            row = conn.execute("SELECT * FROM images WHERE id = ? AND user_id = ?", (image_id, user_id)).fetchone()
        else:
            row = conn.execute("SELECT * FROM images WHERE id = ?", (image_id,)).fetchone()
    return _parse_row(row)


get_image = get_image_by_id


def list_images(user_id: int | None = None) -> list[dict]:
    global _cached_images
    if _cached_images is None:
        _load_all_images_to_cache()

    if user_id == 1:
        return [r for r in _cached_images if r.get("user_id", 1) == 1 and r.get("is_demo") == 1]
    elif user_id is not None:
        return [r for r in _cached_images if r.get("user_id", 1) == user_id]
    else:
        return list(_cached_images)


def search_by_keyword(query: str, user_id: int | None = None) -> list[dict]:
    pattern = f"%{query.strip().lower()}%"
    with _connect() as conn:
        if user_id is not None:
            rows = conn.execute(
                """
                SELECT * FROM images
                WHERE (LOWER(extracted_text) LIKE ? OR LOWER(image_name) LIKE ? OR LOWER(qr_payload) LIKE ?) AND user_id = ?
                ORDER BY created_at DESC
                """,
                (pattern, pattern, pattern, user_id),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT * FROM images
                WHERE LOWER(extracted_text) LIKE ? OR LOWER(image_name) LIKE ? OR LOWER(qr_payload) LIKE ?
                ORDER BY created_at DESC
                """,
                (pattern, pattern, pattern),
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
        invalidate_cache()


def get_all_visual_regions() -> list[dict]:
    """Retrieves all visual regions with embeddings and associated image paths (cached in RAM)."""
    global _cached_visual_regions
    if _cached_visual_regions is not None:
        return list(_cached_visual_regions)

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
    _cached_visual_regions = results
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


def create_user(username: str, hashed_password: str, is_admin: int = 0) -> dict:
    """Creates a new user record in SQLite with role-based access attributes."""
    created_at = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO users (username, hashed_password, is_admin, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (username, hashed_password, 1 if is_admin else 0, created_at),
        )
        conn.commit()
        user_id = cursor.lastrowid
    return {"id": user_id, "username": username, "is_admin": bool(is_admin), "created_at": created_at}


def get_user_by_username(username: str) -> dict | None:
    """Fetches a user record by username."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,),
        ).fetchone()
    if not row:
        return None
    d = dict(row)
    d["is_admin"] = bool(d.get("is_admin", 0))
    return d


def get_user_by_id(user_id: int) -> dict | None:
    """Fetches a user record by user_id."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    if not row:
        return None
    d = dict(row)
    d["is_admin"] = bool(d.get("is_admin", 0))
    return d


def list_users() -> list[dict]:
    """Returns a list of registered users for multi-tenant switching and UI selection."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, username, is_admin, created_at FROM users ORDER BY id ASC"
        ).fetchall()
    res = []
    for r in rows:
        d = dict(r)
        d["is_admin"] = bool(d.get("is_admin", 0))
        res.append(d)
    return res


def update_image_ocr_boxes(image_id: int, word_boxes: list | str) -> None:
    """Stores OCR word bounding boxes JSON for an image ID."""
    box_str = json.dumps(word_boxes) if isinstance(word_boxes, list) else (word_boxes or "[]")
    with _connect() as conn:
        conn.execute("UPDATE images SET ocr_boxes_json = ? WHERE id = ?", (box_str, image_id))
        conn.commit()
        invalidate_cache()


def get_image_ocr_boxes(image_id: int) -> list[dict]:
    """Retrieves OCR word bounding boxes list for an image ID."""
    with _connect() as conn:
        row = conn.execute("SELECT ocr_boxes_json FROM images WHERE id = ?", (image_id,)).fetchone()
        if row and row["ocr_boxes_json"]:
            try:
                return json.loads(row["ocr_boxes_json"])
            except Exception:
                return []
    return []


def update_image_text(image_id: int, extracted_text: str, original_ocr_text: str = "", cleaned_text: str = "") -> None:
    """Updates extracted_text, original_ocr_text, and cleaned_text for an image ID."""
    orig = original_ocr_text or extracted_text
    cleaned = cleaned_text or extracted_text
    with _connect() as conn:
        conn.execute(
            """
            UPDATE images SET
                extracted_text = ?,
                original_ocr_text = ?,
                cleaned_text = ?
            WHERE id = ?
            """,
            (extracted_text, orig, cleaned, image_id),
        )
        conn.commit()
        invalidate_cache()


def update_image_ocr_text(image_id: int, extracted_text: str, original_ocr_text: str = "", cleaned_text: str = "") -> None:
    """Alias for update_image_text."""
    update_image_text(image_id, extracted_text, original_ocr_text, cleaned_text)


def update_image_indexing_status(image_id: int, status: str) -> None:
    """Updates the background indexing status: queued, indexing, completed, failed."""
    with _connect() as conn:
        conn.execute("UPDATE images SET indexing_status = ? WHERE id = ?", (status, image_id))
        conn.commit()
        invalidate_cache()


def update_image_visual_metadata(image_id: int, has_visual_objects: int, visual_metadata: dict | str) -> None:
    """Updates visual object detection metadata for an image."""
    v_str = json.dumps(visual_metadata) if isinstance(visual_metadata, dict) else (visual_metadata or "{}")
    with _connect() as conn:
        conn.execute(
            "UPDATE images SET has_visual_objects = ?, visual_metadata = ? WHERE id = ?",
            (has_visual_objects, v_str, image_id),
        )
        conn.commit()
        invalidate_cache()


def get_sync_statistics(user_id: int | None = None) -> dict:
    """Retrieves document count by indexing status (completed, queued, indexing, failed)."""
    with _connect() as conn:
        if user_id is not None:
            rows = conn.execute(
                "SELECT indexing_status, COUNT(*) as cnt FROM images WHERE user_id = ? GROUP BY indexing_status",
                (user_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT indexing_status, COUNT(*) as cnt FROM images GROUP BY indexing_status"
            ).fetchall()

    counts = {"completed": 0, "queued": 0, "indexing": 0, "failed": 0, "total": 0}
    for r in rows:
        st = r["indexing_status"] or "completed"
        c = r["cnt"]
        counts[st] = counts.get(st, 0) + c
        counts["total"] += c
    return counts




