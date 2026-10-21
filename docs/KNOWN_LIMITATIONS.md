# DocuLens AI - KNOWN LIMITATIONS

## 41. Known Bugs and Limitations


Identified Technical Bugs and Behavioral Limitations:

1. Tracking of Sensitive Data in Git History (CRITICAL P0):
   - Finding: `database/images.db` (18.1 MB) is currently tracked in Git. It contains real user uploads from user 'samrudhi deshmukh' (user_id=24) including WhatsApp photos with real phone numbers and personal names (e.g. `final_test_77699926.jpeg`).
   - Impact: If pushed to a public GitHub repository, sensitive personal communications and phone numbers would be publicly exposed.
   - Mitigation: Must exclude `database/images.db` from public upload, sanitize the database to contain only clean demo documents, and rewrite Git history if already published.

2. Deprecation Warnings in PyTorch and FastAPI:
   - FastAPI `@app.on_event('startup')` is deprecated in FastAPI >= 0.109; should migrate to async lifespan context managers (`@asynccontextmanager async def lifespan(app)`).
   - PyTorch `torch.quantization.quantize_dynamic` is deprecated in PyTorch 2.x in favor of `torchao`.
   - Hugging Face `encoder_attention_mask` warning in BERT self-attention.

3. Disconnected Monolithic Files:
   - `mobile_app/lib/screens/home_screen.dart` is a 3,989-line monolithic stateful widget from earlier phases. It is currently disconnected from `main.dart` (which mounts `AuthScreen` -> `MainShell`). Retained for reference but adds dead weight.
   - `mobile_app/lib/screens/search_screen.dart` is an obsolete 92-line Phase 1 prototype screen, completely disconnected.

4. CPU Processing Latency on Large Un-indexed Folders:
   - Synchronous processing on CPU takes 1.5 - 2.5 seconds per document. While `SyncWorkerManager` mitigates this with background prioritization, batch importing 500+ un-indexed camera photos on low-end laptops can take 12 to 15 minutes.


---

