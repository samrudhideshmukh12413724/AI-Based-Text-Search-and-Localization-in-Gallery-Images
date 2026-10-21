# DocuLens AI - ALGORITHMS AND FORMULAS

## 20. Algorithms and Mathematical Formulas


The DocuLens AI codebase implements specific mathematical formulas across vision, retrieval, and security:

1. Blur Detection (Variance of Laplacian):
Formula:
$$\text{Var}(\Delta) = \frac{1}{N} \sum_{x, y} \left( \nabla^2 I(x, y) - \mu_{\nabla^2 I} \right)^2$$
Where $\nabla^2 I = \frac{\partial^2 I}{\partial x^2} + \frac{\partial^2 I}{\partial y^2}$ is computed using the 3x3 discrete Laplacian kernel:
$$K = \begin{bmatrix} 0 & 1 & 0 \\ 1 & -4 & 1 \\ 0 & 1 & 0 \end{bmatrix}$$
Configured Threshold: $\text{Var}(\Delta) < 100.0 \implies \text{Blurry}$.

2. Gamma Correction (Non-linear Luminance Re-mapping):
Formula:
$$I_{out}(x, y) = 255 \cdot \left( \frac{I_{in}(x, y)}{255} \right)^\gamma$$
Configured Thresholds:
- Dark documents ($Mean(I) < 60.0$): $\gamma = 0.55$ (Brightens text shadows).
- Washed-out/overexposed documents ($Mean(I) > 215.0$): $\gamma = 1.35$ (Darkens faded ink).

3. Unsharp Masking (High-Frequency Edge Restoration):
Formula:
$$I_{sharp} = I_{orig} + \text{strength} \cdot (I_{orig} - G_\sigma * I_{orig})$$
Where $G_\sigma$ is Gaussian blur with $\sigma = 1.2$, and $\text{strength} = 1.5$.

4. Dense Semantic Cosine Similarity:
Formula:
$$\text{Sim}_{cos}(\mathbf{q}, \mathbf{d}) = \frac{\mathbf{q} \cdot \mathbf{d}}{\|\mathbf{q}\|_2 \|\mathbf{d}\|_2} = \frac{\sum_{i=1}^{384} q_i d_i}{\sqrt{\sum_{i=1}^{384} q_i^2} \sqrt{\sum_{i=1}^{384} d_i^2}}$$

5. 6-Signal Multi-Modal Hybrid Scoring:
Formula:
$$S_{hybrid} = w_{ocr} S_{ocr} + w_{sem} S_{sem} + w_{blip} S_{blip} + w_{qr} S_{qr} + w_{vis} S_{vis} + w_{stego} S_{stego}$$
Configured Normalized Weights:
$w_{ocr} = 0.35, w_{sem} = 0.25, w_{blip} = 0.15, w_{qr} = 0.10, w_{vis} = 0.10, w_{stego} = 0.05$.

6. Adaptive Dynamic Threshold (tau_adaptive):
Formula:
$$\tau_{adaptive}(Q, \mathbf{S}) = \max\left(\tau_{min},\; \mu_S + k_\sigma \cdot \sigma_S - \alpha_{len} \cdot \ln(1 + |Q|)\right)$$
Where $\tau_{min} = 0.30, k_\sigma = 0.20, \alpha_{len} = 0.05$, $|Q| = \text{query character length}$, $\mu_S = \text{mean score}$, $\sigma_S = \text{standard deviation of scores}$.

7. Shannon Query Entropy H(Q):
Formula:
$$H(Q) = -\sum_{c \in \Sigma} P(c) \log_2 P(c)$$
Where $P(c) = \frac{\text{count}(c)}{|Q|}$. Used in `entropy_fusion.py` to switch between keyword mode ($H(Q) < 2.5$) and natural language mode ($H(Q) \ge 2.5$).

