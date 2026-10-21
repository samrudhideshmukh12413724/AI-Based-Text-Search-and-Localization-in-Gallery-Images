# DocuLens AI - DEPLOYMENT GUIDE

## 35. Current Deployment Architecture


Deployment Specifications:

1. Docker Containerization (`Dockerfile`):
   - Base Image: `python:3.11-slim` with OS runtime libraries (`libgl1`, `libglib2.0-0`, `libgomp1`, `curl`).
   - PyTorch CPU Optimization: Installs lightweight CPU-only PyTorch wheels from `https://download.pytorch.org/whl/cpu`, shrinking the container image size from 8.2 GB down to ~1.6 GB.
   - Pre-Caching: EasyOCR and MiniLM weights are pre-downloaded during `docker build`, ensuring that container spin-up takes less than 3 seconds.
   - Healthcheck Probe: `curl -f http://127.0.0.1:8000/api/health || exit 1` every 30s.

2. Cloudflare Zero-Trust Tunnel Integration:
   - Bundles `cloudflared.exe` (55.3 MB) and startup batch scripts (`start_all.bat`, `start_public_download_server.bat`).
   - Generates dynamic, secure public HTTPS URLs (`https://*.trycloudflare.com`) routing to port 8000.
   - Enables physical Android devices on cellular data (4G/5G) to connect securely to the backend without port forwarding or public static IPs.

3. Docker Compose (`docker-compose.yml`):
   - Maps host port 8000 to container port 8000.
   - Mounts persistent host volumes for `./uploads:/app/uploads` and `./database:/app/database`.


---

## 37. Installation and Configuration


Step-by-Step Setup Guide:

Prerequisites:
- Python 3.11 (64-bit)
- Flutter SDK 3.27+ with Dart 3.6+
- Git 2.x
- (Optional) Docker Desktop 4.x

Backend Setup:
1. Navigate to backend directory: `cd AI_Image_Search/backend`
2. Create and activate a Python virtual environment:
   `python -m venv venv`
   `venv\Scripts\activate` (Windows) or `source venv/bin/activate` (Linux/Mac)
3. Install CPU PyTorch wheel:
   `pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu`
4. Install production dependencies:
   `pip install -r requirements-prod.txt`
5. Configure environment variables in `backend/.env`:
   `ENVIRONMENT=development`
   `SECRET_KEY=your-secure-random-jwt-key`
   `ALGORITHM=HS256`
   `DB_PATH=database/images.db`

Flutter Setup:
1. Navigate to mobile app directory: `cd AI_Image_Search/mobile_app`
2. Resolve Flutter packages: `flutter pub get`
3. Verify environment health: `flutter doctor -v`


---

## 38. Running the Project Locally


Local Execution Instructions:

Option A: One-Click Startup (Windows):
Double-click `AI_Image_Search/start_all.bat`.
This automated script:
1. Verifies the Python environment.
2. Starts the Uvicorn FastAPI server on `http://0.0.0.0:8000`.
3. Detects your physical LAN IP address (e.g. `10.81.62.241`).
4. Generates an APK download QR poster (`doculens_apk_download_qr.png`).
5. Launches Cloudflare tunnel (`cloudflared.exe`) providing public HTTPS connectivity.

Option B: Manual Command-Line Startup:
1. Start FastAPI Backend:
   `cd AI_Image_Search/backend`
   `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`
2. Run Flutter App on Android Device or Emulator:
   `cd AI_Image_Search/mobile_app`
   `flutter run -d <device_id>`
3. Run on Chrome Browser:
   `flutter run -d chrome --web-port 3000`


---

## 39. Cloud Deployment Instructions


Deploying to Cloud VPS (Oracle Cloud Free Tier, DigitalOcean, AWS EC2, GCP Compute Engine):

1. Provision an Ubuntu 22.04 LTS VPS instance (minimum 2 vCPU, 4GB RAM recommended for CPU PyTorch).
2. Install Docker and Docker Compose:
   `sudo apt-get update && sudo apt-get install -y docker.io docker-compose`
3. Clone the sanitized repository:
   `git clone https://github.com/samrudhideshmukh12413724/AI-Based-Text-Search-and-Localization-in-Gallery-Images.git`
   `cd AI-Based-Text-Search-and-Localization-in-Gallery-Images`
4. Build and start the container in background daemon mode:
   `docker-compose up -d --build`
5. Verify container health:
   `docker ps`
   `curl http://127.0.0.1:8000/api/health`
6. Configure HTTPS Reverse Proxy with Nginx and Certbot Let's Encrypt SSL certificate.


---

