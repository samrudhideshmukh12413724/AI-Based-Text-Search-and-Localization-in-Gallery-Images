import urllib.request
import json
import time
import platform
import sqlite3
import subprocess

print("=== SYSTEM & DATABASE AUDIT ===")
try:
    cpu_info = subprocess.check_output("wmic cpu get name", shell=True).decode().strip().split("\n")
    cpu_name = [line.strip() for line in cpu_info if line.strip() and "Name" not in line][0]
except Exception:
    cpu_name = platform.processor() or "x86_64"
print(f"CPU Model: {cpu_name}")

conn = sqlite3.connect("database/images.db")
c = conn.cursor()
c.execute("SELECT COUNT(*) FROM images")
doc_count = c.fetchone()[0]
print(f"Exact Document Count: {doc_count}")
conn.close()

queries = [
    "1890", "2026", "148",
    "scholrship", "certifcate", "admision",
    "tuition waiver", "financial assistance", "exam schedule", "library book renewal", "sports trial",
    "qr", "stamp", "signature", "seal",
    "dvc", "ollama", "sha", "fees", "bonafide"
]

print("\n=== BENCHMARK: 20 REALISTIC QUERIES ===")
latencies = []
tuition_waiver_data = None

for q in queries:
    req = urllib.request.Request(
        "http://127.0.0.1:8000/search",
        data=json.dumps({"query": q}).encode(),
        headers={"Content-Type": "application/json"}
    )
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=15) as resp:
        d = json.loads(resp.read().decode())
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    latencies.append(elapsed_ms)
    count = d.get("count", 0)
    top_doc = d.get("results", [{}])[0].get("image_name", "None") if count > 0 else "None"
    top_score = d.get("results", [{}])[0].get("similarity_score", 0.0) if count > 0 else 0.0
    print(f"{q:<22} | Count: {count:<3} | Top: {top_doc:<32} | Score: {top_score:<5} | Latency: {elapsed_ms:6.1f} ms")
    if q == "tuition waiver":
        tuition_waiver_data = d

avg_ms = sum(latencies) / len(latencies)
min_ms = min(latencies)
max_ms = max(latencies)
sorted_lat = sorted(latencies)
med_ms = sorted_lat[len(sorted_lat)//2]

print("\n=== BENCHMARK SUMMARY ===")
print(f"Queries Tested: {len(queries)}")
print(f"Average Latency: {avg_ms:.1f} ms")
print(f"Median Latency:  {med_ms:.1f} ms")
print(f"Min Latency:     {min_ms:.1f} ms")
print(f"Max (Worst-Case):{max_ms:.1f} ms")

print("\n=== EXACT TUITION WAIVER RESULT ===")
print("Total Matches:", tuition_waiver_data.get("count"))
for idx, r in enumerate(tuition_waiver_data.get("results", [])[:5]):
    img_name = r.get("image_name")
    score = r.get("similarity_score")
    stype = r.get("search_type")
    img_id = r.get("id")
    print(f"  #{idx+1} ID: {img_id} | Image: {img_name} | Score: {score} | SearchType: {stype}")