8. Error Level Analysis (ELA) Tamper Score:
Formula:
$$\text{ELA}(x, y) = |I_{orig}(x, y) - I_{JPEG, q=90}(x, y)|$$
$$\text{TamperScore} = \min\left(1.0,\; \frac{1.8 \cdot \sigma_{ELA} + 30.0 \cdot \frac{\max(ELA)}{255}}{100.0}\right)$$
Configured Threshold: $\text{TamperScore} \ge 0.55 \implies \text{SUSPICIOUS\_EDITS\_DETECTED}$.


---

## 21. Configured Thresholds and Their Purposes


The codebase incorporates specifically configured thresholds rather than arbitrary constants:

Table of Empirical Thresholds:
- Blur Variance Threshold (`app/ocr/quality.py:54`): `100.0` — Values below 100 indicate camera motion or defocus blur requiring unsharp masking.
- Dark Luminance Threshold (`app/ocr/quality.py:55`): `60.0` — Mean grayscale values below 60 trigger gamma brightening (0.55).
- Overexposure Luminance Threshold (`app/ocr/quality.py:56`): `215.0` — Mean grayscale values above 215 trigger gamma darkening (1.35).
- Low Contrast Threshold (`app/ocr/quality.py:57`): `contrast < 42.0 or dynamic_range < 75.0` — Triggers CLAHE (Contrast Limited Adaptive Histogram Equalization).
- EasyOCR Text Detection Threshold (`app/ocr/ocr_engine.py:235`): `text_threshold = 0.22` — Minimum character box confidence.
- EasyOCR Low Text Threshold (`app/ocr/ocr_engine.py:236`): `low_text = 0.12` — Bound for linking weak character strokes.
- EasyOCR Link Threshold (`app/ocr/ocr_engine.py:237`): `link_threshold = 0.20` — Distance threshold for combining characters into words.
- Fast Upright OCR Acceptance (`app/ocr/ocr_engine.py:284`): `valid_words >= 4 and score >= 12.0` — Accepts 0° upright orientation immediately, skipping 3 redundant rotation passes for a 4x speedup.
- OCR Bounding Box IoU Deduplication (`app/ocr/ocr_engine.py:380`): `iou > 0.40 and SequenceMatcher >= 0.65` — Suppresses duplicate OCR bounding boxes without dropping distinct nearby words.
- Semantic Cosine Cutoff (`app/semantic_search.py:205-209`): Numeric queries: `0.44`, Short entities: `0.42`, General queries: `0.40`.
- CLIP Zero-Shot Visual Match Threshold (`app/visual_search.py:122`): `0.245` — Baseline threshold for open-vocabulary visual object proposals.
- CLIP Area-Aware Localization Yield (`app/visual_search.py:190-201`): For large regions (area >= 6%), tolerance is `0.025`; for small slivers, tolerance is `0.012`.
- Duplicate pHash Hamming Distance (`app/duplicates/detector.py:29`): `max_hamming_distance = 5` — pHash distances <= 5 (out of 64 bits) classify images as visual near-duplicates.


---

## 22. OCR Processing Pipeline


The Optical Character Recognition pipeline (`backend/app/ocr/ocr_engine.py`) follows a robust, multi-stage flow:

1. Ingestion & Scale Normalization:
   Incoming images are loaded with EXIF transposition. If the max dimension exceeds 1600 pixels, it is downscaled using `cv2.INTER_AREA`. This prevents excessive CPU memory consumption while maintaining crisp character legibility.

2. Document Perspective Dewarping & Shadow Removal:
   `app/ocr/document_enhancer.py` inspects the image for quadrangle document borders. If quadrilateral document corners are identified, it applies a 4-point perspective transform (`cv2.getPerspectiveTransform` and `cv2.warpPerspective`). Magic Color shadow removal applies localized division normalization against the background illumination plane.

3. Native 0° Upright Evaluation & Fast Exit:
   The trilingual EasyOCR reader (`en`, `hi`, `mr`) processes the upright 0° image. If the pass detects >= 4 valid alphanumeric words with an orientation score >= 12.0, the document is confirmed upright (e.g. standard PAN card or fee challan). The system accepts 0° immediately, avoiding 3 redundant rotations.

