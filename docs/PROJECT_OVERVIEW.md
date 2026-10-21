# DocuLens AI - PROJECT OVERVIEW

## 1. Executive Summary


DocuLens AI (officially titled "AI-Based Text Search and Localization in Gallery Images") is an enterprise-grade, edge-cloud document intelligence and visual retrieval system. The project bridges the critical gap between unindexed mobile photo galleries and structured document databases. While traditional mobile galleries treat document photos (receipts, Aadhaar cards, PAN cards, invoices, marksheets, hall tickets) as static pixel grids, DocuLens AI transforms them into searchable, explainable, and cryptographically verified digital assets.

The core engineering breakthrough of DocuLens AI lies in its unified multi-modal fusion architecture. It does not rely solely on optical character recognition (OCR) or keyword matching; instead, it harmonizes five complementary intelligence layers:
1. Multi-Orientation Adaptive OCR: Trilingual (English, Hindi, Marathi) text recognition powered by EasyOCR with automated perspective correction, contrast-limited adaptive histogram equalization (CLAHE), and unsharp masking.
2. Dense Semantic Vector Search: SentenceTransformer all-MiniLM-L6-v2 embeddings generating 384-dimensional dense semantic vectors that enable natural language discovery (e.g. querying "tuition cost" retrieves documents containing "college fees").
3. Open-Vocabulary Visual Object Localization: Vision-Language grounding using OpenAI CLIP ViT-B/32 patch embeddings coupled with OpenCV contour gradient proposals to locate physical visual regions (signatures, stamps, QR codes, face photos).
4. Structured Entity Extraction & Relational Graphing: Deterministic pattern engines extracting PAN, Aadhaar, roll numbers, currency amounts, dates, and cross-linking multi-page related documents.
5. Zero-Trust Security & Multi-Tenant Privacy: Row-Level Security (RLS) isolating registered users, ephemeral isolated guest sessions (X-Guest-Session-ID), Error Level Analysis (ELA) document tampering detection, and HMAC-SHA256 ZK-Steganography watermarking.

This comprehensive technical report provides an exhaustive, code-grounded engineering audit of the entire DocuLens AI codebase, configuration files, database schemas, model checkpoints, and runtime benchmarks.


---

## 2. Project Title and Background


- Project Title: DocuLens AI: AI-Based Text Search and Localization in Gallery Images
- System Codename: AI Document & Image-Inside-Image Visual Search
- Repository Version: 5.0.0 Production Release
- Target OS Platforms: Android 10+ (Physical devices & Emulators), Linux VPS (Docker), Windows 11 (Development)
- Primary Engineering Stack: Flutter 3.27.4 (Dart 3.6.2), Python 3.11, FastAPI 0.110+, PyTorch 2.x CPU, SQLite 3 (WAL Mode), EasyOCR 1.7+, Transformers 4.30+, OpenCV 4.8+.

Background:
Smartphones have become the default handheld scanner for students, working professionals, and business owners in India and globally. Users routinely photograph electricity bills, rent agreements, college fee receipts, vehicle registrations, prescription notes, and identity cards. However, mobile gallery applications (such as default Google Photos, Samsung Gallery, or Apple Photos) suffer from three severe architectural bottlenecks:
1. Lexical Brittleness: They fail when the user searches for conceptual synonyms or translated regional terms (e.g. searching "scholarship" misses documents marked in Marathi as "शिष्यवृत्ती").
2. Zero Visual Grounding: They cannot highlight the exact physical coordinates of text inside crowded documents on-device, forcing users to manually read through paragraphs of text.
3. Severe Cloud Privacy Risks: Commercial scanning applications upload personal identity cards and sensitive financial records to third-party public clouds where private user documents are indexed by external entities.

DocuLens AI was conceived to solve these three fundamental challenges through an edge-cloud, multi-modal, privacy-first retrieval paradigm.


---

## 3. Problem Statement


In everyday digital life, smartphone users take thousands of photos, a significant percentage of which are documents, forms, receipts, identity proofs, and notices. When a user urgently needs to retrieve a specific record (e.g. providing an Aadhaar card at an airport counter, presenting a college fee challan during admission, or locating a medical test invoice), they encounter friction:
1. Search Inability: Smartphone galleries index image metadata (date, time, GPS location) but cannot perform deep lexical, fuzzy, or semantic searches inside the text of the photographed documents.
2. Typos and OCR Degradation: Real-world photos suffer from low lighting, camera motion blur, perspective skews, shadows, and wrinkled paper. Off-the-shelf OCR engines frequently produce typos (e.g. 'S0h0larsh1p' instead of 'Scholarship'), causing standard substring queries to fail completely.
3. Multi-Lingual & Code-Mixed Text: In regions like Maharashtra, documents commonly mix English and Devanagari script (Marathi/Hindi). Standard mobile gallery search engines possess zero cross-lingual query expansion capabilities.
4. Duplicate Document Clutter: Users frequently take 3 to 5 rapid burst photos or receive duplicate forwarded WhatsApp images of the same document, cluttering search results.
5. Inability to Verify Document Authenticity: Mobile galleries cannot differentiate between genuine unaltered document photographs and digitally photoshopped or manipulated scans.


