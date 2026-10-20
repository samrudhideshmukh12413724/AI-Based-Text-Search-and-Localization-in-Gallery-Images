"""Rigorous, empirically measured benchmarks for Initial Ingestion vs Incremental Synchronization.

Measures actual wall-clock latencies across different corpus sizes (10, 500, 2000, 5000 images).
Never invents numbers; records actual measured milliseconds.
"""

import time
import requests
import json
from pathlib import Path

BASE_URL = "http://127.0.0.1:8000"

def benchmark_incremental_sync_check():
    """Measures the exact latency of the /images/sync-check endpoint across dataset scales."""
    scales = [10, 100, 500, 2000, 5000]
    results = {}

    for count in scales:
        # Create a realistic mix of existing and new filenames
        files_payload = []
        for i in range(count):
            if i % 2 == 0:
                # Simulated existing file stem
                files_payload.append({"filename": f"doc_{i % 50}.jpg", "size": 150000 + i})
            else:
                # Simulated new file
                files_payload.append({"filename": f"new_unseen_photo_{i}.jpg", "size": 200000 + i})

        t0 = time.perf_counter()
        resp = requests.post(
            f"{BASE_URL}/images/sync-check",
            json={"files": files_payload},
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000

        assert resp.status_code == 200, f"Sync check failed: {resp.text}"
        data = resp.json()
        results[count] = {
            "elapsed_ms": round(elapsed_ms, 2),
            "total_checked": data["total_checked"],
            "already_synced": data["already_synced_count"],
            "missing": data["missing_count"],
        }
        print(f"Scale: {count:<5} items | Sync-Check Latency: {elapsed_ms:>7.2f} ms | Already Synced: {data['already_synced_count']} | Missing: {data['missing_count']}")

    return results

def benchmark_single_image_full_ai_pipeline():
    """Measures exact wall-clock time for one brand-new image through full AI pipeline."""
    sample_images = list(Path("uploads").glob("*.jpg"))
    if not sample_images:
        sample_images = list(Path("uploads").glob("*.png"))
    if not sample_images:
        print("No sample images in uploads to test.")
        return None

    test_file = sample_images[0]
    with open(test_file, "rb") as f:
        file_bytes = f.read()

    print(f"\nBenchmarking Full AI Pipeline on: {test_file.name} ({len(file_bytes)} bytes)")
    times = []
    for run in range(3):
        t0 = time.perf_counter()
        resp = requests.post(
            f"{BASE_URL}/upload",
            files={"file": (f"benchmark_test_run_{run}_{test_file.name}", file_bytes, "image/jpeg")},
            timeout=60,
        )
        elapsed = time.perf_counter() - t0
        assert resp.status_code == 200, f"Upload failed: {resp.text}"
        times.append(elapsed)
        print(f"  Run {run+1}: {elapsed:.3f} s")

    avg_s = sum(times) / len(times)
    print(f"Average Full Pipeline Ingestion Time per new image: {avg_s:.3f} s\n")
    return avg_s

if __name__ == "__main__":
    print("=== DocuLens AI: Performance & Synchronization Benchmark ===")
    # Wait for server ready
    for _ in range(15):
        try:
            r = requests.get(f"{BASE_URL}/health", timeout=2)
            if r.status_code == 200:
                break
        except Exception:
            time.sleep(1)
    
    sync_results = benchmark_incremental_sync_check()
    pipeline_avg = benchmark_single_image_full_ai_pipeline()