4. Multi-Orientation Consensus Voting (Rotated Document Recovery):
   If 0° detects sparse text, the engine rotates the canvas:
   - 90° Clockwise (`cv2.ROTATE_90_CLOCKWISE`)
   - 90° Counter-Clockwise (`cv2.ROTATE_90_COUNTERCLOCKWISE`)
   - 180° Inverted (`cv2.ROTATE_180`)
   The orientation achieving the highest confidence-weighted word density wins.

5. Mathematical Polygon Coordinate Un-Rotation:
   Each detected polygon `pts` on a rotated canvas is mapped back to the original full-size coordinate canvas via `_unrotate_poly`:
   - 90° CW: $x_{orig} = y_{rot}, \quad y_{orig} = H_{sc} - 1 - x_{rot}$
   - 90° CCW: $x_{orig} = W_{sc} - 1 - y_{rot}, \quad y_{orig} = x_{rot}$
   - 180°: $x_{orig} = W_{sc} - 1 - x_{rot}, \quad y_{orig} = H_{sc} - 1 - y_{rot}$
   All coordinates are then divided by the scale factor to match original image pixel dimensions.

6. Handwriting & Ink Enhancement Pass:
   If fewer than 3 valid words are detected on low-contrast documents, `app/ocr/handwriting.py` applies morphological stroke-preserving ink enhancement to recover handwritten signatures and notes.

7. Deduplication & Reading Order Sorting:
   Boxes with $\text{IoU} > 0.40$ and text similarity $> 0.65$ are deduplicated. Finally, boxes are sorted top-to-bottom, left-to-right (`y // 40, x`).


---

## 23. Text and Fuzzy-Search Pipeline


The lexical search pipeline (`backend/app/search/`) combines exact token matching, inflection expansion, and fuzzy string similarity:

1. Tokenization & Normalization:
   Queries and document texts are stripped of punctuation, converted to lowercase, and split into tokens. Stopwords (e.g. 'the', 'is', 'for', 'at') are filtered out when query length permits.

2. Inflection Map Expansion:
   The search engine maintains a dictionary of common academic and administrative inflections (`exact_search.py:INFLECTION_MAP`):
   - 'fee' <-> 'fees', 'tuition', 'challan'
   - 'exam' <-> 'examination', 'hallticket', 'admit'
   - 'scholarship' <-> 'fellowship', 'stipend'
   - 'admit' <-> 'admission', 'hallticket'
   Matches across inflection sets receive a high lexical confidence score (0.95 - 1.00).

3. Fuzzy Typo & OCR Error Matching:
   When camera noise produces minor character substitutions (e.g. 'Scho1arsh1p' instead of 'Scholarship'), standard exact matching fails. `app/search/fuzzy_search.py` evaluates token similarity using Gestalt Pattern Matching (`difflib.SequenceMatcher`).
   If $\text{Ratio}(T_1, T_2) \ge 0.75$ for tokens with length >= 4, the match is accepted with a proportional score penalty.

4. Devanagari Cross-Lingual Translation:
   Queries entered in English (e.g. 'bus ticket') are cross-referenced with `app/translation.py`. If matching Devanagari terms ('बस', 'तिकीट') appear in the OCR text, the document is retrieved with full text match grounding.


---

## 24. Semantic-Search Pipeline


The dense semantic search pipeline (`backend/app/semantic_search.py`) enables concept-level retrieval:

1. Embedding Model Setup:
   Powered by `all-MiniLM-L6-v2`. The model maps text sequences to a 384-dimensional dense vector space where semantically similar concepts reside in close proximity.

2. In-Memory Zero-Disk RAM Vector Cache:
   To eliminate disk I/O thrashing during frequent searches, all document embeddings are cached in RAM (`_IN_MEMORY_CACHE = {'embeddings': Tensor, 'metadata': list}`).

3. Vectorized Cosine Similarity:
   The user query is encoded into a 384-dimensional tensor $\mathbf{q}$. Cosine similarities across all indexed document vectors $\mathbf{D}$ are computed in a single vectorized PyTorch operation:
   $$\mathbf{S} = \frac{\mathbf{q} \cdot \mathbf{D}^T}{\|\mathbf{q}\| \|\mathbf{D}\|}$$

