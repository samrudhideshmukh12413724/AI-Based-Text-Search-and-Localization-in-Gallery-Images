# DocuLens AI - INPUT PROCESSING OUTPUT

## 17. Input, Processing, and Output Documentation


Detailed step-by-step trace of core system pipelines:

WORKFLOW 1: Document Upload & Adaptive OCR Ingestion
- Input: Document photo captured by camera or selected from mobile gallery (JPEG/PNG/WEBP).
- Processing Steps:
  1. Frontend validates file existence and extracts MIME type.
  2. Mobile ApiService sends multipart POST request to `/upload` with optional `X-Guest-Session-ID` header.
  3. Backend sanitizes filename, generates UUID suffix (`{stem}_{hex8}.{ext}`), and writes file to `uploads/`.
  4. Backend checks SHA-256 binary hash and 64-bit perceptual hash (pHash) against the database to detect duplicates.
  5. Image is loaded with EXIF transposition correction (`ImageOps.exif_transpose`).
  6. Quality Assessment module computes Laplacian variance, mean brightness, contrast, and dynamic range.
  7. Preprocessing applies targeted enhancement (gamma correction, CLAHE, unsharp mask, deskew).
  8. EasyOCR executes trilingual OCR across 0° and evaluates alternate rotations (90° CW, 90° CCW, 180°) if text is sparse.
  9. Word-level bounding boxes are parsed, un-rotated, and normalized to relative coordinates [0.0, 1.0].
  10. Entity Engine extracts dates, amounts, Aadhaar, and PAN numbers.
  11. QR Decoder parses barcodes, UPI payment VPAs, and EMVCo tags.
  12. Metadata and extracted text are saved into SQLite database `images` table.
  13. SentenceTransformer generates 384-dimensional dense vector and appends to in-memory embedding cache in < 1ms.
  14. In-memory LRU search cache is cleared.
- Output: JSON response returning `image_id`, `image_name`, `indexing_status='completed'`, and extracted metadata.

WORKFLOW 2: Multi-Modal Search Fusion & Localization
- Input: Natural language query string (e.g. "bus ticket pune", "fee receipt", "aadhaar card") and optional metadata filters.
- Processing Steps:
  1. Frontend sends POST request to `/search` with JSON payload {query, category, date_from, date_to}.
  2. Backend validates authentication token or guest session ID. If unauthenticated (`user_id = -1`), returns empty vault.
  3. Checks in-memory LRU search cache (128-query capacity); if found, returns in < 5ms.
  4. Applies metadata candidate filters (date range, category, format), pruning eligible document IDs in SQL.
  5. Concurrently spawns three parallel threads in ThreadPoolExecutor:
     - Thread A (Keyword): Runs tokenized BM25 and inflection matching.
     - Thread B (Semantic): Encodes query with MiniLM and computes dense vector cosine similarity against all document embeddings.
     - Thread C (Visual): Encodes query with CLIP ViT-B/32 and computes dot product similarity against spatial visual patch embeddings.
  6. Merges candidate pools and computes fused score:
     S_hybrid = w_ocr * S_ocr + w_semantic * S_semantic + w_visual * S_visual
  7. Applies Adaptive Dynamic Threshold tau_adaptive(Q, scores) to filter noise.
  8. Calls `build_highlight_payload` to identify best preview sentence and matching word bounding boxes.
  9. Collapses duplicate variants under primary canonical document.
- Output: Ranked SearchResponse JSON containing preview snippets, match reasons, and normalized bounding box overlays.


---

