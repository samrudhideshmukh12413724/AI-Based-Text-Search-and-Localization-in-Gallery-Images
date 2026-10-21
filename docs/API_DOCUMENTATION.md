# DocuLens AI - API DOCUMENTATION

## 15. Complete API Endpoint Reference


The FastAPI backend exposes 28 REST endpoints organized into 6 functional groups:

1. Authentication & Tenant Management:
- POST `/auth/register`: Register new user account. Accepts JSON {username, password, is_admin}. Returns user_id.
- POST `/auth/login`: Authenticate user and issue JWT bearer token. Accepts JSON {username, password}. Returns access_token, expires_in.
- GET `/auth/me`: Retrieve current authenticated user profile and admin status.
- GET `/auth/users`: List registered users (Administrator access required).

2. Document Ingestion & Storage:
- POST `/upload`: Upload document image. Accepts multipart/form-data (file, async_mode, priority). Returns image_id, indexing_status.
- GET `/uploads/{filename}`: Secure document file delivery. Enforces row-level tenant ownership and blocks path traversal (`../`).
- GET `/images/{image_id}/file`: Authorized original image file download.
- GET `/images/{image_id}/thumbnail`: Authorized thumbnail image stream.
- GET `/images/{image_id}`: Retrieve single document metadata, extracted text, and entities.
- DELETE `/images/{image_id}`: Permanently delete document file and database records. Enforces tenant ownership.
- GET `/images`: List documents in the authenticated user's Document Vault with pagination and category filtering.

3. Document Search & Discovery:
- POST `/search`: Unified Multi-Modal Search Fusion Router. Accepts SearchRequest JSON {query, category, year, date_from, date_to, format, visual_type, entity_type}. Returns ranked results with glowing bounding box coordinates.
- GET `/search`: GET query parameter alias for `/search` supporting browser exploration and URL sharing.
- POST `/search/semantic`: Dense vector semantic search using SentenceTransformer embeddings.
- POST `/search/visual_region`: Pure zero-shot visual region search using CLIP ViT-B/32 patch embeddings.

4. Synchronization & Gallery Background Processing:
- POST `/images/sync-check`: High-speed bulk folder crawler check. Compares up to 5,000 filenames/sizes against indexed database records in < 0.5 seconds.
- GET `/sync/status` & `/images/sync-status`: Real-time sync worker diagnostics, active job queue size, and worker thread status.

5. Document Intelligence & Relationships:
- GET `/images/{image_id}/relationships`: Retrieve explainable related documents sharing Aadhaar, PAN, phone, or application IDs.
- GET `/knowledge-graph`: Generate interactive global knowledge graph (nodes = documents + entities, edges = shared relationships).
- GET `/parse-invoice/{image_id}`: Parse receipts into structured line items, CGST/SGST taxes, payment mode, and grand total.
- POST `/translate-indic`: Detect Devanagari text and return English translations with cross-lingual query expansions.
- GET `/images/{image_id}/export-pdf`: Compile single document into searchable PDF with embedded OCR text and SHA-256 metadata.
- POST `/images/export-multi-pdf`: Compile multiple selected documents into a unified multi-page PDF portfolio.

6. Security, Integrity & Patentable Modules:
- GET `/analyze-tampering/{image_id}`: Run Error Level Analysis (ELA) to compute localized tamper suspicion score.
- POST `/patentable/stego-crypto-bind/{image_id}`: Embed HMAC-SHA256 zero-knowledge signature into image pixel LSBs.
- GET `/patentable/forgery-localizer/{image_id}`: Pinpoint exact forged OCR word bounding boxes having pixel error spikes.
- POST `/patentable/entropy-fusion`: Calculate Shannon Query Entropy H(Q) and return dynamic multi-modal weights.
- GET `/health` & `/api/health`: Container and Kubernetes liveness probe.
- GET `/download-app` & `/download`: Direct mobile APK download endpoint for distribution over local Wi-Fi or Cloudflare tunnel.


---

