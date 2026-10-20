import re
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Union, Dict, Any, List, Optional
import cv2
import numpy as np


# UPI Payment Provider VPA Suffix Mapping
UPI_PROVIDER_MAP = {
    "@ybl": "PhonePe",
    "@ibl": "PhonePe",
    "@axl": "PhonePe",
    "@okhdfcbank": "Google Pay",
    "@okaxis": "Google Pay",
    "@oksbi": "Google Pay",
    "@okicici": "Google Pay",
    "@paytm": "Paytm",
    "@ptaxis": "Paytm",
    "@pthdfc": "Paytm",
    "@ptyes": "Paytm",
    "@upi": "BHIM",
    "@apl": "Amazon Pay",
    "@yapl": "Amazon Pay",
    "@axisb": "Cred",
    "@cred": "Cred",
    "@bharatpe": "BharatPe",
    "@postbank": "India Post Payments Bank",
}


def _identify_provider_from_vpa_or_url(vpa: str, raw_url: str) -> Optional[str]:
    """Identifies payment application or provider from UPI VPA suffix or URL scheme."""
    vpa_lower = vpa.lower().strip()
    url_lower = raw_url.lower().strip()

    # Check URL schemes / domains
    if "phonepe" in url_lower or "phon.pe" in url_lower:
        return "PhonePe"
    if "paytm" in url_lower:
        return "Paytm"
    if "tez://" in url_lower or "gpay://" in url_lower or "google" in url_lower:
        return "Google Pay"
    if "bharatpe" in url_lower:
        return "BharatPe"

    # Check VPA handle
    for handle, provider in UPI_PROVIDER_MAP.items():
        if vpa_lower.endswith(handle):
            return provider

    return None


def parse_emvco_tlv(payload: str) -> Dict[str, str]:
    """
    Parses EMVCo / BharatQR Tag-Length-Value payload (starts with '000201').
    Extracts tags like:
      - Tag 59: Merchant Name
      - Tag 60: Merchant City
      - Tag 26-51: Merchant Account Information (UPI VPAs)
    """
    tags: Dict[str, str] = {}
    i = 0
    payload_len = len(payload)
    while i + 4 <= payload_len:
        tag = payload[i:i+2]
        try:
            length = int(payload[i+2:i+4])
        except ValueError:
            break
        val_start = i + 4
        val_end = val_start + length
        if val_end > payload_len:
            break
        value = payload[val_start:val_end]
        tags[tag] = value
        i = val_end
    return tags


def parse_vcard_or_mecard(payload: str) -> Dict[str, str]:
    """Extracts name, org, and phone from vCard or MeCard format."""
    data = {}
    # MeCard format: MECARD:N:Name;ORG:Company;TEL:1234567890;;
    if payload.upper().startswith("MECARD:"):
        n_match = re.search(r"\bN:([^;]+)", payload, re.IGNORECASE)
        org_match = re.search(r"\bORG:([^;]+)", payload, re.IGNORECASE)
        tel_match = re.search(r"\bTEL:([^;]+)", payload, re.IGNORECASE)
        if n_match:
            data["name"] = n_match.group(1).strip()
        if org_match:
            data["org"] = org_match.group(1).strip()
        if tel_match:
            data["phone"] = tel_match.group(1).strip()
    # vCard format
    elif "BEGIN:VCARD" in payload.upper():
        fn_match = re.search(r"^FN:(.*?)$", payload, re.IGNORECASE | re.MULTILINE)
        org_match = re.search(r"^ORG:(.*?)$", payload, re.IGNORECASE | re.MULTILINE)
        tel_match = re.search(r"^TEL[^:]*:(.*?)$", payload, re.IGNORECASE | re.MULTILINE)
        if fn_match:
            data["name"] = fn_match.group(1).strip()
        if org_match:
            data["org"] = org_match.group(1).strip()
        if tel_match:
            data["phone"] = tel_match.group(1).strip()
    return data