4. Numeric Query Guard:
   When a user searches for numeric identifiers (e.g. '100', '2026', '88'), dense embedding models can exhibit semantic drift by associating numbers with unrelated financial or calendar contexts.
   `semantic_search.py` enforces a strict Numeric Guard: If a query consists of digits, candidates must contain the exact digit string in the OCR text or filename; otherwise, they are rejected unless the semantic score exceeds 0.52.

5. Sub-Millisecond Incremental Ingestion:
   When a new image finishes OCR, `append_single_embedding(doc_row)` encodes only the new document and concatenates its tensor to the active RAM tensor (`torch.cat([old_emb, new_emb])`), allowing the document to be searched instantly without re-indexing the entire database.


---

## 25. Visual-Search Pipeline


The visual search pipeline (`backend/app/visual_search.py`) allows open-vocabulary image retrieval without relying on OCR:

1. Region Proposal Generation:
   When an image is indexed, `app/visual_region_extractor.py` detects candidate visual regions:
   - Structured visual objects (QR codes, barcodes)
   - Color graphic blocks (photos, colored badges, identity headers)
   - Saturated color regions (cars, pets, objects)
   - Edge gradient contour enclosures (signatures, stamps, seals)
   - Quadrant anchors and full document canvas

2. Patch Embedding with CLIP ViT-B/32:
   Each proposed visual crop is resized to 224x224 pixels, normalized with ImageNet mean and standard deviation, and passed through OpenAI CLIP ViT-B/32. The model generates 512-dimensional L2-normalized feature vectors saved as binary blobs in the `visual_regions` SQLite table.

3. Prompt Ensembling:
   User visual queries (e.g. 'signature', 'official stamp', 'college logo') are expanded using prompt templates:
   - "a document containing {query}"
   - "a photo or image of {query}"
   - "an official {query}"
   - "{query}"
   The prompt embeddings are averaged and re-normalized to form a robust query vector.

4. Spatial Patch Similarity & Area-Aware Localization Yield:
   Query vectors are compared against all stored region blobs via dot product.
   To avoid always selecting the full document canvas over a localized object, DocuLens AI applies Area-Aware Localization Yield: If a specific localized region (stamp or signature) scores within $\Delta \le 0.025$ of the full document score, the localized bounding box is selected for UI presentation.


---

## 26. OpenCV Candidate-Region Processing


The OpenCV candidate region extraction module (`backend/app/visual_region_extractor.py`) detects sub-regions for zero-shot visual patch embedding:

1. Color Block Segmentation (Photos & Badges):
   Converts image to HSV color space. Computes a binary mask filtering for saturation in [70, 255] and value in [50, 255], isolating saturated colored areas while excluding plain white paper, dark text, and ambient background tints.
   A 15x15 rectangular structuring element (`cv2.morphologyEx(..., MORPH_CLOSE)`) closes broken contours. Bounding rectangles are extracted, retaining areas between 4,000 and 0.70 * W * H pixels.

2. Sobel Edge Gradient Contours (Signatures & Stamps):
   Computes horizontal and vertical Sobel gradients (`cv2.Sobel(gray, CV_16S, dx=1, dy=0, ksize=3)`). Absolute gradients are blended to produce an edge intensity magnitude map.
   Binary thresholding at 50, followed by a 20x15 morphological dilation, connects signature strokes and circular stamp outlines into coherent single-bounding regions.

3. Spatial Location Descriptors:
   Every proposed region is classified into a human-readable location tag based on its normalized center coordinates:
   - Horizontal: Left ($cx < 0.35$), Right ($cx > 0.65$), Center
   - Vertical: Top ($cy < 0.35$), Bottom ($cy > 0.65$), Middle
   - Output label examples: "Top-Right", "Bottom-Left", "Center", or "Full Document" (when $w \ge 0.85$ and $h \ge 0.85$).


