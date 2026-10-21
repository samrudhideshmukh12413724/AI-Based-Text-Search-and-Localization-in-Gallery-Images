# Security Policy

## Supported Versions
Only the latest release on the `main` branch receives active security updates and vulnerability patches.

| Version | Supported          |
| ------- | ------------------ |
| 5.0.x   | :white_check_mark: |
| < 5.0   | :x:                |

## Reporting a Vulnerability
We take the security and privacy of DocuLens AI seriously. If you discover a security vulnerability:

1. **Do not disclose the issue publicly** on GitHub issues, pull requests, or forums.
2. Email the maintainers privately with a detailed description of the vulnerability, proof of concept, and impact assessment.
3. You will receive an acknowledgment within 48 hours.
4. A coordinated disclosure date will be established once a fix is verified.

## Local Data Isolation & Privacy Policy
- **On-Device & Self-Hosted**: DocuLens AI is designed to run self-hosted or purely locally. Extracted OCR text, perceptual hashes, and vector embeddings remain on your own deployment.
- **Tenant Isolation**: All database queries enforce strict user ID matching.
- **Guest Ephemeral Mode**: Guest sessions use UUID-based headers (`X-Guest-Session-ID`) with strictly separated row partitions.
- **Forensic Verification**: Steganographic watermarks and Error Level Analysis (ELA) are computed on-premise without forwarding images to third-party APIs.