def enrich_qr_payload(payload: str, fetch_web: bool = False) -> Dict[str, Any]:
    """
    Enriches QR payload by:
    1. Parsing UPI payment URLs (case-insensitive parameters) for Merchant/Payee name, VPA, and Provider.
    2. Parsing EMVCo / BharatQR TLV payloads for Merchant Name (Tag 59).
    3. Parsing vCard / MeCard payloads for person / business identity.
    4. Guarding against identity hallucination when only an identifier is present.
    5. Fetching Web URLs (safe fallback) to extract title and description.
    """
    cleaned = payload.strip()
    if not cleaned:
        return {
            "raw": "",
            "enriched_text": "",
            "merchants": [],
            "payees": [],
            "providers": [],
            "vpas": [],
            "is_payment": False,
        }

    merchants: List[str] = []
    payees: List[str] = []
    providers: List[str] = []
    vpas: List[str] = []
    details: List[str] = []
    is_payment = False

    # Case 1: UPI Payment Link (PhonePe, Paytm, Google Pay, BHIM)
    if cleaned.lower().startswith("upi:"):
        is_payment = True
        try:
            parsed = urllib.parse.urlparse(cleaned)
            # Case-insensitive parameter extraction
            raw_qs = parsed.query
            params: Dict[str, List[str]] = {}
            for part in raw_qs.split("&"):
                if "=" in part:
                    k, v = part.split("=", 1)
                    k_clean = k.strip().lower()
                    v_clean = urllib.parse.unquote_plus(v.strip())
                    params.setdefault(k_clean, []).append(v_clean)

            pn = params.get("pn", [""])[0].strip()  # Payee / Merchant Name
            pa = params.get("pa", [""])[0].strip()  # VPA
            tn = params.get("tn", [""])[0].strip()  # Note
            mc = params.get("mc", [""])[0].strip()  # Merchant Category Code

            if pa:
                vpas.append(pa)
                provider = _identify_provider_from_vpa_or_url(pa, cleaned)
                if provider:
                    providers.append(provider)

            # Assign merchant or payee name strictly if present
            if pn:
                # If merchant category code exists or MCC indicates business, categorize as merchant
                if mc or any(kw in pn.lower() for kw in ["chaat", "wala", "shop", "store", "hotel", "restaurant", "mart", "enterprise", "agency", "services"]):
                    merchants.append(pn)
                else:
                    payees.append(pn)
                    merchants.append(pn)  # Also indexable under merchant/payee

            upi_info = []
            if pn:
                upi_info.append(f"Merchant/Payee: {pn}")
            if pa:
                upi_info.append(f"UPI VPA: {pa}")
            if providers:
                upi_info.append(f"Provider: {', '.join(set(providers))}")
            if tn:
                upi_info.append(f"Payment Note: {tn}")

            if upi_info:
                details.append(f"[UPI Payment Info: {' | '.join(upi_info)}]")
        except Exception:
            pass

    # Case 2: EMVCo / BharatQR Specification (starts with '000201')
    elif cleaned.startswith("000201"):
        is_payment = True
        try:
            tags = parse_emvco_tlv(cleaned)
            merchant_name = tags.get("59", "").strip()
            merchant_city = tags.get("60", "").strip()
            if merchant_name:
                merchants.append(merchant_name)
            
            # Inspect sub-tags 26-51 for UPI VPAs
            for t in range(26, 52):
                tag_str = f"{t:02d}"
                if tag_str in tags:
                    sub_val = tags[tag_str]
                    sub_tlv = parse_emvco_tlv(sub_val)
                    sub_vpa = sub_tlv.get("01", "")
                    if "@" in sub_vpa:
                        vpas.append(sub_vpa)
                        prov = _identify_provider_from_vpa_or_url(sub_vpa, cleaned)
                        if prov:
                            providers.append(prov)

            bqr_info = []
            if merchant_name:
                bqr_info.append(f"Merchant: {merchant_name}")
            if merchant_city:
                bqr_info.append(f"City: {merchant_city}")
            if vpas:
                bqr_info.append(f"VPA: {', '.join(vpas)}")
            if providers:
                bqr_info.append(f"Provider: {', '.join(set(providers))}")

            if bqr_info:
                details.append(f"[BharatQR / EMVCo Info: {' | '.join(bqr_info)}]")
        except Exception:
            pass

    # Case 3: Contact Card (vCard / MeCard)
    elif "BEGIN:VCARD" in cleaned.upper() or cleaned.upper().startswith("MECARD:"):
        card_data = parse_vcard_or_mecard(cleaned)
        if card_data.get("name"):
            payees.append(card_data["name"])
        if card_data.get("org"):
            merchants.append(card_data["org"])
        card_info = [f"{k.capitalize()}: {v}" for k, v in card_data.items() if v]
        if card_info:
            details.append(f"[Contact Card: {' | '.join(card_info)}]")

    # Case 4: Web URL (Google Forms, Websites, Shop Links) - Fast local parsing (0ms)
    target_url = cleaned
    if not cleaned.lower().startswith(("http://", "https://", "upi:")) and not cleaned.startswith("000201"):
        if cleaned.lower().startswith("www.") or any(domain_ext in cleaned.lower() for domain_ext in [".com", ".in", ".org", ".net", ".io", ".app", ".gle", ".co", ".store", ".shop"]):
            target_url = f"https://{cleaned}"

    if target_url.lower().startswith(("http://", "https://")):
        try:
            parsed_u = urllib.parse.urlparse(target_url)
            domain = parsed_u.netloc.replace("www.", "").strip()
            path_kw = [tok for tok in re.split(r"[/_\-\.\?&=]+", parsed_u.path) if len(tok) >= 3 and not tok.isdigit()]
            web_summary = []
            if domain:
                web_summary.append(f"Domain: {domain}")
            if path_kw:
                web_summary.append(f"Keywords: {' '.join(path_kw[:4])}")
            if web_summary:
                details.append(f"[Web Link: {' | '.join(web_summary)}]")
        except Exception:
            pass

        if fetch_web:
            try:
                req = urllib.request.Request(
                    target_url,
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                )
                with urllib.request.urlopen(req, timeout=1.0) as resp:
                    content_type = resp.headers.get("Content-Type", "")
                    if "text/html" in content_type:
                        html_bytes = resp.read(32768)
                        html_text = html_bytes.decode("utf-8", errors="ignore")
                        title_match = re.search(r"<title[^>]*>(.*?)</title>", html_text, re.IGNORECASE | re.DOTALL)
                        if title_match:
                            details.append(f"[Web Title: {title_match.group(1).strip()}]")
            except Exception:
                pass

    # Assemble enriched textual representation
    enriched_text = f"{cleaned} {' '.join(details)}".strip()

    return {
        "raw": cleaned,
        "enriched_text": enriched_text,
        "merchants": sorted(list(set(merchants))),
        "payees": sorted(list(set(payees))),
        "providers": sorted(list(set(providers))),
        "vpas": sorted(list(set(vpas))),
        "is_payment": is_payment,
    }