---

## 27. CLIP-Based Matching


Why OpenCV and CLIP are complementary and not interchangeable:
- OpenCV is a classical computer vision library executing deterministic pixel arithmetic, edge filters, color masking, and morphological transformations. It cannot understand semantics (e.g. it cannot know if an edge contour represents an official university seal or an ink smudge).
- OpenAI CLIP is a multi-modal deep neural network trained on hundreds of millions of image-text pairs. It maps vision and language into a shared embedding space, allowing open-vocabulary queries. However, running a Vision Transformer over an entire 4000x3000 document photo will blur out small 50x50 pixel stamps.
- The DocuLens AI Fusion: OpenCV acts as the Region Proposer (detecting candidate bounding crops with zero neural inference cost), and CLIP acts as the Semantic Matcher (evaluating zero-shot vision-language similarity on the proposed crops).


---

## 28. Bounding-Box Generation and Display


The in-image spatial localization subsystem translates OCR and visual detection coordinates into real-time UI highlight overlays:

1. Coordinate Normalization Formula (`app/highlighting.py:312-317`):
   To ensure that bounding boxes render consistently across different Android screen densities, tablets, and orientation changes, all absolute pixel bounding boxes $(x, y, w, h)$ are normalized relative to effective image dimensions $(W_{eff}, H_{eff})$:
   $$\text{norm\_x} = \text{round}\left(\frac{x}{W_{eff}}, 4\right), \quad \text{norm\_y} = \text{round}\left(\frac{y}{H_{eff}}, 4\right)$$
   $$\text{norm\_w} = \text{round}\left(\frac{w}{W_{eff}}, 4\right), \quad \text{norm\_h} = \text{round}\left(\frac{h}{H_{eff}}, 4\right)$$

2. Flutter Canvas Rendering (`BoundingBoxOverlayPainter`):
   In `mobile_app/lib/widgets/bounding_box_painter.dart`, Flutter's `CustomPainter` renders the overlay directly on the document image canvas:
   - Text Highlights (`type == 'text_highlight'`): Rendered in vibrant yellow (`Color(0xFFFFB300)` border, `Color(0x60FFE600)` translucent fill, and `Color(0x35FFEA00)` glowing border).
   - Visual Objects (`type == 'visual_region'` or `'qr_detector'`): Rendered in cyan (`Color(0xFF00E5FF)` border, `Color(0x2A00E5FF)` translucent fill).
   - Precision Corner Brackets: Four corner accent lines are drawn at each vertex with length:
     $$\text{cornerLen} = \text{clamp}(w_{box} \cdot 0.25,\; 4.0,\; 14.0)$$
     This produces a modern, high-tech scanner HUD aesthetic.


---

## 29. QR/Barcode Processing


The QR/Barcode intelligence module (`backend/app/qr_decoder.py`) decodes payloads and extracts structured transactional metadata:

1. UPI Payment String Parsing:
   Detects `upi://pay` URI schemes and extracts standard National Payments Corporation of India (NPCI) parameters:
   - `pa`: Payee VPA address (e.g. `merchant@okhdfcbank`, `canteen@ybl`)
   - `pn`: Payee / Merchant display name
   - `am`: Transaction amount in INR
   - `cu`: Currency code (default: INR)

2. Payment Provider Handle Resolution (`UPI_PROVIDER_MAP`):
   Maps VPA handle suffixes to known Indian payment applications:
   - `@ybl`, `@ibl`, `@axl` -> PhonePe
   - `@okhdfcbank`, `@okaxis`, `@oksbi`, `@okicici` -> Google Pay
   - `@paytm`, `@ptaxis`, `@pthdfc` -> Paytm
   - `@upi` -> BHIM
   - `@apl`, `@yapl` -> Amazon Pay
   - `@axisb`, `@cred` -> Cred
   - `@bharatpe` -> BharatPe

