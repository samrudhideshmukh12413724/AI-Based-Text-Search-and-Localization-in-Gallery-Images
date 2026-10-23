"""XSS (Cross-Site Scripting) Protection & Input Sanitization Engine.

Protects frontend & mobile clients against XSS payloads, script injection,
and malicious HTML/JS tags embedded in OCR text, user search queries, or QR payloads.
"""

import html
import re
from typing import Any, Union, Dict, List


def sanitize_text(input_val: Union[str, None]) -> str:
    """
    Sanitizes string input to prevent Cross-Site Scripting (XSS).
    1. Strips out dangerous HTML tags (<script>, <iframe>, <object>, <embed>, <applet>, etc.).
    2. Removes event handlers (onerror=, onload=, onclick=, javascript:).
    3. HTML-escapes reserved characters (&, <, >, ", ').
    """
    if input_val is None:
        return ""
    
    text = str(input_val).strip()
    if not text:
        return ""

    # Remove dangerous tags completely
    text = re.sub(r"<(script|iframe|object|embed|applet|meta|link|style)[^>]*>.*?</\1>", "", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<(script|iframe|object|embed|applet|meta|link|style)[^>]*>", "", text, flags=re.IGNORECASE)
    
    # Strip JavaScript event attributes (onerror=, onload=, etc.) and javascript: URIs
    text = re.sub(r"on\w+\s*=\s*[\"'].*?[\"']", "", text, flags=re.IGNORECASE)
    text = re.sub(r"on\w+\s*=\s*[^>\s]+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"javascript:\s*", "", text, flags=re.IGNORECASE)

    # HTML-escape special characters
    return html.escape(text, quote=True)


def sanitize_dict_fields(data: Dict[str, Any], target_fields: List[str]) -> Dict[str, Any]:
    """Recursively sanitizes specified string fields inside a dictionary payload."""
    sanitized = data.copy()
    for k, v in sanitized.items():
        if k in target_fields and isinstance(v, str):
            sanitized[k] = sanitize_text(v)
        elif isinstance(v, dict):
            sanitized[k] = sanitize_dict_fields(v, target_fields)
    return sanitized