---

## 4. Objectives


The primary engineering objectives accomplished in DocuLens AI are:
1. Real-Time High-Accuracy Multi-Orientation OCR: Achieve >= 95% word accuracy on camera document captures across 0°, 90° CW, 90° CCW, and 180° rotations with automated orientation detection and deskewing.
2. In-Image Spatial Text Highlighting: Normalize polygon OCR bounding box coordinates to relative [0, 1] screen space and render glowing bounding box overlays in Flutter directly on top of the matched text.
3. Dense Semantic & Cross-Lingual Search: Integrate SentenceTransformers all-MiniLM-L6-v2 and a Devanagari bilingual translation dictionary to support semantic natural language queries and cross-lingual concept search.
4. Open-Vocabulary Visual Object Grounding: Employ OpenAI CLIP ViT-B/32 patch embeddings and OpenCV contour proposals to locate signatures, official stamps, QR codes, and face photos inside documents.
5. Multi-Tenant Row-Level Data Privacy: Enforce complete cryptographic user isolation using JWT Bearer authentication, stable client-specific guest sessions (X-Guest-Session-ID), and isolated empty vaults for unauthenticated requests.
6. Real-Time Duplicate Clustering: Implement SHA-256 binary hashing and 64-bit perceptual hashing (pHash) with Hamming distance thresholding to collapse duplicate variants under single canonical records.
7. Document Authenticity & Tamper Detection: Provide digital Error Level Analysis (ELA) to compute tamper suspicion heatmaps and embed HMAC-SHA256 ZK-Steganography watermarks into image pixel LSBs.
8. Single-Click Searchable PDF Export: Generate clean, printable PDF documents containing OCR text metadata, SHA-256 hashes, and extracted entities using ReportLab.


---

## 5. Target Users and Use Cases


Target Users:
- University & College Students: Managing exam hall tickets, semester marksheets, hostel night-out passes, bonafide certificates, scholarship forms, and tuition fee receipts.
- Office Professionals & Accountants: Archiving GST invoices, business cards, fuel receipts, travel tickets, client contracts, and vendor challans.
- General Smartphone Users: Organizing Aadhaar cards, PAN cards, driving licenses, passport copies, medical prescriptions, and vehicle insurance papers.
- Academic & Research Reviewers: Evaluating edge-cloud AI computer vision pipelines, multi-modal score fusion formulas, and zero-trust authentication architectures.

Core Use Cases:
1. Instant Receipt & Expense Auditing: User photographs a paper payment receipt with an embedded UPI QR code. The app decodes the merchant VPA, extracts the total amount (e.g. ₹4,500), indexes line items, and allows instant search by merchant name or price.
2. Multi-Lingual Academic Document Retrieval: A student queries "college fees" or "scholarship"; DocuLens AI automatically retrieves Marathi documents titled "महाविद्यालयीन शुल्क पावती" or "शिष्यवृत्ती अर्ज" and highlights the matching terms in yellow.
3. Offline Emergency Document Access: User searches for their Aadhaar or blood group record while traveling with zero mobile data connectivity. The app retrieves cached documents and highlights numbers immediately.
4. Tamper & Forgery Verification: An administrative officer inspects a certificate photo. The app runs Error Level Analysis (ELA), flagging suspicious localized text edits where pixels were spliced or edited.


---

## 6. Scope and Boundaries


In Scope:
- Android mobile client built with Flutter supporting camera scanning, gallery importing, and background folder synchronization.
- Python FastAPI asynchronous backend serving REST API endpoints on port 8000.
- SQLite embedded database with Write-Ahead Logging (WAL) and Row-Level Security (RLS).
- Offline model caching for EasyOCR, MiniLM, and CLIP ViT-B/32 enabling fast startup without repeated internet model downloads.
- Hybrid multi-signal ranking fusing OCR lexical score, semantic embedding cosine similarity, QR metadata, and visual patch scores.
- Asynchronous multi-worker sync queue prioritizing important documents (PAN, Aadhaar, receipts) over bulk general camera photos.

Out of Scope / Current Boundaries:
- Continuous cloud-to-cloud multi-device synchronization (all data resides locally on the user's host or private VPS).
- GPU-accelerated server clusters (pipeline is engineered and optimized specifically for CPU PyTorch inference).
- Native iOS Swift UI (the current frontend is optimized and tested on Android and Flutter Web).
- Real-time video stream OCR (processing operates on static captured frames and gallery photographs).


---

