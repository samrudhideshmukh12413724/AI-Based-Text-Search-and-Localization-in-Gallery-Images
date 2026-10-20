"""
Asynchronous Priority-Aware Sync Worker & Multi-Threaded Processing Queue.

Decouples network photo uploading from heavy CPU/GPU AI processing (OCR, NER, QR, CLIP, BLIP).
Features:
- Document & Temporal Priority: Prioritizes important documents (PAN card, Aadhaar, receipts,
  college forms, certificates) and recent photos so users can search newly added documents in seconds
  without waiting for thousands of gallery photos to finish.
- Controlled Safe Parallelism: Runs a 2-worker execution pool preventing laptop CPU/RAM overload
  while doubling background ingestion throughput.
- Immediate Searchability: As soon as an image's OCR and semantic embeddings finish, it is
  immediately committed to SQLite, appended to in-memory embeddings, and cache-invalidated
  so live queries find it right away.
"""

import itertools
import queue
import re
import threading
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, Optional, List

from app import database
from app.duplicates.detector import check_duplicate
from app.ocr.ocr_engine import extract_text_adaptive
from app.entities import extract_entities, extract_urls
from app.search import extract_image_metadata
from app.visual_detector import get_visual_detector
from app.qr_decoder import extract_qr_payloads
from app.steganography import extract_stego_text, compute_document_hash
from app.captioning import generate_caption
from app.visual_search import get_visual_search_engine
from app.semantic_search import append_single_embedding


PRIORITY_DOCUMENT_KEYWORDS = {
    "pan", "aadhaar", "aadhar", "receipt", "invoice", "bill", "cert", "certificate",
    "marksheet", "id", "card", "college", "exam", "admit", "admission", "fees",
    "fee", "salary", "form", "pass", "bonafide", "hallticket", "hall_ticket",
    "transcript", "degree", "diploma", "ration", "voter", "driving", "license",
    "passport", "challan", "bank", "statement", "document", "doc", "tuition",
    "screenshot", "screen", "scan", "cam"
}


@dataclass
class SyncJob:
    image_id: int
    dest_path: Path
    safe_name: str
    user_id: int
    priority: int = 1


