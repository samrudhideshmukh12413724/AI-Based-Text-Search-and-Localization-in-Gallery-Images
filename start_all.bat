@echo off
title AI Image Search - 1-Click Launcher
echo ========================================================
echo      AI IMAGE SEARCH - AUTOMATED 1-CLICK LAUNCHER
echo ========================================================
echo.

:: Add Flutter, Android SDK, and Python tools to PATH for this session
set PATH=%PATH%;C:\src\flutter\bin;C:\Users\deshm\AppData\Local\Android\Sdk\platform-tools;C:\Users\deshm\AppData\Local\Android\Sdk\emulator
set ADB=C:\Users\deshm\AppData\Local\Android\Sdk\platform-tools\adb.exe
set EMULATOR=C:\Users\deshm\AppData\Local\Android\Sdk\emulator\emulator.exe
set AVD_NAME=Pixel_7a

:: 1. Start Python Backend in a separate window (if not already running)
echo [1/4] Checking / Starting FastAPI Backend Server on port 8000...
netstat -ano | findstr /r ":8000 .*LISTENING" >nul
if %errorlevel% equ 0 (
    echo [Backend] Server is already running on http://127.0.0.1:8000
) else (
    echo [Backend] Starting FastAPI Server in a separate window...
    start "AI Image Search - Backend Server" cmd /k "cd /d %~dp0backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"
    timeout /t 3 /nobreak >nul
)

:: 2. Check if a device is connected (Physical Phone via USB or Emulator)
echo.
echo [2/4] Checking connected devices (Physical Phone or Emulator)...
set DEVICE_FOUND=0
"%ADB%" devices | findstr /v "List of devices" | findstr /r "device$" >nul
if %errorlevel% equ 0 (
    echo [Device] Active device detected via USB/ADB!
    set DEVICE_FOUND=1
    goto AFTER_DEVICE
)

:: If no device is connected, boot the Android Emulator
echo [Device] No active device detected. Preparing Android Emulator (%AVD_NAME%)...
echo [Emulator] Cleaning up any hung instances and stale locks...
taskkill /f /im qemu-system-x86_64.exe >nul 2>&1
taskkill /f /im emulator.exe >nul 2>&1
del /f /q "C:\Users\deshm\.android\avd\%AVD_NAME%.avd\*.lock" >nul 2>&1
for /d %%d in ("C:\Users\deshm\.android\avd\%AVD_NAME%.avd\*.lock") do rd /s /q "%%d" >nul 2>&1
"%ADB%" kill-server >nul 2>&1
"%ADB%" start-server >nul 2>&1

echo [Emulator] Booting fresh %AVD_NAME% (cold boot mode)...
start "" "%EMULATOR%" -avd %AVD_NAME% -no-snapshot-load -gpu host

echo [Emulator] Waiting for emulator to connect to ADB...
"%ADB%" wait-for-device

echo [Emulator] Waiting for Android OS to finish booting...
:WAIT_BOOT
timeout /t 3 /nobreak >nul
set BOOT_DONE=0
for /f "tokens=*" %%i in ('"%ADB%" shell getprop sys.boot_completed 2^>nul') do set BOOT_DONE=%%i
if "%BOOT_DONE%" neq "1" (
    echo   Still booting... please wait a few seconds...
    goto WAIT_BOOT
)
echo [Emulator] Android OS boot completed successfully!

:AFTER_DEVICE

:: 3. Configure reverse port forwarding for local API calls
echo.
echo [3/4] Forwarding Backend Port 8000 to connected device...
"%ADB%" reverse tcp:8000 tcp:8000
echo [Network] Port forwarding active: http://127.0.0.1:8000 and http://10.0.2.2:8000 mapped!

:: 4. Build and run Flutter App
echo.
echo [4/4] Building and launching Flutter app...
echo ========================================================
echo The app will compile and automatically appear on your
echo device screen. (Hot-reload: press 'r' in this window)
echo ========================================================
echo.
cd /d "%~dp0mobile_app"
call flutter run

pause
