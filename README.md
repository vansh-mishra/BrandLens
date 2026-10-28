## Render deployment troubleshooting
[`link`](https://brandlens-demo-98xc.onrender.com)
This repository includes a `Dockerfile` and a Docker-based `render.yaml`. The Docker build uses Node to compile the React frontend and Python to run FastAPI, avoiding a mixed-toolchain assumption in a single native runtime.

# BrandLens — evidence-backed brand governance

**BrandLens catches potentially off-brand copy before publication.** It checks content against approved rules and facts, explains each finding with its source, proposes a correction, and leaves the decision to a human reviewer.

> **Demo data notice:** LumaLeaf is a fictional skincare brand. The sample policies and facts are made up for this prototype. Do not treat them as real product claims or legal advice.

## What works in this MVP

- **Review Studio:** paste text, choose a publishing channel, run a review, inspect severity and a heuristic alignment score.
- **Source-linked findings:** each built-in finding displays the configured policy passage, source title, and section.
- **Constrained optional LLM pass:** if an OpenAI API key is configured, the second analysis pass receives only the reviewed copy and the approved rule/fact catalog. Its findings are accepted only if the source ID is valid and the quoted text is an exact substring of the content. API failures fall back to deterministic checks.
- **Suggested corrections:** select “Apply and recheck” to revise the content and rerun the check. Suggestions are never applied automatically.
- **Optional authentication:** visitors can enter an isolated demo workspace without signing up; registered creators submit/revise content, and reviewer/admin accounts can approve, reject, or request revisions. Role permissions are enforced by the backend and decisions are recorded.
- **Brand Library:** inspect active rules and approved demo facts, add a structured rule, and upload `.txt`, `.md`, `.csv`, or text-based `.pdf` guidelines for storage and manual inspection.
- **History and insights:** saved reviews, decision history, status counts, severity counts, and JSON export.
- **No-key local demo:** the app works without an LLM API key using deterministic checks.

## Architecture

- **Frontend:** React + Vite + Lucide icons
- **API:** Python + FastAPI + Pydantic
- **Local persistence:** SQLite by default
- **Hosted persistence:** PostgreSQL when `DATABASE_URL` is configured (for example, a managed Supabase PostgreSQL database)
- **Authentication:** PBKDF2-SHA256 password hashing and signed, expiring HS256 bearer tokens; permissions are looked up server-side on each request
- **Optional analysis:** OpenAI Responses API, configured using environment variables
- **File extraction:** `pypdf` for text-based PDFs

For local development, SQLite keeps setup straightforward. For a hosted judging demo, configure `DATABASE_URL` with a managed PostgreSQL connection string so user accounts, workspace membership, reviews, decisions, custom rules, and uploaded guideline text survive service restarts/redeploys. The app creates/migrates its tables at startup. This is not a full pgvector/RAG implementation; the demo uses an explicit rule catalog and validated source references.

## Run locally

Requirements: Python 3.10+ and Node.js 18+.

### 1. Start the API

```bash
cd backend
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

API health check: `http://127.0.0.1:8000/api/health`  
Interactive API docs: `http://127.0.0.1:8000/docs`

### 2. Start the frontend in a second terminal

```bash
cd frontend
npm install
npm run dev
```

Open the local URL printed by Vite, usually `http://localhost:5173`. Choose **Explore demo without signing up** to try the product immediately, or sign in/create an account for a persistent team workspace. Each demo session has its own isolated sample workspace. Tokens expire after 12 hours; session data older than 24 hours is cleaned up when a later demo session starts.

### 3. Try the core flow

1. Open **Review studio**.
2. Click **Problematic copy** and run the brand check.
3. Inspect each finding's source and suggested correction.
4. Apply a correction and confirm the copy is checked again.
5. To test an approval, create a second account using the workspace invite code, then assign it the **Brand reviewer** role from **Team access**. Reviewers/admins can approve, reject, or request revisions; creators cannot make final decisions.
6. Open **Review history**, load the review, and inspect **Brand library** and **Insights**.

The local SQLite database is created automatically at `backend/data/brandlens.db`. Delete that file to reset local accounts, workspace data, history, and custom rules. When `DATABASE_URL` is set, the app uses PostgreSQL instead of SQLite.

## Optional demo access and accounts

- **No account needed:** choose **Explore demo without signing up** on the landing page. The demo runs the same review studio, brand library, review history, insights, source-backed findings, corrections, and reviewer decisions. Its sample data and review history are isolated from other visitors. Team administration is only available to registered workspace admins.
- Demo sessions use an expiring token and are cleaned up after 24 hours when another demo session is started. Use a registered account when you need a durable workspace or team management.
- Open the site and choose **Create account**. The first account without an invite code creates a new private workspace and becomes its `brand_admin`.
- From **Team access**, copy the workspace invite code and share it only with intended teammates. A new account using this code joins that workspace as a `content_creator`.
- The workspace admin can change teammates to `brand_reviewer` or `brand_admin`. The API checks the current role stored in the database before allowing decisions or rule creation.
- A reviewer/admin can approve, reject, or request revisions. A content creator can submit and revise copy but cannot finalise a decision.
- Signed bearer tokens expire after 12 hours by default. The frontend keeps the token in `sessionStorage`; signing out removes it from that browser tab.

**Security scope:** this is a hackathon-ready authentication layer, not a complete identity platform. It does not yet provide email verification, password reset, MFA, rate limiting, or PostgreSQL Row Level Security policies. Application queries are workspace-scoped, and database credentials must remain server-side. Do not use it as a production system for sensitive customer data without further security review. Workspace invite codes do not expire, so share them privately.

## Persistent PostgreSQL for deployment

For a public demo, use the provided Render Blueprint to provision managed PostgreSQL automatically, or connect an existing managed PostgreSQL database such as Supabase. For Supabase, get the server-side connection string from **Connect** in the dashboard; use the shared session pooler if the host cannot reach the direct IPv6 endpoint. Keep the database password private. The backend uses psycopg with prepared statements disabled and applies the `DATABASE_SSLMODE` value when the URL does not already specify an SSL mode.

The included Render Blueprint provisions a PostgreSQL database in Singapore, wires its private connection string into `DATABASE_URL`, and generates `JWT_SECRET` automatically. It sets `DATABASE_SSLMODE=disable` because the Render database connection is private and within the same Render region. The free Render Postgres plan is intended for a short demo and expires after 30 days. For a Supabase/external Postgres database instead, replace `DATABASE_URL` with that provider's SSL connection string and set `DATABASE_SSLMODE=require`. If deploying without the Blueprint, configure both values and a long random `JWT_SECRET` manually. Never commit `.env` or database credentials.

For local-only work, leave `DATABASE_URL` blank. SQLite is convenient locally but is not durable on a free Render web service. Render's current documentation says free web service files are lost on restart/redeploy/spin-down, and its free Postgres databases expire after 30 days. The included Blueprint is therefore suitable for hackathon judging and short demos, not indefinite retention. See [Render free-instance limits](https://render.com/docs/free), [Render Blueprint database wiring](https://render.com/docs/infrastructure-as-code), [Supabase Postgres connection guidance](https://supabase.com/docs/guides/database/connecting-to-postgres), and [Render environment variables](https://render.com/docs/configure-environment-variables).

## Optional OpenAI analysis

The application runs without an API key. To enable an additional model-based analysis pass:

1. Copy `backend/.env.example` to `backend/.env` or set environment variables in your shell.
2. Set `OPENAI_API_KEY` and, if needed, `OPENAI_MODEL` to a model available to your API account.
3. Install the backend requirements and start the API from a shell that has those variables loaded.

The API loads `backend/.env` at startup. With the optional LLM enabled, reviewed text and the provided approved sources are sent to the configured OpenAI API. Do not use confidential customer material in the demo. Do not commit secrets to GitHub.

## Verify the production frontend build

From the project root, run:

```bash
cd frontend
npm install
npm run build:verify
```

A successful check prints `Frontend production build verified.` and confirms that Vite generated `dist/index.html` plus JavaScript and CSS bundles under `dist/assets`. The repository includes a GitHub Actions workflow at `.github/workflows/frontend-build.yml` that runs this check for frontend changes and pull requests. A passing build verifies compilation and bundle output; it does not replace a browser smoke test against the API.

## Deploy a public demo with Render

The repository includes `render.yaml` for a single web service that builds the React frontend and serves it from FastAPI. Push the project to GitHub, create a Render Web Service from that repository, and let Render use the blueprint settings. The service should expose `/` for the interface and `/api/health` for a quick smoke test.

**Persistence setup:** When you deploy using the included `render.yaml` Blueprint, Render provisions the `brandlens-db` PostgreSQL database and injects its connection string into `DATABASE_URL`; you do not need to add that value manually. Confirm `/api/health` reports `PostgreSQL` after deployment. If you create a web service without using the Blueprint, connect a managed PostgreSQL database manually and set `DATABASE_URL`, `DATABASE_SSLMODE`, and a strong `JWT_SECRET` before starting the service. The backend intentionally refuses to start on Render without `DATABASE_URL` so it cannot silently use an ephemeral SQLite file for account data. Render's free Postgres databases currently expire after 30 days, so use an external managed database such as Supabase or a paid persistent database for longer retention. A free Render web service may also spin down after inactivity, causing a cold-start delay; test the link before recording or submitting. See [Render's free-instance guide](https://render.com/docs/free), [Render Blueprint database wiring](https://render.com/docs/infrastructure-as-code), and [Supabase Postgres connection guidance](https://supabase.com/docs/guides/database/connecting-to-postgres).

## API overview

| Method | Route | Purpose |
|---|---|---|
| `GET` | `/api/health` | Service, storage, and analysis mode (public health check) |
| `POST` | `/api/auth/demo` | Start an isolated demo session without an account |
| `POST` | `/api/auth/register` | Create account/workspace or join with invite code |
| `POST` | `/api/auth/login` | Authenticate and receive a bearer token |
| `GET` | `/api/auth/me` | Read the authenticated account and workspace |
| `GET` | `/api/team` | List team and invite code (workspace admin only) |
| `PATCH` | `/api/team/users/{user_id}/role` | Assign a workspace role (workspace admin only) |
| `GET` | `/api/brand` | Demo brand profile |
| `GET` | `/api/rules` | Active brand rules |
| `POST` | `/api/rules` | Add a structured rule |
| `GET` | `/api/facts` | Approved demo facts |
| `GET` | `/api/guidelines` | Uploaded guideline metadata |
| `POST` | `/api/guidelines/upload` | Store text/Markdown/CSV/PDF guideline |
| `POST` | `/api/reviews` | Create a review and findings |
| `GET` | `/api/reviews` | List review history |
| `GET` | `/api/reviews/{id}` | Load a review with findings/decisions |
| `POST` | `/api/reviews/{id}/revise` | Save revised text and re-run analysis |
| `POST` | `/api/reviews/{id}/decision` | Approve, reject, or request revision |
| `GET` | `/api/reviews/{id}/export` | Return a review export payload |
| `GET` | `/api/metrics` | Demo workspace metrics |

## Tests

From the project root:

```bash
python -m pip install -r backend/requirements.txt pytest
pytest -q
```

## Known limitations to state honestly in a demo

- Email verification, password recovery, multi-factor authentication, login rate limiting, and PostgreSQL Row Level Security policies are not implemented; perform a security review before any real-customer use.
- Uploaded guideline files are stored and text extracted, but new rules are **not** automatically generated from them. A human must create and approve structured rules.
- Findings and the alignment score are a prototype aid, not a legal, regulatory, or factual certification.
- The included checks are deliberately limited. Measure precision and recall on a labelled test set before presenting accuracy claims.
- SQLite is for local development. Hosted persistence requires `DATABASE_URL` configured to a managed PostgreSQL instance; the backend database adapter is not yet load-tested for multi-instance/high-concurrency production.
- Image/visual asset review, pgvector retrieval, and advanced insights remain future work.

## Hackathon demo principle

Show the complete loop, not a feature list: **bad copy → source-backed finding → chosen correction → recheck → reviewer decision → audit record**. Be clear about what is deterministic, what uses an optional model, and what remains human judgment.
