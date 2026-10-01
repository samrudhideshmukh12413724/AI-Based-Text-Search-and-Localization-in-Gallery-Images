# Flutter + Android Studio setup (Windows)

Follow these steps in order.

---

## Step 1 — Install Flutter SDK (automated script)

Open **PowerShell** (not CMD) and run:

```powershell
cd c:\Users\deshm\Downloads\ocr_image_search_mobile_app\AI_Image_Search
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\install_flutter.ps1
```

This downloads Flutter to `C:\src\flutter` and adds it to your PATH.

**After the script finishes, close and reopen PowerShell**, then verify:

```powershell
flutter --version
flutter doctor
```

---

## Step 2 — Install Android Studio (required for phone/emulator)

1. Download: https://developer.android.com/studio
2. Run the installer → choose **Standard** setup
3. Open Android Studio → **More Actions** → **SDK Manager**
4. Ensure these are installed:
   - Android SDK Platform (API 34 or 35)
   - Android SDK Build-Tools
   - Android SDK Command-line Tools
5. Open **Device Manager** → Create a virtual device (e.g. Pixel 7, API 34)

Or via winget (may take several minutes):

```powershell
winget install Google.AndroidStudio
```

---

## Step 3 — Accept Android licenses

```powershell
flutter doctor --android-licenses
```

Type `y` for each prompt.

---

## Step 4 — Fix common `flutter doctor` issues

| Issue | Fix |
|-------|-----|
| Android toolchain missing | Install Android Studio + SDK (Step 2) |
| cmdline-tools not found | SDK Manager → install **Command-line Tools** |
| Android licenses | `flutter doctor --android-licenses` |
| Visual Studio missing (Windows desktop) | Optional; not needed for Android app |

Target: `flutter doctor` shows ✓ for **Flutter** and **Android toolchain**.

---

## Step 5 — Create and run your mobile app

**Terminal 1 — backend:**

```powershell
cd c:\Users\deshm\Downloads\ocr_image_search_mobile_app\AI_Image_Search
.\start_backend.bat
```

**Terminal 2 — Flutter app:**

```powershell
cd c:\Users\deshm\Downloads\ocr_image_search_mobile_app\AI_Image_Search\mobile_app
flutter create . --project-name ai_image_search
flutter pub get
flutter doctor
flutter run
```

Pick your Android emulator or connected phone when prompted.

---

## Step 6 — API URL (important)

Edit `mobile_app/lib/services/api_service.dart`:

| Device | `baseUrl` |
|--------|-----------|
| Android emulator | `http://10.0.2.2:8000` (default) |
| Physical phone (same Wi‑Fi) | `http://YOUR_PC_IP:8000` |

Find your PC IP:

```powershell
ipconfig
```

Look for **IPv4 Address** under your Wi‑Fi adapter (e.g. `192.168.1.5`).

---

## Step 7 — Faculty demo checklist

1. Start backend (`start_backend.bat`)
2. Open app on emulator/phone
3. **SELECT IMAGE** → pick `scholarship.jpg`
4. **EXTRACT TEXT** → see OCR result
5. Search **scholarship** → see matching image + text

---

## Troubleshooting

**`flutter` not recognized**  
Close all terminals, open a new PowerShell, run `flutter --version`.  
If still failing, add manually to PATH: `C:\src\flutter\bin`

**App cannot connect to backend**  
- Backend running? Test: http://127.0.0.1:8000/health  
- Emulator uses `10.0.2.2`, not `localhost`  
- Phone must use PC IP, not `127.0.0.1`

**`flutter create` overwrites files**  
Our `lib/` code is already written. If prompted, keep existing files or re-copy from git/backup.

**Slow first OCR**  
EasyOCR downloads models on first run (~1–2 min). Normal.

---

## What you already have installed

- ✅ Python 3.11  
- ✅ Git  
- ✅ Java (multiple versions)  
- ❌ Flutter — install with Step 1  
- ❌ Android Studio / SDK — install with Step 2  