3. EMVCo / BharatQR Tag-Length-Value (TLV) Decoder (`parse_emvco_tlv`):
   Parses raw static QR payloads conforming to EMVCo Merchant-Presented QR Specifications (strings beginning with `000201`):
   - Tag 59: Merchant Name
   - Tag 60: Merchant City
   - Tag 26-51: Merchant Account Information & UPI VPAs

4. vCard & Contact Card Parsing (`parse_vcard_or_mecard`):
   Parses `BEGIN:VCARD` and `MECARD:` payloads, extracting Full Name (`FN:` / `N:`), Organization (`ORG:`), and Phone Number (`TEL:`).


---

## 30. Search Ranking and Score Fusion


DocuLens AI executes a multi-signal score fusion and dynamic pruning strategy in `app/main.py:1051-1430`:

1. Concurrency:
   ThreadPoolExecutor spawns three parallel threads: Keyword Retrieval, Semantic Retrieval, and Visual CLIP Retrieval.

2. Fused Relevance Score ($S_{fused}$):
   - Multi-Modal Case (Both text and visual criteria met):
     $$S_{fused} = \min(0.95,\; \max(S_{text}, S_{vis}) \cdot 0.85 + \min(S_{text}, S_{vis}) \cdot 0.15)$$
     If exact keyword match exists with $S_{text} \ge 0.98$, fused score is locked at a perfect 1.00.
   - Text-Only Case: $S_{fused} = \min(0.95, S_{text})$. Rejects semantic drift where $S_{text} < 0.40$.
   - Visual-Only Case: Normalized via `_norm_vis_score`. Minimum cutoff is 0.335 for visual targets and 0.460 for general phrases.

3. Tie-Breaking & Evidence Grounding:
   When candidate documents share identical fused scores, visual evidence grounding breaks ties:
   $$\text{Weight}(SearchType) = \begin{cases} 1.0 & \text{if keyword} \\ 0.8 & \text{if multimodal} \\ 0.5 & \text{if semantic} \\ 0.2 & \text{if visual} \end{cases}$$

4. Adaptive Threshold Pruning:
   Applies `tau_adaptive(query, scores)`. When high-confidence text matches exist ($S \ge 0.85$), weak visual-only stragglers with score $< 0.50$ are pruned.


---

## 31. Duplicate Detection and Document Linking


The duplicate detection and cross-document relationship discovery engines operate in `app/duplicates/` and `app/linking/`:

Duplicate Detection Hierarchy:
1. Exact Binary Match (SHA-256):
   Computes standard SHA-256 hash over file bytes. If another document owned by the same user shares the hash: match_type = 'exact_binary', distance = 0, similarity = 1.0.
2. Exact Visual Match (64-bit pHash):
   Computes discrete cosine transform perceptual hash (`imagehash.phash`). If pHash matches identically: match_type = 'exact_phash', distance = 0, similarity = 1.0.
3. Near-Duplicate Match:
   Computes Hamming distance between 64-bit hashes:
   $$\text{Distance}_{Hamming}(H_1, H_2) = \sum_{i=1}^{64} (H_1[i] \oplus H_2[i])$$
   $$\text{Similarity} = 1.0 - \frac{\text{Distance}}{64}$$
   If distance is in $[1, 5]$, classified as 'near_duplicate'.
4. Unique Document:
   Distance $> 5$ classified as unique.

Duplicate Collapsing in Search Results:
Duplicate variants are collapsed under their primary canonical document (`canonical_image_id`). Search results display the canonical card with a badge indicating "+X duplicate copies grouped".

Cross-Document Relationship Linking:
`linker.py` scans extracted entities and links distinct non-duplicate documents sharing high-confidence tokens:
- Shared Aadhaar numbers
- Shared PAN numbers
- Shared Application IDs (e.g. `ALT-2026-APP-8841`)
- Shared Roll Numbers (e.g. `23AIML123`)
- Shared Personal Phone Numbers & Personal Emails
Duplicate copies are explicitly excluded from cross-document relationships (`are_duplicates(...) == True`). Common dictionary words (APEX, COLLEGE, NOTICE) and public helplines (1800..., 1947) are strictly blacklisted.


---

