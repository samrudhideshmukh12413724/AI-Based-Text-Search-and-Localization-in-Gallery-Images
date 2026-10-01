"""BLIP Image Captioning Module.

Generates natural language text descriptions/captions for images.
Enables visual queries (e.g., 'honey bee', 'beach sunset', 'white car')
even when no OCR text is written on the image.
"""

from pathlib import Path
from typing import Union, Optional
from PIL import Image
import torch

_blip_processor = None
_blip_model = None
_blip_initialized = False


def _init_blip():
    """Lazy loader for BLIP Image Captioning model."""
    global _blip_processor, _blip_model, _blip_initialized
    if _blip_initialized:
        return
    _blip_initialized = True
    try:
        from transformers import BlipProcessor, BlipForConditionalGeneration
        _blip_processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
        _blip_model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")
        _blip_model.eval()
    except Exception as e:
        print(f"[Captioning] Note: BLIP model lazy-init deferred or operating in fallback mode: {e}")


def generate_caption(image_input: Union[str, Path, Image.Image]) -> str:
    """
    Generates a natural language caption for the given image.
    Returns descriptive string caption.
    """
    try:
        if isinstance(image_input, (str, Path)):
            p = Path(image_input)
            if not p.is_file():
                return ""
            raw_image = Image.open(p).convert("RGB")
        elif isinstance(image_input, Image.Image):
            raw_image = image_input.convert("RGB")
        else:
            return ""

        _init_blip()

        if _blip_processor is not None and _blip_model is not None:
            with torch.no_grad():
                inputs = _blip_processor(raw_image, return_tensors="pt")
                out = _blip_model.generate(**inputs, max_new_tokens=30)
                caption = _blip_processor.decode(out[0], skip_special_tokens=True)
                return caption.strip()

        # Rule-based visual fallback caption based on image dimensions and properties
        w, h = raw_image.size
        aspect = "landscape" if w > h else ("portrait" if h > w else "square")
        return f"photo image in {aspect} format ({w}x{h})"

    except Exception as e:
        print(f"[Captioning] Error generating caption: {e}")
        return ""
