"""
High-Precision Searchable PDF Exporter (Adobe Scan / CamScanner standard).

Converts scanned document images into commercial-grade PDF files featuring:
1. High-resolution document image rendering.
2. An embedded invisible OCR text layer (render_mode=3) matching pixel coordinates,
   allowing Ctrl+F search, mouse/touch text selection, and direct copy-paste.
3. Multi-page document compilation (combines multiple scanned pages into one searchable PDF).
"""

from pathlib import Path
from typing import List, Dict, Any, Optional
import fitz  # PyMuPDF
from PIL import Image


def generate_searchable_pdf(
    image_path: str | Path,
    ocr_text: str = "",
    word_boxes: Optional[List[Dict[str, Any]]] = None,
    output_path: Optional[str | Path] = None,
) -> bytes:
    """
    Creates a single-page searchable PDF with the document image and embedded invisible text layer.
    """
    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found at {image_path}")

    with Image.open(image_path) as img:
        img_w, img_h = img.size

    doc = fitz.open()
    page = doc.new_page(width=float(img_w), height=float(img_h))

    # Insert document image filling the entire page
    page_rect = fitz.Rect(0, 0, float(img_w), float(img_h))
    page.insert_image(page_rect, filename=str(image_path))

    # Insert invisible searchable text layer
    if word_boxes:
        for wb in word_boxes:
            text = str(wb.get("text", "")).strip()
            if not text:
                continue
            bbox = wb.get("bbox", {})
            bx = float(bbox.get("x", 0))
            by = float(bbox.get("y", 0))
            bw = float(bbox.get("width", 20))
            bh = float(bbox.get("height", 14))

            # Guard against invalid box geometry
            if bw <= 0 or bh <= 0 or bx >= img_w or by >= img_h:
                continue

            rect = fitz.Rect(bx, by, min(bx + bw, img_w), min(by + bh, img_h))
            fontsize = max(6.0, min(bh * 0.8, 36.0))
            try:
                # render_mode=3 is invisible text in PDF standard (selectable and searchable)
                page.insert_textbox(
                    rect,
                    text,
                    fontsize=fontsize,
                    render_mode=3,
                    align=fitz.TEXT_ALIGN_LEFT,
                )
            except Exception:
                pass
    elif ocr_text.strip():
        # Fallback: insert the full OCR text as an invisible layer across the page
        try:
            page.insert_textbox(
                fitz.Rect(20, 20, img_w - 20, img_h - 20),
                ocr_text.strip(),
                fontsize=11.0,
                render_mode=3,
            )
        except Exception:
            pass

    pdf_bytes = doc.tobytes(deflate=True)
    if output_path:
        with open(output_path, "wb") as f:
            f.write(pdf_bytes)
    doc.close()
    return pdf_bytes


def generate_multi_page_pdf(
    documents: List[Dict[str, Any]],
    output_path: Optional[str | Path] = None,
) -> bytes:
    """
    Creates a multi-page searchable PDF containing multiple scanned documents.
    Each item in documents is:
    {
        "image_path": str,
        "ocr_text": str,
        "word_boxes": list (optional)
    }
    """
    doc = fitz.open()

    for item in documents:
        img_path = Path(item["image_path"])
        if not img_path.exists():
            continue

        with Image.open(img_path) as img:
            img_w, img_h = img.size

        page = doc.new_page(width=float(img_w), height=float(img_h))
        page_rect = fitz.Rect(0, 0, float(img_w), float(img_h))
        page.insert_image(page_rect, filename=str(img_path))

        word_boxes = item.get("word_boxes")
        ocr_text = item.get("ocr_text", "")

        if word_boxes:
            for wb in word_boxes:
                text = str(wb.get("text", "")).strip()
                if not text:
                    continue
                bbox = wb.get("bbox", {})
                bx = float(bbox.get("x", 0))
                by = float(bbox.get("y", 0))
                bw = float(bbox.get("width", 20))
                bh = float(bbox.get("height", 14))

                if bw <= 0 or bh <= 0 or bx >= img_w or by >= img_h:
                    continue

                rect = fitz.Rect(bx, by, min(bx + bw, img_w), min(by + bh, img_h))
                fontsize = max(6.0, min(bh * 0.8, 36.0))
                try:
                    page.insert_textbox(
                        rect,
                        text,
                        fontsize=fontsize,
                        render_mode=3,
                        align=fitz.TEXT_ALIGN_LEFT,
                    )
                except Exception:
                    pass
        elif ocr_text.strip():
            try:
                page.insert_textbox(
                    fitz.Rect(20, 20, img_w - 20, img_h - 20),
                    ocr_text.strip(),
                    fontsize=11.0,
                    render_mode=3,
                )
            except Exception:
                pass

    pdf_bytes = doc.tobytes(deflate=True)
    if output_path:
        with open(output_path, "wb") as f:
            f.write(pdf_bytes)
    doc.close()
    return pdf_bytes