class SyncWorkerManager:
    def __init__(self, num_workers: int = 2):
        self._queue: queue.PriorityQueue = queue.PriorityQueue()
        self._seq = itertools.count()
        self._lock = threading.Lock()
        self._num_workers = num_workers
        self._workers: List[threading.Thread] = []

        self._total_submitted: int = 0
        self._total_completed: int = 0
        self._total_failed: int = 0
        self._active_jobs: Dict[int, str] = {}  # image_id -> safe_name
        self._ensure_workers_started()

    def _ensure_workers_started(self):
        with self._lock:
            # Clean up dead threads
            self._workers = [w for w in self._workers if w.is_alive()]
            while len(self._workers) < self._num_workers:
                idx = len(self._workers) + 1
                t = threading.Thread(
                    target=self._worker_loop,
                    name=f"DocuLens-SyncWorker-{idx}",
                    daemon=True,
                )
                t.start()
                self._workers.append(t)

    def enqueue(
        self,
        image_id: int,
        dest_path: Path,
        safe_name: str,
        user_id: int,
        priority: Optional[int] = None,
    ) -> None:
        """
        Enqueues an uploaded image for asynchronous background AI indexing.
        Priority:
          0 = Urgent/Important (PAN card, Aadhaar, receipts, college documents, recent)
          1 = Standard (recent photos)
          2 = Bulk archive (older gallery photos)
        """
        self._ensure_workers_started()

        if priority is None:
            name_lower = safe_name.lower()
            # Fast keyword heuristic for document priority
            tokens = set(re.findall(r"[a-z0-9]+", name_lower))
            if tokens & PRIORITY_DOCUMENT_KEYWORDS:
                priority = 0
            else:
                priority = 1

        job = SyncJob(
            image_id=image_id,
            dest_path=dest_path,
            safe_name=safe_name,
            user_id=user_id,
            priority=priority,
        )

        with self._lock:
            self._total_submitted += 1
            seq = next(self._seq)

        self._queue.put((priority, seq, job))

    def get_status(self) -> Dict[str, Any]:
        """Returns live multi-worker sync diagnostics and active task lists for mobile UI."""
        with self._lock:
            q_size = self._queue.qsize()
            active_files = list(self._active_jobs.values())
            is_active = (q_size > 0) or (len(active_files) > 0)
            return {
                "queued": q_size,
                "active": len(active_files),
                "active_files": active_files,
                "current_file": active_files[0] if active_files else None,
                "completed": self._total_completed,
                "failed": self._total_failed,
                "total": self._total_submitted,
                "is_active": is_active,
                "num_workers": self._num_workers,
            }

    def _worker_loop(self):
        while True:
            try:
                priority, seq, job = self._queue.get()
                if job is None:
                    break

                with self._lock:
                    self._active_jobs[job.image_id] = job.safe_name

                database.update_image_indexing_status(job.image_id, "indexing")
                self._process_single_job(job)

                with self._lock:
                    self._total_completed += 1
                    self._active_jobs.pop(job.image_id, None)

                database.update_image_indexing_status(job.image_id, "completed")

                # Invalidate search cache so newly completed document is searchable immediately
                try:
                    from app.main import invalidate_search_cache
                    invalidate_search_cache()
                except Exception:
                    pass

            except Exception as e:
                print(f"[SyncWorker Error] Processing failed for job: {e}")
                traceback.print_exc()
                with self._lock:
                    self._total_failed += 1
                    if "job" in locals() and job:
                        self._active_jobs.pop(job.image_id, None)
                try:
                    if "job" in locals() and job:
                        database.update_image_indexing_status(job.image_id, "failed")
                except Exception:
                    pass
            finally:
                self._queue.task_done()

    def _process_single_job(self, job: SyncJob):
        dest_path = job.dest_path
        if not dest_path.exists():
            print(f"[SyncWorker] Destination file {dest_path} not found on disk, skipping.")
            return

        # 1. Duplicate & Near-Duplicate Detection (Phase 4 Step 5)
        dupe_res = check_duplicate(dest_path)
        is_dupe = 1 if dupe_res.get("is_duplicate") else 0
        canon_id = dupe_res.get("canonical_id")
        dupe_sim = float(dupe_res.get("similarity", 0.0)) if is_dupe else 0.0
        dupe_match_type = dupe_res.get("match_type", "unique") if is_dupe else "unique"
        sha256_hash = dupe_res.get("sha256_hash", "")
        phash = dupe_res.get("phash", "")
        doc_sha256 = sha256_hash or compute_document_hash(dest_path)

        # 2. Extract Steganography payload
        stego_text = extract_stego_text(dest_path)

        # 3. EasyOCR Multi-Orientation Adaptive Text Extraction (Phase 1 & 2)
        try:
            ocr_res = extract_text_adaptive(dest_path)
            text = ocr_res.get("text", "")
            word_boxes = ocr_res.get("word_boxes", [])
        except Exception as ocr_err:
            print(f"[SyncWorker OCR Exception] {ocr_err}")
            text = "(no text detected)"
            word_boxes = []

        if not text.strip():
            text = "(no text detected)"

        # 4. Extract Structured Entities (NER)
        entities = extract_entities(text)

        # 5. Extract Technical & Temporal Metadata
        img_meta = extract_image_metadata(dest_path, entities)

        # 6. OpenCV Visual Object Detection
        detector = get_visual_detector()
        vis_res = detector.detect_visual_objects(dest_path)
        has_visual = 1 if vis_res.get("detected") else 0

        # 7. QR Code Extraction
        qr_res = extract_qr_payloads(dest_path)
        qr_summary = qr_res.get("qr_summary", "")
        if qr_summary:
            for qu in extract_urls(qr_summary):
                entities.setdefault("urls", [])
                if qu not in entities["urls"]:
                    entities["urls"].append(qu)
        if qr_res.get("detected"):
            has_visual = 1
            vis_res["detected"] = True
            vis_objs = vis_res.setdefault("objects", [])
            for qro in qr_res.get("qr_objects", []):
                vis_objs.append(qro)
            if qr_res.get("enriched"):
                entities["qr_metadata"] = qr_res.get("enriched")

        # 8. Update Database with full extracted metadata
        database.update_image_ocr_text(job.image_id, text)
        database.update_image_ocr_boxes(job.image_id, word_boxes)
        database.update_image_entities(job.image_id, entities)
        database.update_image_visual_metadata(job.image_id, has_visual, vis_res)
        database.update_image_metadata(
            image_id=job.image_id,
            file_size_bytes=img_meta["file_size_bytes"],
            image_width=img_meta["image_width"],
            image_height=img_meta["image_height"],
            file_format=img_meta["file_format"],
            file_modified_at=img_meta["file_modified_at"],
            exif_created_at=img_meta["exif_created_at"],
            primary_date=img_meta["primary_date"],
        )
        database.update_multimodal_payloads(
            image_id=job.image_id,
            blip_caption="",
            qr_payload=qr_summary,
            stego_payload=stego_text,
        )
        database.update_image_duplicates(
            image_id=job.image_id,
            sha256_hash=doc_sha256,
            phash=phash,
            is_duplicate=is_dupe,
            canonical_image_id=canon_id,
            duplicate_similarity=dupe_sim,
            duplicate_match_type=dupe_match_type,
        )

        # 9. Incremental Semantic NLP Embedding (immediately searchable!)
        row = database.get_image_by_id(job.image_id)
        if row:
            append_single_embedding(row)

        # 10. Background Visual Region Indexing & BLIP Caption
        try:
            cap = generate_caption(dest_path)
            if cap:
                database.update_multimodal_payloads(
                    image_id=job.image_id,
                    blip_caption=cap,
                    qr_payload=qr_summary,
                    stego_payload=stego_text,
                )
        except Exception as e:
            print(f"[SyncWorker BLIP Note] {e}")

        try:
            v_search = get_visual_search_engine()
            v_search.index_document(job.image_id, job.safe_name, str(dest_path))
        except Exception as e:
            print(f"[SyncWorker Visual Indexing Note] {e}")


# Singleton instance
_sync_worker: Optional[SyncWorkerManager] = None


def get_sync_worker() -> SyncWorkerManager:
    global _sync_worker
    if _sync_worker is None:
        _sync_worker = SyncWorkerManager(num_workers=2)
    return _sync_worker
