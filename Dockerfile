# ==============================================================================
# DocuLens AI - Production Cloud Dockerfile
# Optimized for Oracle Cloud / DigitalOcean / AWS / GCP VPS (CPU PyTorch)
# ==============================================================================

FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive \
    PORT=8000

# Install minimal OS runtime dependencies for OpenCV and image operations
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 1. Install PyTorch CPU-only wheel (reduces image size from 8GB down to ~1.6GB)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu

# 2. Copy and install production Python dependencies
COPY backend/requirements-prod.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# 3. Copy application code and assets
COPY backend/app /app/app
COPY backend/uploads /app/uploads
COPY database /app/database
COPY DocuLens_AI_App.apk /app/DocuLens_AI_App.apk

# 4. Pre-download models during build to ensure fast container boot
RUN python -c "
import easyocr
print('Pre-caching EasyOCR models...')
easyocr.Reader(['en'], gpu=False, verbose=False)
from sentence_transformers import SentenceTransformer
print('Pre-caching MiniLM embeddings...')
SentenceTransformer('all-MiniLM-L6-v2')
"

# Expose port
EXPOSE 8000

# Health check probe
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://127.0.0.1:8000/api/health || exit 1

# Launch production server with Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
