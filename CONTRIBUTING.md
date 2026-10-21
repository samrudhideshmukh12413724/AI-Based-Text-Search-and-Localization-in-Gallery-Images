# Contributing to DocuLens AI

Thank you for your interest in contributing to **DocuLens AI**! We welcome bug reports, feature proposals, documentation improvements, and pull requests.

## Code of Conduct
We are committed to providing a welcoming and inclusive environment for everyone. Please be respectful and constructive in all interactions.

## How to Contribute

### 1. Reporting Bugs
- Search existing issues to ensure the bug has not already been reported.
- Open a new issue with a clear descriptive title.
- Provide step-by-step reproduction instructions, logs, and device/environment details.

### 2. Suggesting Features
- Open an issue describing the proposed feature, the problem it solves, and potential implementation approaches.
- Wait for discussion before submitting large pull requests.

### 3. Pull Request Workflow
1. Fork the repository and create a feature branch (`git checkout -b feature/amazing-feature`).
2. Implement your changes adhering to the repository standards:
   - **Backend**: Python 3.11+, FastAPI, type hints, PEP8 compliance.
   - **Frontend**: Flutter 3.27.4+ / Dart 3.6.2+, standard Flutter widget tree structure.
3. Run automated tests before committing:
   ```bash
   # Backend tests
   pytest backend/tests/
   # Frontend static analysis
   cd mobile_app && flutter analyze
   ```
4. Commit your changes with conventional commit messages (`feat: ...`, `fix: ...`, `docs: ...`).
5. Push to your branch and open a Pull Request against `main`.

## Coding Standards & Rules
- **No Secrets**: Never commit `.env` files, API keys, passwords, or personal databases.
- **Privacy First**: Any test data must use synthetic mock documents, never personal identities.
- **Documentation**: All new endpoints must include OpenAPI docstrings and Pydantic schemas.
