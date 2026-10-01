@echo off
title Start Android Emulator (Pixel 7a)
echo ========================================================
echo      PREPARING ANDROID VIRTUAL DEVICE: Pixel_7a
echo ========================================================
echo.

set PATH=%PATH%;C:\Users\deshm\AppData\Local\Android\Sdk\emulator;C:\Users\deshm\AppData\Local\Android\Sdk\platform-tools;C:\src\flutter\bin
set ADB=C:\Users\deshm\AppData\Local\Android\Sdk\platform-tools\adb.exe
set EMULATOR=C:\Users\deshm\AppData\Local\Android\Sdk\emulator\emulator.exe

:: Check if already running and online
"%ADB%" devices | findstr /r "emulator-[0-9]*.*device$" >nul
if %errorlevel% equ 0 (
    echo [OK] Emulator Pixel_7a is ALREADY RUNNING and online!
    echo No need to launch another instance.
    pause
    exit /b 0
)

:: Clean up any hung QEMU processes and stale lock files
echo Cleaning up any old/hung emulator processes and locks...
taskkill /f /im qemu-system-x86_64.exe >nul 2>&1
taskkill /f /im emulator.exe >nul 2>&1
del /f /q "C:\Users\deshm\.android\avd\Pixel_7a.avd\*.lock" >nul 2>&1
for /d %%d in ("C:\Users\deshm\.android\avd\Pixel_7a.avd\*.lock") do rd /s /q "%%d" >nul 2>&1
"%ADB%" kill-server >nul 2>&1
"%ADB%" start-server >nul 2>&1

echo Launching Pixel_7a in fresh cold-boot mode...
"%EMULATOR%" -avd Pixel_7a -no-snapshot-load -gpu host

pause
