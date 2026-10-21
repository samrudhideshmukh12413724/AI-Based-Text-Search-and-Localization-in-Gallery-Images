# DocuLens AI - AI MODELS AND LIBRARIES

## 18. AI Model Inventory


The system incorporates four deep learning neural network architectures:

1. Optical Character Recognition (OCR) Engine:
- Model Architecture: EasyOCR (Dual-stage: CRAFT text detector + CRNN text recognizer).
- Checkpoint / Checkpoints: CRAFT (Character Region Awareness for Text Detection) + standard PyTorch CRNN weights.
- Framework: PyTorch 2.x CPU inference.
- Supported Scripts: Latin (English), Devanagari (Hindi, Marathi).
- Weights Location: Cached in user home directory `~/.EasyOCR/model/` (craft_mlt_25k.pth ~45 MB, devanagari.pth ~35 MB, english_g2.pth ~25 MB).
- Repository Status: Pre-downloaded in Dockerfile; not committed directly to git repository (avoids bloat).

2. Dense Semantic Vector Embedding Model:
- Model Architecture: BERT-based 6-layer MiniLM transformer.
- Checkpoint: `sentence-transformers/all-MiniLM-L6-v2`.
- Framework: Hugging Face Transformers & Sentence-Transformers.
- Vector Dimensionality: 384 dimensions, normalized Euclidean float32.
- Purpose: Natural language conceptual search and semantic document retrieval.
- Weights Location: Cached in `~/.cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2/` (~90 MB).
- Repository Status: Loaded dynamically; pre-cached during Docker build.

3. Vision-Language Visual Region Matcher:
- Model Architecture: CLIP (Contrastive Language-Image Pre-training) ViT-B/32 (Vision Transformer Base, 32x32 patch size).
- Checkpoint: `openai/clip-vit-base-patch32`.
- Framework: Hugging Face Transformers & PyTorch.
- Vector Dimensionality: 512 dimensions, L2-normalized float32.
- Purpose: Open-vocabulary zero-shot visual region matching (signatures, stamps, logos, face photos).
- Weights Location: Cached in `~/.cache/huggingface/hub/models--openai--clip-vit-base-patch32/` (~600 MB).
- Repository Status: Weights excluded from git; loaded on-demand with offline cache fallback.

4. Image Captioning Engine (Visual Fallback):
- Model Architecture: BLIP (Bootstrapping Language-Image Pre-training) Conditional Generation Base.
- Checkpoint: `Salesforce/blip-image-captioning-base`.
- Framework: Hugging Face Transformers.
- Purpose: Generates natural language descriptive text captions for images lacking written text.
- Fallback Mode: When model weights are absent, falls back gracefully to rule-based aspect ratio descriptions (`photo image in landscape format (1600x1200)`).


---

## 19. Library and Framework Inventory


Backend Python Dependencies (from backend/requirements-prod.txt):
- `fastapi` (>=0.110.0): Core ASGI web framework providing asynchronous request handling, routing, dependency injection, and Pydantic validation.
- `uvicorn[standard]` (>=0.27.0): High-performance ASGI web server managing worker processes and event loops.
- `python-multipart` (>=0.0.9): Streaming multipart form-data parser required for file uploads.
- `Pillow` (>=10.0.0): Core image manipulation library handling EXIF orientation, crop transformations, and format conversions.
- `opencv-python-headless` (>=4.8.0): Production computer vision library providing CLAHE, Sobel gradients, contour detection, and QRCodeDetector.
- `easyocr` (>=1.7.0): Multi-language OCR engine.
- `sentence-transformers` (>=2.2.0): Sentence embedding library for dense semantic text representation.
- `transformers` (>=4.30.0): Hugging Face model orchestration library supporting CLIP and BLIP models.
- `pyjwt` (>=2.8.0): RFC 7519 compliant JSON Web Token library for stateless user authentication.
- `passlib[bcrypt]` (>=1.7.4) & `bcrypt` (>=4.0.1): Cryptographic password hashing using salted Blowfish.
- `qrcode[pil]` (>=7.4.2): QR code generation utility for download posters.
- `reportlab` (>=4.0.0): PDF document generation engine.
- `imagehash` (>=4.3.1): Perceptual hashing library providing 64-bit pHash for visual near-duplicate detection.
- `numpy` (>=1.24.0): Matrix computation and vector math.
- `pydantic` (>=2.0.0): Data validation and settings management.
- `PyMuPDF` (>=1.23.0): PDF parsing utility.
- `python-docx` (>=1.2.0): Word document generator for comprehensive audit reports.

Frontend Flutter Dependencies (from mobile_app/pubspec.yaml):
- `flutter`: Core cross-platform mobile SDK.
- `http` (^1.2.0): REST HTTP networking client.
- `image_picker` (^1.0.7): Camera and gallery photo selection plugin.
- `file_picker` (^11.0.3): Local device filesystem file and directory selector.
- `photo_manager` (^3.0.0): Native Android media library crawler.
- `shared_preferences` (^2.5.3): Persistent key-value storage on Android.
- `url_launcher` (^6.3.0): Native intent launcher for web links, telephone calls, and PDF viewing.


---

