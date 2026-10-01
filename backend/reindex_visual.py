import os
os.environ["USE_TF"] = "0"
os.environ["USE_TORCH"] = "1"
os.environ["TRANSFORMERS_NO_TF"] = "1"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
import sys
sys.modules["tensorflow"] = None

from pathlib import Path
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app import database
from app.visual_search import get_visual_search_engine

def main():
    print("Initializing Visual Search Engine...")
    t0 = time.time()
    v_engine = get_visual_search_engine()
    print(f"Engine initialized in {time.time() - t0:.2f}s")
    
    images = database.list_images()
    print(f"Re-indexing visual regions for {len(images)} images in database...")
    sys.stdout.flush()
    
    total_regions = 0
    t_start = time.time()
    for idx, img in enumerate(images, 1):
        img_id = img["id"]
        img_name = img["image_name"]
        img_path = img["image_path"]
        
        if not Path(img_path).exists():
            continue
            
        count = v_engine.index_document(img_id, img_name, img_path)
        total_regions += count
        if idx % 50 == 0 or idx == len(images):
            print(f"  [{idx}/{len(images)}] Indexed {total_regions} regions total...")
            sys.stdout.flush()
            
    print(f"\nRe-indexing completed in {time.time() - t_start:.2f}s!")
    print(f"Total visual regions indexed: {total_regions}")

if __name__ == "__main__":
    main()
