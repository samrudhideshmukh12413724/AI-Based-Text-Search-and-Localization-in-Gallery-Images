# ==============================================================================
# DocuLens AI - Production Cloud Dockerfile
# Optimized for Hugging Face Spaces (16GB RAM) & Cloud VPS (CPU PyTorch)
# ==============================================================================

FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive \
    DOCULENS_ROOT=/app \
    PYTHONPATH=/app \
    PORT=7860

# Install minimal OS runtime dependencies for OpenCV and image operations
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Hugging Face Spaces requires a non-root user with UID 1000
RUN useradd -m -u 1000 user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    HF_HOME=/home/user/.cache/huggingface \
    TORCH_HOME=/home/user/.cache/torch \
    EASYOCR_MODULE_PATH=/home/user/.EasyOCR

WORKDIR /app

# 1. Install PyTorch CPU-only wheel (reduces image size from 8GB down to ~1.6GB)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu

# 2. Copy and install production Python dependencies
COPY backend/requirements-prod.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# 3. Copy application code and initialize safe writable storage
COPY backend/app /app/app
# Copy compiled APK if present so /download serves it
COPY DocuLens_AI_App.apk* /app/

RUN mkdir -p /app/uploads /app/database /home/user/.cache /home/user/.EasyOCR && \
    chown -R user:user /app /home/user

# Switch to non-root user for security and Hugging Face Spaces compliance
USER user

# 4. Pre-download models during build to ensure fast container boot
RUN python -c "\
import easyocr; \
print('Pre-caching EasyOCR models...'); \
easyocr.Reader(['en'], gpu=False, verbose=False); \
from sentence_transformers import SentenceTransformer; \
print('Pre-caching MiniLM embeddings...'); \
SentenceTransformer('all-MiniLM-L6-v2'); \
"

# Expose ports (7860 for Hugging Face Spaces, 8000 for standard Docker)
EXPOSE 7860 8000

# Health check probe
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://127.0.0.1:${PORT:-7860}/api/health || exit 1

# Launch production server with Uvicorn on dynamic PORT
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-7860} --workers 1"]
