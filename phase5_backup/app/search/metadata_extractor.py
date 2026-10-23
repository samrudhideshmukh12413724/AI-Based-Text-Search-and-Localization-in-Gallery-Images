"""Image File & EXIF Metadata Extractor.

Extracts technical file properties and temporal metadata:
- File size (bytes)
- Dimensions (width, height)
- Image format (JPEG, PNG, WEBP)
- File modification timestamp
- Camera EXIF creation timestamp (if present)
- Primary resolved document date (OCR entities -> EXIF -> File timestamp)
"""

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional
from PIL import Image, ExifTags


def extract_image_metadata(image_path: str | Path, entities: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Extracts comprehensive technical, EXIF, and resolved temporal metadata from an image.
    """
    path = Path(image_path)
    if not path.exists():
        return {
            "file_size_bytes": 0,
            "image_width": 0,
            "image_height": 0,
            "file_format": "",
            "file_modified_at": "",
            "exif_created_at": "",
            "primary_date": "",
        }

    # 1. File stats
    stat = path.stat()
    file_size = stat.st_size
    file_mod = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()

    # 2. Image dimensions & format via Pillow
    width = 0
    height = 0
    img_fmt = ""
    exif_date = ""

    try:
        with Image.open(path) as img:
            width, height = img.size
            img_fmt = img.format or path.suffix.lstrip(".").upper()

            # EXIF extraction
            try:
                exif_data = img.getexif()
                if exif_data:
                    # Tag 36867 = DateTimeOriginal, 306 = DateTime, 36868 = DateTimeDigitized
                    for tag_id in (36867, 306, 36868):
                        if tag_id in exif_data:
                            raw_exif_dt = str(exif_data[tag_id]).strip()
                            # EXIF dates are typically "YYYY:MM:DD HH:MM:SS"
                            parts = raw_exif_dt.split(" ")
                            if parts:
                                iso_d = parts[0].replace(":", "-")
                                if len(iso_d) == 10:
                                    exif_date = iso_d
                                    break
            except Exception:
                pass
    except Exception:
        pass

    # 3. Resolve primary document date:
    # Priority 1: Date printed on document (from OCR entities)
    # Priority 2: EXIF capture date
    # Priority 3: File modified date (YYYY-MM-DD)
    primary_date = ""
    if entities and entities.get("primary_date"):
        primary_date = entities["primary_date"]
    elif exif_date:
        primary_date = exif_date
    elif file_mod:
        primary_date = file_mod[:10]

    return {
        "file_size_bytes": file_size,
        "image_width": width,
        "image_height": height,
        "file_format": img_fmt,
        "file_modified_at": file_mod,
        "exif_created_at": exif_date,
        "primary_date": primary_date,
    }