def _get_aruco_detector():
    """Lazy instantiation of QRCodeDetectorAruco if available in opencv-contrib / opencv >= 4.7.0."""
    if hasattr(cv2, "QRCodeDetectorAruco"):
        try:
            return cv2.QRCodeDetectorAruco()
        except Exception:
            return None
    return None


def extract_qr_payloads(image_input: Union[str, Path, np.ndarray]) -> Dict[str, Any]:
    """
    Robust Dual-Detector QR Engine:
    1. Primary: cv2.QRCodeDetectorAruco (resilient against perspective, blur, and occlusions).
    2. Fallback: cv2.QRCodeDetector with multi-pass preprocessing (CLAHE, Otsu, 1.5x upscaling, multi-angle rotations).
    3. Retains individual bounding box coordinates and extracts structured merchant/payee metadata.
    """
    try:
        if isinstance(image_input, (str, Path)):
            img = cv2.imread(str(image_input))
        else:
            img = image_input

        if img is None:
            return {
                "has_qr": False,
                "count": 0,
                "payloads": [],
                "enriched_payloads": [],
                "merchants": [],
                "payees": [],
                "providers": [],
                "vpas": [],
                "qr_summary": "",
                "qr_objects": [],
            }

        h_orig, w_orig = img.shape[:2]
        decoded_entries: List[Dict[str, Any]] = []  # List of {"payload": str, "points": np.ndarray}
        seen_payloads = set()

        aruco_detector = _get_aruco_detector()
        standard_detector = cv2.QRCodeDetector()

        def _try_detect(detector, canvas, tag=""):
            if detector is None or canvas is None:
                return
            try:
                retval, decoded_info, points, _ = detector.detectAndDecodeMulti(canvas)
                if retval and decoded_info:
                    for i, info in enumerate(decoded_info):
                        val = str(info).strip()
                        if val and val not in seen_payloads:
                            pts = points[i] if (points is not None and len(points) > i) else None
                            seen_payloads.add(val)
                            decoded_entries.append({"payload": val, "points": pts, "method": f"{tag}_multi"})
            except Exception:
                pass

            if not decoded_entries:
                try:
                    single_val, pts, _ = detector.detectAndDecode(canvas)
                    val = str(single_val).strip()
                    if val and val not in seen_payloads:
                        seen_payloads.add(val)
                        decoded_entries.append({"payload": val, "points": pts, "method": f"{tag}_single"})
                except Exception:
                    pass

        # Pass 1: Try QRCodeDetectorAruco on original image
        if aruco_detector:
            _try_detect(aruco_detector, img, "aruco_native")

        # Pass 2: Try standard QRCodeDetector on original image
        if not decoded_entries:
            _try_detect(standard_detector, img, "standard_native")

        # Pass 3: Preprocessed Variants (CLAHE contrast boost & Otsu threshold)
        if not decoded_entries:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img.copy()
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            enhanced_gray = clahe.apply(gray)
            _try_detect(standard_detector, enhanced_gray, "clahe")

            if not decoded_entries:
                _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                _try_detect(standard_detector, otsu, "otsu")

        # Pass 4: 1.5x Upscaling for tiny QR codes in large documents
        if not decoded_entries and max(h_orig, w_orig) < 2500:
            upscaled = cv2.resize(img, (int(w_orig * 1.5), int(h_orig * 1.5)), interpolation=cv2.INTER_CUBIC)
            if aruco_detector:
                _try_detect(aruco_detector, upscaled, "aruco_upscaled")
            if not decoded_entries:
                _try_detect(standard_detector, upscaled, "standard_upscaled")

        # Pass 5: Multi-orientation scan (90° CW, 180°, 270° CW)
        if not decoded_entries:
            rotations = [cv2.ROTATE_90_CLOCKWISE, cv2.ROTATE_180, cv2.ROTATE_90_COUNTERCLOCKWISE]
            for rot_code in rotations:
                rot_img = cv2.rotate(img, rot_code)
                _try_detect(standard_detector, rot_img, "rotated")
                if decoded_entries:
                    break

        has_qr = len(decoded_entries) > 0
        payloads = [e["payload"] for e in decoded_entries]

        # Enrich payloads
        all_merchants = []
        all_payees = []
        all_providers = []
        all_vpas = []
        enriched_payloads = []
        qr_objects = []

        for e in decoded_entries:
            p = e["payload"]
            enr = enrich_qr_payload(p)
            enriched_payloads.append(enr["enriched_text"])
            all_merchants.extend(enr["merchants"])
            all_payees.extend(enr["payees"])
            all_providers.extend(enr["providers"])
            all_vpas.extend(enr["vpas"])

            # Compute bounding box
            pts = e.get("points")
            bbox = {}
            norm_bbox = {}
            if pts is not None:
                try:
                    pts_arr = np.array(pts, dtype=np.int32).reshape(-1, 2)
                    x, y, bw, bh = cv2.boundingRect(pts_arr)
                    # Guard bounds
                    x = max(0, min(x, w_orig - 1))
                    y = max(0, min(y, h_orig - 1))
                    bw = max(1, min(bw, w_orig - x))
                    bh = max(1, min(bh, h_orig - y))
                    bbox = {"x": int(x), "y": int(y), "width": int(bw), "height": int(bh)}
                    norm_bbox = {
                        "x": round(x / float(w_orig), 4),
                        "y": round(y / float(h_orig), 4),
                        "width": round(bw / float(w_orig), 4),
                        "height": round(bh / float(h_orig), 4),
                    }
                except Exception:
                    bbox = {}
                    norm_bbox = {}

            # Construct label
            label = "QR Code"
            if enr["merchants"]:
                label = f"QR: {enr['merchants'][0]}"
            elif enr["payees"]:
                label = f"QR: {enr['payees'][0]}"
            elif enr["providers"]:
                label = f"QR: {enr['providers'][0]}"

            qr_objects.append({
                "type": "qr_code",
                "label": label,
                "data": p,
                "location_desc": "Embedded QR Code",
                "confidence": 1.0,
                "bbox": bbox,
                "normalized_bbox": norm_bbox,
                "merchant": enr["merchants"][0] if enr["merchants"] else None,
                "payee": enr["payees"][0] if enr["payees"] else None,
                "provider": enr["providers"][0] if enr["providers"] else None,
            })

        summary = " | ".join(enriched_payloads) if has_qr else ""

        enriched_info = {
            "has_qr": has_qr,
            "count": len(payloads),
            "payloads": payloads,
            "merchants": sorted(list(set(all_merchants))),
            "payees": sorted(list(set(all_payees))),
            "providers": sorted(list(set(all_providers))),
            "vpas": sorted(list(set(all_vpas))),
            "summary": summary,
        } if has_qr else None

        return {
            "detected": has_qr,
            "has_qr": has_qr,
            "count": len(payloads),
            "payloads": payloads,
            "enriched_payloads": enriched_payloads,
            "merchants": sorted(list(set(all_merchants))),
            "payees": sorted(list(set(all_payees))),
            "providers": sorted(list(set(all_providers))),
            "vpas": sorted(list(set(all_vpas))),
            "qr_summary": summary,
            "qr_objects": qr_objects,
            "enriched": enriched_info,
        }
    except Exception as e:
        print(f"[QR Engine] Extraction error: {e}")
        return {
            "detected": False,
            "has_qr": False,
            "count": 0,
            "payloads": [],
            "enriched_payloads": [],
            "merchants": [],
            "payees": [],
            "providers": [],
            "vpas": [],
            "qr_summary": "",
            "qr_objects": [],
            "enriched": None,
        }


