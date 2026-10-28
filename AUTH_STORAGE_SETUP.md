# BrandLens authentication and persistent storage

## What's implemented

- Optional no-signup demo access with an isolated workspace; all main demo sections remain available.
- Email/password registration and sign-in for persistent team workspaces.
- Passwords stored as salted PBKDF2-SHA256 hashes, not plaintext.
- Signed, expiring bearer tokens.
- Server-side authorization checks for creator, reviewer, and workspace-admin roles.
- A private workspace per first account; teammates join using that workspace's invite code.
- Workspace-scoped review history, findings, custom rules, and uploaded guideline text.
- SQLite for local development and PostgreSQL when `DATABASE_URL` is configured.

## Local test (Windows PowerShell)

From the extracted project folder:

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Open a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open the Vite URL and choose **Explore demo without signing up** to test the demo immediately. To test registered team access, create the first account (workspace admin), then open **Team access** and copy its invite code. Register a second account with that code, sign in to the second account, and assign it the **Brand reviewer** role from the admin account. Verify that a creator cannot approve or reject a review.

The local database is `backend/data/brandlens.db`. Deleting it resets local users and demo data. Do not delete it if you need to retain the local test workspace.

## Hosted deployment

### Recommended quick path: Render Blueprint

1. Push the extracted project to a GitHub repository.
2. In Render, create a new Blueprint from that repository and let Render apply `render.yaml`.
3. The Blueprint provisions a PostgreSQL database and injects its connection string into `DATABASE_URL`; it also generates `JWT_SECRET`.
4. Once the service is deployed, open `/api/health` on the deployed URL. Confirm that `storage` reports `PostgreSQL`.
5. Create an account and complete the review, invite, role, and history tests on the deployed site.

The Render free Postgres plan is for short demos and expires after 30 days according to current Render documentation. For longer retention, connect an external managed PostgreSQL database or use a paid persistent database plan.

### Use an external database (for example, Supabase)

Set these in the backend hosting environment, not in browser code:

- `DATABASE_URL`: server-side PostgreSQL connection string.
- `DATABASE_SSLMODE`: use `require` for an external TLS database unless the provider specifies another setting.
- `JWT_SECRET`: long, randomly generated secret (at least 32 bytes for hosted use).
- `JWT_TTL_SECONDS`: optional; defaults to `43200` (12 hours).

Keep database credentials and secrets out of Git, screenshots, frontend variables, and public issue trackers. Never put the database URL or JWT secret in a `VITE_` variable.

## Verification status

- Backend tests: 10 passed in the latest local test run, including anonymous demo review and isolation.
- Python syntax compilation: passed.
- Frontend JSX syntax parsing: passed.
- Vite production bundle: not yet verified in the generation environment because npm package-registry network access failed. Run `npm install` and `npm run build:verify` locally or let the included GitHub Actions workflow run on GitHub before submitting.

## Demo mode behavior

`POST /api/auth/demo` provisions a distinct sample workspace and returns a signed 12-hour token. Visitors can run reviews, inspect findings, revise copy, add custom rules, upload guideline text, view history and insights, and make demo reviewer decisions. Demo sessions cannot access team administration. Old demo workspaces and their review data are cleaned up when a new demo session is opened after they are more than 24 hours old. Use a registered account for lasting workspace history.

## Security boundaries

This is a hackathon MVP, not a fully hardened identity service. Email verification, account recovery, MFA, login rate limiting, invite-code expiration/rotation, and PostgreSQL Row Level Security policies remain future work. Review the code and database provider's security guidance before storing sensitive real customer information.
