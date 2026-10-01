"""Automates searching on Flutter mobile app running on Android emulator and captures live screenshots."""

import io
import subprocess
import sys
import time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ADB = r"C:\Users\deshm\AppData\Local\Android\Sdk\platform-tools\adb.exe"
ARTIFACT_DIR = Path(r"C:\Users\deshm\.gemini\antigravity\brain\e15ec4a3-03b4-4e1c-9a25-245b6c1ce9eb")

def adb_cmd(cmd):
    full_cmd = f'"{ADB}" {cmd}'
    res = subprocess.run(full_cmd, shell=True, capture_output=True, text=True)
    return res.stdout.strip()

def tap_search_box():
    # Tap the Search Textfield at (450, 890) on 1080x2400 display
    adb_cmd("shell input tap 450 890")
    time.sleep(0.5)

def clear_search_box():
    tap_search_box()
    # Move cursor to end and delete existing text
    adb_cmd("shell input keyevent 123")
    for _ in range(35):
        adb_cmd("shell input keyevent 67")
    time.sleep(0.3)

def type_query_and_search(query_text):
    print(f"\n--- Testing Query on Mobile App: '{query_text}' ---")
    clear_search_box()
    escaped = query_text.replace(" ", "%s")
    adb_cmd(f"shell input text {escaped}")
    time.sleep(0.5)
    # Tap 'SEARCH DOCUMENTS' button at (500, 1050)
    adb_cmd("shell input tap 500 1050")
    print(f"Tapped SEARCH DOCUMENTS button. Waiting for multi-modal response...")
    time.sleep(3.5)

def capture_screenshot(filename):
    out_device = f"/sdcard/{filename}"
    out_local = ARTIFACT_DIR / filename
    adb_cmd(f"shell screencap -p {out_device}")
    adb_cmd(f"pull {out_device} \"{out_local}\"")
    adb_cmd(f"shell rm {out_device}")
    print(f"Captured live screenshot: {out_local.name} ({out_local.stat().st_size} bytes)")
    return out_local

def run_tests():
    print("=" * 80)
    print("STARTING FLUTTER MOBILE LIVE UI VERIFICATION")
    print("=" * 80)

    # 1. Signature visual query
    type_query_and_search("signature")
    capture_screenshot("live_flutter_phase3b_signature.png")

    # Scroll down slightly to see card preview clearly
    adb_cmd("shell input swipe 500 1600 500 1100 300")
    time.sleep(1.0)
    capture_screenshot("live_flutter_phase3b_signature_card.png")

    # 2. Official Stamp visual query
    adb_cmd("shell input swipe 500 800 500 1800 300") # Scroll back up
    time.sleep(0.5)
    type_query_and_search("official stamp")
    capture_screenshot("live_flutter_phase3b_stamp.png")

    # 3. Photograph visual query
    type_query_and_search("photograph")
    capture_screenshot("live_flutter_phase3b_photograph.png")

    # 4. QR Code visual query
    type_query_and_search("QR code")
    capture_screenshot("live_flutter_phase3b_qr_code.png")

    # 5. Scholarship text/semantic query (Phase 1 & 2 regression test)
    type_query_and_search("scholarship")
    capture_screenshot("live_flutter_phase3b_scholarship_text.png")

    print("\n" + "=" * 80)
    print("ALL LIVE MOBILE UI SCREENSHOTS CAPTURED SUCCESSFULLY!")
    print("=" * 80)

if __name__ == "__main__":
    run_tests()
