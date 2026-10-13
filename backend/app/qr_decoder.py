import re
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Union, Dict, Any, List
import cv2
import numpy as np


def enrich_qr_payload(payload: str) -> str:
    """
    Enriches QR payload by:
    1. Parsing UPI payment URLs (PhonePe, Paytm, Google Pay, BHIM) to extract merchant/payee name & VPA.
    2. Fetching Web URLs (Google Forms, Websites, Shop Links, Shortlinks, Event Flyers) to extract Title, Meta Description, Headings, & Body text.
    3. Auto-detecting bare domain/shortlink URLs (e.g. forms.gle/..., www.bhelwala.com).
    """
    cleaned = payload.strip()
    if not cleaned:
        return ""

    enriched_parts = [cleaned]

    # Normalize URLs missing http:// or https:// (e.g. forms.gle/xyz, www.shop.com)
    target_url = cleaned
    if not cleaned.lower().startswith(("http://", "https://", "upi:")):
        if cleaned.lower().startswith("www.") or any(domain_ext in cleaned.lower() for domain_ext in [".com", ".in", ".org", ".net", ".io", ".app", ".gle", ".co", ".store", ".shop"]):
            target_url = f"https://{cleaned}"

    # Case 1: UPI Payment Link (PhonePe, Paytm, GPay, BHIM)
    if cleaned.lower().startswith("upi:"):
        try:
            parsed = urllib.parse.urlparse(cleaned)
            params = urllib.parse.parse_qs(parsed.query)
            pn = params.get("pn", [""])[0]  # Payee/Merchant Name
            pa = params.get("pa", [""])[0]  # VPA
            tn = params.get("tn", [""])[0]  # Transaction Note
            
            upi_info = []
            if pn:
                upi_info.append(f"Merchant/Payee: {pn}")
            if pa:
                upi_info.append(f"UPI VPA: {pa}")
            if tn:
                upi_info.append(f"Payment Note: {tn}")
            
            if upi_info:
                enriched_parts.append(f"[UPI Payment Info: {' | '.join(upi_info)}]")
        except Exception:
            pass

    # Case 2: Web Link (Google Form, Website, Event Link, Shop URL, Shortlinks)
    elif target_url.lower().startswith(("http://", "https://")):
        try:
            req = urllib.request.Request(
                target_url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            )
            with urllib.request.urlopen(req, timeout=3.5) as resp:
                content_type = resp.headers.get("Content-Type", "")
                if "text/html" in content_type:
                    html_bytes = resp.read(65536)  # Read first 64KB
                    html_text = html_bytes.decode("utf-8", errors="ignore")
                    
                    # Extract <title>
                    title_match = re.search(r"<title[^>]*>(.*?)</title>", html_text, re.IGNORECASE | re.DOTALL)
                    title = title_match.group(1).strip() if title_match else ""
                    
                    # Extract meta description / og:title / og:description
                    meta_desc = ""
                    meta_match = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\'](.*?)["\']', html_text, re.IGNORECASE)
                    if not meta_match:
                        meta_match = re.search(r'<meta[^>]*content=["\'](.*?)["\'][^>]*name=["\']description["\']', html_text, re.IGNORECASE)
                    if not meta_match:
                        meta_match = re.search(r'<meta[^>]*property=["\']og:(?:title|description)["\'][^>]*content=["\'](.*?)["\']', html_text, re.IGNORECASE)
                    if meta_match:
                        meta_desc = meta_match.group(1).strip()
                    
                    # Extract h1 / h2 headers
                    headers = re.findall(r"<h[12][^>]*>(.*?)</h[12]>", html_text, re.IGNORECASE | re.DOTALL)
                    clean_headers = [re.sub(r"<[^>]+>", "", h).strip() for h in headers if h.strip()][:3]
                    
                    # Strip out script and style tags to extract body text snippet
                    no_script = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html_text, flags=re.IGNORECASE | re.DOTALL)
                    clean_body = re.sub(r"<[^>]+>", " ", no_script)
                    body_words = [w for w in clean_body.split() if len(w) > 2][:40]
                    body_snippet = " ".join(body_words)
                    
                    details = []
                    if title:
                        details.append(f"Title: {title}")
                    if meta_desc:
                        details.append(f"Description: {meta_desc}")
                    if clean_headers:
                        details.append(f"Headings: {' | '.join(clean_headers)}")
                    if body_snippet and len(body_snippet) > 20:
                        details.append(f"Page Text: {body_snippet}")
                    
                    if details:
                        enriched_parts.append(f"[Webpage Content: {' ; '.join(details)}]")
        except Exception:
            pass

    return " ".join(enriched_parts)


def extract_qr_payloads(image_input: Union[str, Path, np.ndarray]) -> Dict[str, Any]:
    """
    Detects, decodes, and enriches QR codes inside an image.
    Fetches web content (Google Forms, Event pages) & parses PhonePe/Paytm UPI merchant details.
    """
    try:
        if isinstance(image_input, (str, Path)):
            img = cv2.imread(str(image_input))
        else:
            img = image_input

        if img is None:
            return {"has_qr": False, "payloads": [], "qr_summary": ""}

        detector = cv2.QRCodeDetector()
        retval, decoded_info, points, _ = detector.detectAndDecodeMulti(img)

        payloads: List[str] = []
        if retval and decoded_info:
            for info in decoded_info:
                if info and info.strip():
                    payloads.append(info.strip())

        if not payloads:
            single_val, pts, _ = detector.detectAndDecode(img)
            if single_val and single_val.strip():
                payloads.append(single_val.strip())

        # Fallback multi-angle orientation scan (90 CW, 180, 270 CW) if no QR code found at 0 deg
        if not payloads:
            rotations = [cv2.ROTATE_90_CLOCKWISE, cv2.ROTATE_180, cv2.ROTATE_90_COUNTERCLOCKWISE]
            for rot_code in rotations:
                rot_img = cv2.rotate(img, rot_code)
                retval, decoded_info, _, _ = detector.detectAndDecodeMulti(rot_img)
                if retval and decoded_info:
                    for info in decoded_info:
                        if info and info.strip():
                            payloads.append(info.strip())
                if not payloads:
                    single_val, _, _ = detector.detectAndDecode(rot_img)
                    if single_val and single_val.strip():
                        payloads.append(single_val.strip())
                if payloads:
                    break

        has_qr = len(payloads) > 0
        enriched_payloads = [enrich_qr_payload(p) for p in payloads]
        summary = " | ".join(enriched_payloads) if has_qr else ""

        return {
            "has_qr": has_qr,
            "payloads": payloads,
            "enriched_payloads": enriched_payloads,
            "qr_summary": summary
        }
    except Exception:
        return {"has_qr": False, "payloads": [], "qr_summary": ""}

