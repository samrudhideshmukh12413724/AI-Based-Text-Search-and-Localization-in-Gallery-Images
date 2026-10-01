"""Quick Phase 1 API smoke test."""

import json
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:8000"


def post_json(path: str, payload: dict) -> dict:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def main() -> None:
    health = urllib.request.urlopen(f"{BASE}/health", timeout=5).read()
    print("Health:", health.decode())

    for query in ("scholarship", "admission", "airplane", "college"):
        result = post_json("/search", {"query": query})
        names = [r["image_name"] for r in result["results"]]
        print(f"Search '{query}': {result['count']} match(es) -> {names}")

    image = Path(__file__).parent / "dataset" / "scholarship.jpg"
    if image.is_file():
        boundary = "----Boundary7MA4YWxkTrZu0gW"
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="scholarship.jpg"\r\n'
            f"Content-Type: image/jpeg\r\n\r\n"
        ).encode() + image.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
        req = urllib.request.Request(
            f"{BASE}/upload",
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            upload = json.loads(resp.read())
        print("Upload OK:", upload["image_name"])
        print("Extracted:", upload["text"].replace("\n", " "))


if __name__ == "__main__":
    main()
