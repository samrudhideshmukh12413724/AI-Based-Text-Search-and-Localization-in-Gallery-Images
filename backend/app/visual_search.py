"""Phase 3B: Open-Vocabulary Visual Region Search & Zero-Shot Patch Embeddings using CLIP ViT-B/32."""

import os
os.environ["TRANSFORMERS_NO_TF"] = "1"
os.environ["USE_TF"] = "0"
os.environ["USE_TORCH"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
import sys

# Prevent broken TF stub from interfering
sys.modules["tensorflow"] = None

import json
from pathlib import Path
from typing import List, Dict, Any, Tuple
import numpy as np
import torch
import torchvision.transforms as T
from PIL import Image
from transformers import CLIPModel, CLIPTokenizer

from app import database
from app.visual_region_extractor import get_visual_region_extractor, VisualRegion

MODEL_NAME = "openai/clip-vit-base-patch32"

# Standard CLIP Preprocessing Transform
clip_transform = T.Compose([
    T.Resize((224, 224), interpolation=T.InterpolationMode.BICUBIC),
    T.ToTensor(),
    T.Normalize(
        mean=[0.48145466, 0.4578275, 0.40821073],
        std=[0.26862954, 0.26130258, 0.27577711]
    )
])


class VisualSearchEngine:
    """Zero-shot visual search engine using CLIP region embeddings."""

    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        try:
            self.model = CLIPModel.from_pretrained(MODEL_NAME, local_files_only=True).to(self.device)
            self.tokenizer = CLIPTokenizer.from_pretrained(MODEL_NAME, local_files_only=True)
        except Exception:
            self.model = CLIPModel.from_pretrained(MODEL_NAME).to(self.device)
            self.tokenizer = CLIPTokenizer.from_pretrained(MODEL_NAME)
        self.model.eval()
        self.extractor = get_visual_region_extractor()

    def encode_crops(self, crops: List[Image.Image]) -> np.ndarray:
        """Encodes a list of PIL Image crops into normalized 512-dim numpy vectors."""
        if not crops:
            return np.empty((0, 512), dtype=np.float32)

        tensors = torch.stack([clip_transform(crop) for crop in crops]).to(self.device)
        with torch.no_grad():
            features = self.model.get_image_features(tensors)
            features = features / features.norm(p=2, dim=-1, keepdim=True)
        return features.cpu().numpy().astype(np.float32)

    def encode_query(self, query: str) -> np.ndarray:
        """Encodes a natural language visual query into a normalized 512-dim vector with prompt ensembling."""
        clean_q = query.strip()
        # Prompt ensemble templates
        prompts = [
            f"a document containing {clean_q}",
            f"a photo or image of {clean_q}",
            f"an official {clean_q}",
            f"{clean_q}"
        ]

        text_inputs = self.tokenizer(prompts, padding=True, return_tensors="pt").to(self.device)
        with torch.no_grad():
            text_features = self.model.get_text_features(**text_inputs)
            text_features = text_features / text_features.norm(p=2, dim=-1, keepdim=True)
            # Average prompts and re-normalize
            ensemble_vec = text_features.mean(dim=0, keepdim=True)
            ensemble_vec = ensemble_vec / ensemble_vec.norm(p=2, dim=-1, keepdim=True)

        return ensemble_vec.cpu().numpy().astype(np.float32)

    def index_document(self, image_id: int, image_name: str, image_path: str) -> int:
        """Extracts candidate visual regions from an image, generates embeddings, and saves to database."""
        regions = self.extractor.extract_regions(image_path)
        if not regions:
            return 0

        crops = [r.crop_image for r in regions]
        embeddings = self.encode_crops(crops)

        records = []
        for i, reg in enumerate(regions):
            records.append({
                "source": reg.source,
                "location_desc": reg.location_desc,
                "bbox": reg.bbox,
                "normalized_bbox": reg.normalized_bbox,
                "embedding_blob": embeddings[i].tobytes(),
            })

        database.save_visual_regions(image_id, image_name, records)
        return len(records)

    def index_all_documents(self) -> int:
        """Re-indexes visual regions for all images stored in the database."""
        images = database.list_images()
        total_indexed = 0
        for img in images:
            p = img["image_path"]
            if Path(p).exists():
                count = self.index_document(img["id"], img["image_name"], p)
                total_indexed += count
        return total_indexed

    def search(
        self,
        query: str,
        top_k: int = 10,
        threshold: float = 0.245,
        use_refinement: bool = True,
        bypass_cache: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Searches all indexed visual regions for the best matching visual objects.
        When use_refinement=True (default), delegates to modular open-vocabulary VisualRefiner.
        When use_refinement=False, executes the Phase 3B baseline implementation.
        """
        if use_refinement:
            from app.visual_refinement import get_visual_refiner
            refiner = get_visual_refiner(self)
            return refiner.search(query=query, top_k=top_k, threshold=threshold, bypass_cache=bypass_cache)

        all_regions = database.get_all_visual_regions()
        if not all_regions:
            return []

        query_vec = self.encode_query(query)  # (1, 512)

        # Compute similarities & group by image_id
        # image_id -> list of (sim, region_dict)
        doc_patches: Dict[int, List[Tuple[float, Dict[str, Any]]]] = {}

        for r in all_regions:
            emb_blob = r["embedding_blob"]
            vec = np.frombuffer(emb_blob, dtype=np.float32).reshape(1, 512)
            sim = float(np.dot(query_vec, vec.T)[0, 0])

            img_id = r["image_id"]
            if sim >= threshold:
                if img_id not in doc_patches:
                    doc_patches[img_id] = []
                doc_patches[img_id].append((sim, r))

        # Proposal source taxonomy
        GENERIC_SOURCES = {"full_doc", "card_proposal", "quadrant_anchor"}
        SPECIFIC_SOURCES = {
            "color_region",
            "contour_graphic",
            "card_enclosure",
            "qr_detector",
            "fine_contour",
        }

        doc_matches = []
        for img_id, patches in doc_patches.items():
            # ---------------------------------------------------------
            # Step 1B: Source-Aware, Relevance-First Ranking
            # ---------------------------------------------------------
            # 1. Relevance first: Document retrieval score is the highest
            #    raw CLIP similarity. No blanket penalties, preserving
            #    full-scene groundings (e.g. mountain landscape).
            # 2. Localization second: When the highest-scoring region is a
            #    generic fallback (full_doc, card_proposal, quadrant_anchor),
            #    prefer a detected specific visual region if its relevance
            #    score is very close to the top score.
            # ---------------------------------------------------------
            patches.sort(key=lambda x: x[0], reverse=True)
            doc_sim, top_r = patches[0]

            best_sim, best_r = doc_sim, top_r

            # If top region is generic, look for a specific detected candidate with close relevance
            if top_r.get("region_source") in GENERIC_SOURCES and len(patches) > 1:
                for sub_sim, sub_r in patches[1:]:
                    if sub_r.get("region_source") in SPECIFIC_SOURCES:
                        # Area-aware yield:
                        # For full_doc: substantial objects (>= 6% area) get generous tolerance (Δ <= 0.025);
                        # small slivers (< 6% area) get strict tolerance (Δ <= 0.012) to protect full landscapes.
                        # For card/quadrant stripes: allow Δ <= 0.025.
                        if top_r.get("region_source") == "full_doc":
                            norm_bbox = sub_r.get("normalized_bbox", {})
                            norm_area = norm_bbox.get("width", 0.0) * norm_bbox.get("height", 0.0)
                            tolerance = 0.025 if norm_area >= 0.06 else 0.012
                        else:
                            tolerance = 0.025

                        if (doc_sim - sub_sim) <= tolerance:
                            best_sim, best_r = sub_sim, sub_r
                            break

            doc_matches.append({
                "id": img_id,
                "image_name": best_r["image_name"],
                "image_path": best_r["image_path"],
                "extracted_text": best_r.get("extracted_text", ""),
                "category": best_r.get("category", ""),
                "similarity_score": round(doc_sim, 3),  # Full relevance preserved for retrieval ranking
                "best_region": {
                    "source": best_r["region_source"],
                    "location_desc": best_r["location_desc"],
                    "bbox": best_r["bbox"],
                    "normalized_bbox": best_r["normalized_bbox"],
                    "confidence": round(best_sim, 3),
                    "label": f"Visual Match: {best_r['location_desc']}",
                }
            })

        # Sort descending by score
        doc_matches.sort(key=lambda x: x["similarity_score"], reverse=True)
        return doc_matches[:top_k]


_engine = None


def get_visual_search_engine() -> VisualSearchEngine:
    global _engine
    if _engine is None:
        _engine = VisualSearchEngine()
    return _engine
