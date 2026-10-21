# DocuLens AI - FUTURE SCOPE

## 43. Planned versus Completed Work


Milestone Audit:

Completed Work:
- Phase 1: Baseline EasyOCR text extraction and SQLite metadata indexing.
- Phase 2: SentenceTransformer MiniLM semantic vector search and calibrated dynamic thresholds.
- Phase 3A: OpenCV candidate region extraction and contour gradient detection.
- Phase 3B: OpenAI CLIP ViT-B/32 zero-shot visual region patch matching.
- Phase 4: BLIP image captioning, bilingual Marathi Devanagari translation, UPI QR decoder, SHA-256 duplicate detection, document relationship linking.
- Phase 5: Multi-tenant row-level security, JWT bearer tokens, isolated guest sessions, custom hybrid scoring formula, ELA tamper detection, 8-screen Flutter UI.

Planned Future Enhancements:
- Milestone 6: On-device quantized TFLite / ONNX inference for offline mobile OCR without local Python server dependency.
- Milestone 7: Document LayoutLM / Donut transformer for hierarchical document structure understanding (table cells, column flows).
- Milestone 8: Biometric fingerprint / FaceUnlock authentication for the Document Vault screen.


---

## 47. Future Improvements


Technical Roadmap for Future Releases:

1. Model Quantization (INT8 / ONNX Runtime):
   Quantize SentenceTransformer and CLIP models from FP32 down to INT8 using ONNX Runtime or `torchao`, reducing RAM consumption by 70% and accelerating CPU inference from 250ms down to ~60ms.

2. On-Device Flutter Mobile TFLite Pipeline:
   Port EasyOCR and lightweight embedding models directly into Flutter using TensorFlow Lite / ONNX Mobile, allowing simple OCR searches to operate completely offline on the phone with zero backend communication.

3. Structured Form Layout Understanding (LayoutLM / Donut):
   Upgrade the invoice and entity parser to use a document transformer (LayoutLMv3 or Donut) to extract complex nested tables, line-item tax matrices, and multi-column forms.

4. Biometric App Lock & Encrypted Vault:
   Implement native Android BiometricPrompt (fingerprint and face unlock) on the Document Vault screen, encrypting cached image files on the phone using AES-256-GCM.


---

## 48. Risks and Technical Debt


Technical Debt and Operational Risks:

1. Large Binaries and Backups in Repository Root (HIGH RISK):
   The active working tree contains `cloudflared.exe` (55.3 MB), `DocuLens_AI_App.apk` (22.6 MB), multiple `.db` backup snapshots (148 MB), and frozen screenshots (53 MB). These must remain strictly excluded from public Git tracking to prevent repository bloat.

2. Database Tracked in Git (SECURITY RISK P0):
   `database/images.db` and `images.db.bak_step8_pristine` are currently tracked in Git history. They must be removed from Git index (`git rm --cached`) and `.gitignore` updated with `database/*.db`.

3. Monolithic Legacy Code:
   `mobile_app/lib/screens/home_screen.dart` contains 3,989 lines of legacy code. While preserved locally to ensure no functionality is lost, it should be cleanly archived into a legacy reference module.

4. Hardcoded HMAC Secret Key in Patentable Prototype:
   `backend/app/patentable/stego_crypto_binding.py:17` defines `SECRET_HMAC_KEY = b"2026-patentable-zk-stego-secret-key-ocr-search"`. Must be moved to an environment variable (`os.getenv('STEGO_HMAC_SECRET')`).


---

