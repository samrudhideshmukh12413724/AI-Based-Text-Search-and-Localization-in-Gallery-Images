import os
os.environ["TRANSFORMERS_NO_TF"] = "1"
os.environ["USE_TF"] = "0"
os.environ["USE_TORCH"] = "1"
import sys

# Prevent broken tensorflow stub from breaking transformers
sys.modules["tensorflow"] = None

import io
from pathlib import Path
import torch
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import torchvision.transforms as T
from transformers import CLIPTokenizer, CLIPModel

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Standard CLIP Image Normalization
clip_transform = T.Compose([
    T.Resize((224, 224)),
    T.ToTensor(),
    T.Normalize(
        mean=[0.48145466, 0.4578275, 0.40821073],
        std=[0.26862954, 0.26130258, 0.27577711]
    )
])

def create_sample_patches():
    patches = {}

    # 1. Signature Patch
    img_sig = Image.new("RGB", (200, 100), color=(255, 255, 255))
    draw = ImageDraw.Draw(img_sig)
    points = [(20, 60), (45, 25), (60, 75), (85, 30), (110, 65), (140, 40), (175, 55), (190, 45)]
    draw.line(points, fill=(10, 20, 120), width=3, joint="curve")
    draw.line([(30, 80), (170, 80)], fill=(10, 20, 120), width=2)
    patches["signature"] = img_sig

    # 2. Official Stamp / Seal Patch
    img_stamp = Image.new("RGB", (150, 150), color=(255, 255, 255))
    draw = ImageDraw.Draw(img_stamp)
    draw.ellipse([15, 15, 135, 135], outline=(180, 20, 20), width=4)
    draw.ellipse([25, 25, 125, 125], outline=(180, 20, 20), width=2)
    draw.text((38, 65), "VERIFIED", fill=(180, 20, 20))
    patches["official_stamp"] = img_stamp

    # 3. Photograph / Portrait Patch
    img_photo = Image.new("RGB", (150, 180), color=(210, 225, 245))
    draw = ImageDraw.Draw(img_photo)
    draw.ellipse([50, 30, 100, 85], fill=(220, 180, 150))
    draw.ellipse([20, 95, 130, 180], fill=(40, 50, 90))
    patches["portrait_photograph"] = img_photo

    # 4. Text Paragraph Patch
    img_text = Image.new("RGB", (200, 100), color=(255, 255, 255))
    draw = ImageDraw.Draw(img_text)
    for y in range(15, 90, 16):
        draw.line([(15, y), (185, y)], fill=(80, 80, 80), width=2)
    patches["text_paragraph"] = img_text

    return patches

def test_clip_patch_scoring():
    print("=" * 85)
    print("PHASE 3B EXPERIMENT: CLIP REGION / PATCH VISUAL SIMILARITY SCORING")
    print("=" * 85)

    patches = create_sample_patches()
    model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
    tokenizer = CLIPTokenizer.from_pretrained("openai/clip-vit-base-patch32")
    model.eval()

    queries = [
        "a handwritten signature",
        "an official circular stamp seal",
        "a student portrait photograph",
        "plain text paragraph lines"
    ]

    print("\nVisual Queries Tested:")
    for q in queries:
        print(f"  • '{q}'")

    print("\n" + "-" * 85)
    print(f"{'Target Visual Crop':<25} | " + " | ".join([f"{q[:18]:<18}" for q in queries]))
    print("-" * 85)

    # Encode all text queries
    text_inputs = tokenizer(queries, padding=True, return_tensors="pt")
    with torch.no_grad():
        text_features = model.get_text_features(**text_inputs)
        text_features = text_features / text_features.norm(p=2, dim=-1, keepdim=True)

        for patch_name, img in patches.items():
            img_tensor = clip_transform(img).unsqueeze(0)
            img_features = model.get_image_features(img_tensor)
            img_features = img_features / img_features.norm(p=2, dim=-1, keepdim=True)

            # Cosine similarity
            cos_sim = (img_features @ text_features.T).squeeze(0)
            probs = cos_sim.softmax(dim=-1).cpu().numpy()

            row_str = f"{patch_name:<25} | "
            scores = []
            for i, p in enumerate(probs):
                score_val = f"{p * 100:5.1f}%"
                if p == max(probs):
                    score_val = f"★ {score_val}"
                else:
                    score_val = f"  {score_val}"
                scores.append(f"{score_val:<18}")
            row_str += " | ".join(scores)
            print(row_str)

    print("-" * 85)
    print("★ Indicates Top-1 Visual Match per Region Crop")
    print("=" * 85)

if __name__ == "__main__":
    test_clip_patch_scoring()
