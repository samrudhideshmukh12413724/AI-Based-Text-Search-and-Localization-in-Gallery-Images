# DocuLens AI - PRIVACY AND SECURITY

## 33. Authentication and Privacy


Multi-Tenant Row-Level Security (RLS) & Zero-Trust Privacy Audit (`backend/app/auth.py`):

1. Registered User Authentication:
   - Uses RFC 7519 JSON Web Tokens (JWT) signed with HMAC-SHA256 (`ALGORITHM = 'HS256'`).
   - Token payload encodes `sub` (username), `user_id`, and `is_admin`.
   - Passwords are encrypted with salted Blowfish using `passlib.context.CryptContext(schemes=['bcrypt'])`.

2. Isolated Guest Session Mode (`X-Guest-Session-ID`):
   - To provide instant access without forcing mobile users to register, the mobile app generates a cryptographically secure 128-bit random hex UUID stored in SharedPreferences (`doculens_guest_session_id`).
   - The UUID is sent via the `X-Guest-Session-ID` HTTP request header.
   - The backend maps this UUID to a dedicated guest account in the `users` table. Guest A can never see Guest B's documents.

3. Unauthenticated Empty Vault Isolation:
   - If an incoming request contains neither a JWT token nor an `X-Guest-Session-ID` header, `auth.get_current_user` returns an anonymous guest entity with `user_id = -1`.
   - All SQL queries scoped to `user_id = -1` return zero records. This guarantees that unauthenticated requests to `/search` or `/uploads` can never leak private records.

4. Path Traversal & IDOR Protection:
   - `/uploads/{filename}` validates `safe_filename == filename`, rejects `..`, `/`, `\`, and verifies that the resolved path begins with the uploads directory.
   - Document delivery verifies ownership: non-admin requests attempting to view another user's image receive a `403 Forbidden`.


---

## 49. Security and Privacy Recommendations


Mandatory Security and Privacy Actions Before Public GitHub Upload:

1. Isolate and Quarantine Sensitive User Data:
   Do NOT push `database/images.db` containing real WhatsApp photos or personal phone numbers. Seed the public database with clean synthetic demo documents (`backend/seed_dataset.py`).

2. Update .gitignore Rules:
   Add explicit exclusions for all SQLite databases, binary executables, APKs, and backup snapshots:
   ```gitignore
   database/*.db
   database/*.db-wal
   database/*.db-shm
   *.db
   *.apk
   *.exe
   backend/.env
   .env
   uploads/
   ```

3. Rotate Credentials:
   Rotate the JWT `SECRET_KEY` in `backend/.env` and generate a cryptographically secure 256-bit random string via `openssl rand -hex 32`.

4. Row-Level Ownership Checks on Static File Mounts:
   Ensure that `/uploads/{filename}` strictly enforces tenant ownership checks and cannot be accessed via unauthenticated direct URL scraping.


---

