# Flutter setup for Phase 1 mobile app
#
# 1. Install Flutter (pick one):
#    winget install Google.Flutter
#    OR download: https://docs.flutter.dev/get-started/install/windows
#
# 2. Install Android Studio + Android SDK
#
# 3. Then run:
#    cd mobile_app
#    flutter create . --project-name ai_image_search
#    flutter pub get
#    flutter doctor
#    flutter run
#
# 4. Start backend first (from project root):
#    start_backend.bat
#
# 5. API URL (edit lib/services/api_service.dart if needed):
#    Emulator:  http://10.0.2.2:8000
#    Real phone: http://YOUR_PC_IP:8000

Write-Host "Flutter setup checklist written to SETUP_FLUTTER.md"
Write-Host "After installing Flutter, run:"
Write-Host "  cd mobile_app"
Write-Host "  flutter create . --project-name ai_image_search"
Write-Host "  flutter pub get"
Write-Host "  flutter run"
