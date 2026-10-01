# Downloads and installs Flutter SDK on Windows.
# Run in PowerShell:
#   Set-ExecutionPolicy -Scope Process Bypass
#   .\install_flutter.ps1

$ErrorActionPreference = "Stop"

$FlutterRoot = "C:\src\flutter"
$ZipPath = "$env:TEMP\flutter_windows_stable.zip"
$FlutterUrl = "https://storage.googleapis.com/flutter_infra_release/releases/stable/windows/flutter_windows_3.27.4-stable.zip"

Write-Host "=== Flutter SDK Installer ===" -ForegroundColor Cyan
Write-Host ""

if (Test-Path "$FlutterRoot\bin\flutter.bat") {
    Write-Host "Flutter already exists at $FlutterRoot" -ForegroundColor Green
} else {
    New-Item -ItemType Directory -Force -Path "C:\src" | Out-Null

    Write-Host "Downloading Flutter SDK (~1 GB). This may take several minutes..." -ForegroundColor Yellow
    Write-Host "URL: $FlutterUrl"
    Invoke-WebRequest -Uri $FlutterUrl -OutFile $ZipPath -UseBasicParsing

    Write-Host "Extracting to C:\src ..."
    Expand-Archive -Path $ZipPath -DestinationPath "C:\src" -Force
    Remove-Item $ZipPath -Force
    Write-Host "Flutter extracted to $FlutterRoot" -ForegroundColor Green
}

$BinPath = "$FlutterRoot\bin"
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*$BinPath*") {
    [Environment]::SetEnvironmentVariable("Path", "$userPath;$BinPath", "User")
    $env:Path = "$env:Path;$BinPath"
    Write-Host "Added $BinPath to user PATH" -ForegroundColor Green
    Write-Host "IMPORTANT: Close and reopen PowerShell after this script finishes." -ForegroundColor Yellow
} else {
    Write-Host "Flutter bin already in PATH" -ForegroundColor Green
}

Write-Host ""
Write-Host "Running flutter doctor..." -ForegroundColor Cyan
& "$BinPath\flutter.bat" doctor -v

Write-Host ""
Write-Host "=== Next steps ===" -ForegroundColor Cyan
Write-Host "1. Install Android Studio: https://developer.android.com/studio"
Write-Host "2. Reopen PowerShell, then run: flutter doctor --android-licenses"
Write-Host "3. Read INSTALL_FLUTTER.md for running the mobile app"
Write-Host ""
