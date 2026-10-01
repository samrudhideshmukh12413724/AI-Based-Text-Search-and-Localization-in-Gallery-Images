# AI Image Search — Phase 1

Phase 1 proves the basic pipeline works:

**Mobile app → upload image → Python backend → EasyOCR → SQLite → keyword search → show result**

## Folder structure

```
AI_Image_Search/
├── mobile_app/          Flutter app
├── backend/             FastAPI + EasyOCR + SQLite
├── dataset/             Sample images (10 files)
├── database/            SQLite file (images.db)
└── README.md
```

## Setup

### 1. Python backend

```powershell
cd AI_Image_Search\backend
pip install -r requirements.txt
python seed_dataset.py
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

API docs: http://127.0.0.1:8000/docs

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Server check |
| `/upload` | POST | Upload image, OCR, save to SQLite |
| `/search` | POST | Keyword search (`{"query": "scholarship"}`) |
| `/images` | GET | List all indexed images |

### 2. Flutter mobile app

Install [Flutter](https://docs.flutter.dev/get-started/install) and Android Studio first.

```powershell
cd AI_Image_Search\mobile_app
flutter create . --project-name ai_image_search
flutter pub get
flutter run
```

**API URL:** Edit `lib/services/api_service.dart`:
- Android emulator: `http://10.0.2.2:8000` (default)
- Physical phone: use your PC IP, e.g. `http://192.168.1.5:8000`

## Checkpoints

| Checkpoint | Status |
|------------|--------|
| 1 — OCR on test image | Run `python test_ocr.py` |
| 2 — Backend OCR API | POST `/upload` |
| 3 — Flutter → backend | Select image → Extract Text |
| 4 — Full system | Upload → store → search → show image |

## Faculty demo flow

1. Open app → **SELECT IMAGE** → choose `scholarship.jpg`
2. Tap **EXTRACT TEXT** → show extracted text
3. Search **scholarship** → show matching image + text

## AI in Phase 1

EasyOCR uses pre-trained deep learning models to read text from images. We are **not** training our own model.

## Not in Phase 1

LLM, NLP, semantic search, vector DB, QR detection, custom training — later phases.
