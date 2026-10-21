# DocuLens AI - VIVA QUESTIONS

## 52. Viva Questions and Answers


Comprehensive College Viva & Technical Review Q&A:

Q1: What is the core problem that DocuLens AI solves compared to standard mobile galleries?
A: Standard mobile galleries treat images as unsearchable pixel grids, indexing only camera filenames and timestamps. DocuLens AI extracts text, visual objects, entities, and QR metadata, enabling deep semantic, lexical, and visual retrieval with in-image glowing spatial bounding box localization directly on the phone.

Q2: How does your OCR engine handle rotated documents (e.g. photos taken sideways or upside-down)?
A: It employs a multi-orientation consensus pipeline. It evaluates the upright 0° orientation; if text is sparse, it tests 90° CW, 90° CCW, and 180° rotations. The orientation producing the highest alphanumeric word density wins. Crucially, all detected polygon coordinates are mathematically inverse-transformed back to the original full-size image canvas via custom inverse coordinate formulas.

Q3: Why did you choose all-MiniLM-L6-v2 for semantic text search?
A: all-MiniLM-L6-v2 strikes the optimal balance between high semantic retrieval quality (cosine similarity on academic and administrative terminology) and extreme inference speed (sub-25ms CPU encoding for 384-dimensional dense vectors with an image footprint of only ~90 MB).

Q4: What is the difference between OpenCV region detection and CLIP visual search?
A: OpenCV is a deterministic classical vision library that finds candidate physical bounding boxes using color masks and Sobel edge gradients with zero neural inference cost. CLIP ViT-B/32 is a vision-language deep transformer that evaluates zero-shot semantic similarity between the candidate crop and a text prompt. OpenCV proposes WHERE objects might be; CLIP determines WHAT the object actually represents.

Q5: What is the purpose of the Adaptive Dynamic Threshold tau_adaptive(Q, scores)?
A: Static cutoffs (e.g. always filtering at 0.50) fail because short queries produce high baseline variance while long queries suffer from token dilution. tau_adaptive dynamically adjusts the cutoff based on the score distribution mean, standard deviation, and a logarithmic query length penalty, preventing false-positive semantic drift.

Q6: How does the system detect image tampering and photoshopped text?
A: It uses Error Level Analysis (ELA). The document is re-compressed in-memory at a fixed JPEG quality (90%). Photoshopped or digitally spliced regions have different error levels compared to the rest of the image. The system computes the pixel difference map and flags localized variance spikes exceeding the global mean by 1.8 standard deviations.

Q7: How do you enforce privacy when multiple users or guests use the app?
A: DocuLens AI enforces multi-tenant Row-Level Security (RLS). Registered users authenticate via JWT tokens. Guests are assigned a persistent 128-bit UUID via the `X-Guest-Session-ID` header, which maps to an isolated guest account. Unauthenticated requests default to user_id = -1, which returns an empty vault, guaranteeing zero data leakage.

Q8: How does duplicate image detection work?
A: It uses a two-tier strategy: First, exact binary match via SHA-256 hash (distance=0, sim=1.0). Second, visual near-duplicate match via 64-bit perceptual hashing (pHash) using discrete cosine transforms. If the Hamming distance is between 1 and 5 bits, it is classified as a near-duplicate and collapsed under the canonical document.


---

## 53. Glossary of Technical Terms


Technical Terminology Reference:
- OCR (Optical Character Recognition): Technology that converts photographed or scanned text into machine-readable character strings.
- CLAHE (Contrast Limited Adaptive Histogram Equalization): Computer vision algorithm that enhances local contrast in non-uniform illumination without amplifying background noise.
- CRAFT (Character Region Awareness for Text Detection): Neural network architecture used by EasyOCR to detect individual character regions and affinity links.
- MiniLM: Lightweight, distilled BERT transformer model mapping sentences into dense semantic vector spaces.
- Cosine Similarity: Metric measuring the cosine of the angle between two multi-dimensional vectors, evaluating orientation rather than magnitude.
- CLIP (Contrastive Language-Image Pre-training): Multi-modal neural network trained to associate natural language prompts with image crops.
- pHash (Perceptual Hash): Frequency-based image fingerprint derived from discrete cosine transforms that remains invariant to minor compression or scaling.
- Hamming Distance: Number of bit positions in which two binary strings of equal length differ.
- ELA (Error Level Analysis): Forensic technique analyzing JPEG compression artifact differences to detect digital manipulation.
- RLS (Row-Level Security): Database access control mechanism ensuring SQL queries only return rows matching the authenticated tenant's ID.
- ZK-Steganography: Technique embedding cryptographic signatures into pixel Least Significant Bits without altering visual appearance.


---

