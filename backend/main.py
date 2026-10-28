from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
load_dotenv(ROOT / ".env")
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
DATABASE_SSLMODE = os.getenv("DATABASE_SSLMODE", "require").strip().lower()
if os.getenv("RENDER") and not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is required on Render so workspace data is not stored on an ephemeral disk.")
DB_PATH = Path(os.getenv("DATABASE_PATH", str(DATA_DIR / "brandlens.db")))
JWT_SECRET_VALUE = os.getenv("JWT_SECRET", "local-development-secret-change-before-deploy")
if os.getenv("RENDER") and (len(JWT_SECRET_VALUE.encode("utf-8")) < 32 or JWT_SECRET_VALUE == "local-development-secret-change-before-deploy"):
    raise RuntimeError("Set a strong JWT_SECRET in the hosted environment before starting BrandLens.")
JWT_SECRET = JWT_SECRET_VALUE.encode("utf-8")
JWT_TTL_SECONDS = int(os.getenv("JWT_TTL_SECONDS", "43200"))

app = FastAPI(
    title="BrandLens API",
    description="Evidence-backed brand governance and pre-publication content review.",
    version="0.2.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(","),
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

SEED_RULES = [
    {
        "id": "R-001", "title": "Avoid the phrase 'chemical-free'", "category": "Terminology",
        "severity": "medium", "pattern": r"\bchemical[- ]free\b",
        "guidance": "Avoid absolute language about chemicals. Describe specific ingredients or formulation facts only when they are approved.",
        "replacement": "Explore the ingredients in our thoughtfully formulated products.",
        "source_title": "LumaLeaf Brand Guide", "source_section": "§2.1 Approved terminology",
        "source_excerpt": "Do not use 'chemical-free'. Prefer specific, verifiable ingredient language and avoid implying that products contain no chemicals.",
    },
    {
        "id": "R-002", "title": "Environmental claims require evidence", "category": "Claims & evidence",
        "severity": "high", "pattern": r"\b(?:100%\s*(?:sustainable|eco[- ]?friendly|green)|zero[- ]?(?:impact|carbon|waste)|carbon[- ]neutral|planet[- ]friendly|good for the planet)\b",
        "guidance": "Absolute environmental claims must be supported by a specific, approved fact. Avoid broad claims that imply a product has no environmental impact.",
        "replacement": "Our refill pouch uses 70% less packaging plastic by weight than our standard 250 ml bottle.",
        "source_title": "LumaLeaf Claims Policy", "source_section": "§3.2 Environmental claims",
        "source_excerpt": "Avoid absolute environmental claims such as 'zero impact' and '100% sustainable'. Use only approved, specific comparisons and preserve their exact scope.",
    },
    {
        "id": "R-003", "title": "Medical claims are not approved", "category": "Claims & evidence",
        "severity": "critical", "pattern": r"\b(?:clinically proven|cures?\s+(?:acne|eczema|rosacea|psoriasis)|treats?\s+(?:acne|eczema|rosacea|psoriasis)|heals?\s+(?:acne|eczema)|eliminates?\s+(?:acne|eczema))\b",
        "guidance": "Do not make medical or clinical efficacy claims unless the exact claim has been reviewed and approved with appropriate evidence.",
        "replacement": "Explore LumaLeaf's straightforward approach to skincare.",
        "source_title": "LumaLeaf Claims Policy", "source_section": "§4.1 Medical and efficacy claims",
        "source_excerpt": "Medical, therapeutic, and clinical efficacy claims are prohibited in consumer copy unless they have been explicitly reviewed and approved. An AI-generated statement is not evidence.",
    },
    {
        "id": "R-004", "title": "Avoid guarantees and instant-result promises", "category": "Claims & evidence",
        "severity": "high", "pattern": r"\b(?:guaranteed results?|instant results?|works instantly|never fails|miracle cure)\b",
        "guidance": "Do not promise guaranteed outcomes or instant effects. Use only substantiated product facts and realistic descriptions.",
        "replacement": "Learn about the formula and how it fits into your skincare routine.",
        "source_title": "LumaLeaf Claims Policy", "source_section": "§4.2 Performance promises",
        "source_excerpt": "Do not promise guaranteed results or instant effects. Product outcomes can vary and must not be represented as certain without approved evidence.",
    },
    {
        "id": "R-005", "title": "Use a calm, informative voice", "category": "Tone of voice",
        "severity": "low", "pattern": r"\b(?:AMAZING|MIRACLE|BEST EVER|BUY NOW|INSANE RESULTS)\b|!{2,}",
        "guidance": "LumaLeaf voice is clear, calm, practical, and informative. Avoid shouting, overstatement, and pressure tactics.",
        "replacement": "Discover a simple addition to your skincare routine.",
        "source_title": "LumaLeaf Brand Guide", "source_section": "§1.3 Tone of voice",
        "source_excerpt": "Be clear, calm, practical, and informative. Avoid all-caps promotional language, exaggerated superlatives, and pressure tactics.",
    },
]

SEED_FACTS = [
    {"id": "F-001", "title": "Calm Cleanser formula", "content": "LumaLeaf Calm Cleanser contains 2% niacinamide.", "source_title": "LumaLeaf Approved Facts Sheet", "source_section": "§1.1 Product specifications"},
    {"id": "F-002", "title": "Refill pouch packaging comparison", "content": "The LumaLeaf refill pouch uses 70% less packaging plastic by weight than the standard 250 ml bottle.", "source_title": "LumaLeaf Approved Facts Sheet", "source_section": "§1.2 Packaging comparisons"},
    {"id": "F-003", "title": "Returns policy", "content": "Unopened LumaLeaf products can be returned within 30 days of purchase.", "source_title": "LumaLeaf Approved Facts Sheet", "source_section": "§2.1 Customer policy"},
    {"id": "F-004", "title": "Product positioning", "content": "LumaLeaf is a fictional skincare brand focused on straightforward routines and ingredient transparency.", "source_title": "LumaLeaf Approved Facts Sheet", "source_section": "§1.0 Brand overview"},
]

SCHEMA = """
CREATE TABLE IF NOT EXISTS workspaces (
  id TEXT PRIMARY KEY, name TEXT NOT NULL, invite_code TEXT NOT NULL UNIQUE, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY, email TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL,
  name TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'content_creator', workspace_id TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS rules (
  id TEXT PRIMARY KEY, title TEXT NOT NULL, category TEXT NOT NULL, severity TEXT NOT NULL,
  pattern TEXT NOT NULL, guidance TEXT NOT NULL, replacement TEXT NOT NULL,
  source_title TEXT NOT NULL, source_section TEXT NOT NULL, source_excerpt TEXT NOT NULL,
  active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL, workspace_id TEXT
);
CREATE TABLE IF NOT EXISTS facts (
  id TEXT PRIMARY KEY, title TEXT NOT NULL, content TEXT NOT NULL,
  source_title TEXT NOT NULL, source_section TEXT NOT NULL, created_at TEXT NOT NULL, workspace_id TEXT
);
CREATE TABLE IF NOT EXISTS guidelines (
  id TEXT PRIMARY KEY, filename TEXT NOT NULL, content TEXT NOT NULL, created_at TEXT NOT NULL, workspace_id TEXT
);
CREATE TABLE IF NOT EXISTS reviews (
  id TEXT PRIMARY KEY, content TEXT NOT NULL, channel TEXT NOT NULL, status TEXT NOT NULL,
  score INTEGER NOT NULL, summary TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, workspace_id TEXT
);
CREATE TABLE IF NOT EXISTS findings (
  id TEXT PRIMARY KEY, review_id TEXT NOT NULL, title TEXT NOT NULL, category TEXT NOT NULL,
  severity TEXT NOT NULL, quote TEXT NOT NULL, explanation TEXT NOT NULL, source_title TEXT NOT NULL,
  source_section TEXT NOT NULL, source_excerpt TEXT NOT NULL, suggestion TEXT NOT NULL,
  confidence REAL NOT NULL, rule_id TEXT, fact_id TEXT, status TEXT NOT NULL DEFAULT 'open',
  FOREIGN KEY(review_id) REFERENCES reviews(id)
);
CREATE TABLE IF NOT EXISTS decisions (
  id TEXT PRIMARY KEY, review_id TEXT NOT NULL, decision TEXT NOT NULL, reviewer TEXT NOT NULL,
  comment TEXT NOT NULL, created_at TEXT NOT NULL, FOREIGN KEY(review_id) REFERENCES reviews(id)
);
"""


class HybridRow(dict):
    """Mapping row that also supports SQLite-style positional access."""
    def __getitem__(self, key):
        if isinstance(key, int):
            return list(self.values())[key]
        return super().__getitem__(key)


def hybrid_row(cursor):
    names = [column.name for column in cursor.description]
    return lambda values: HybridRow(zip(names, values))


class PostgresConnection:
    """Small DB-API adapter to keep the same query code working on SQLite or Postgres."""
    def __init__(self, connection):
        self.connection = connection

    def execute(self, statement, params=()):
        # Application SQL uses qmark placeholders for local SQLite; psycopg uses %s.
        return self.connection.execute(statement.replace("?", "%s"), params or (), prepare=False)

    def executescript(self, script):
        for statement in script.split(";"):
            if statement.strip():
                self.execute(statement.strip())

    def __enter__(self):
        self.connection.__enter__()
        return self

    def __exit__(self, exc_type, exc, tb):
        return self.connection.__exit__(exc_type, exc, tb)


def connect():
    if DATABASE_URL:
        try:
            import psycopg
        except ImportError as exc:
            raise RuntimeError("DATABASE_URL is set but psycopg is not installed. Install backend requirements.") from exc
        dsn = DATABASE_URL
        if "sslmode=" not in dsn.lower():
            dsn += ("&" if "?" in dsn else "?") + f"sslmode={DATABASE_SSLMODE}"
        return PostgresConnection(psycopg.connect(dsn, row_factory=hybrid_row))
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def rowdict(row: Any | None) -> dict[str, Any] | None:
    return dict(row) if row else None


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _db_columns(conn, table: str) -> set[str]:
    if DATABASE_URL:
        rows = conn.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name=?", (table,)).fetchall()
        return {row["column_name"] for row in rows}
    return {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def init_db() -> None:
    if not DATABASE_URL:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
    with connect() as conn:
        conn.executescript(SCHEMA)
        # Migrate older SQLite demo databases and existing Postgres deployments in place.
        for table in ("rules", "facts", "guidelines", "reviews"):
            if "workspace_id" not in _db_columns(conn, table):
                conn.execute(f"ALTER TABLE {table} ADD COLUMN workspace_id TEXT")
        if conn.execute("SELECT COUNT(*) FROM rules").fetchone()[0] == 0:
            for rule in SEED_RULES:
                conn.execute(
                    """INSERT INTO rules (id,title,category,severity,pattern,guidance,replacement,source_title,source_section,source_excerpt,active,created_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?,1,?)""",
                    (rule["id"], rule["title"], rule["category"], rule["severity"], rule["pattern"], rule["guidance"], rule["replacement"], rule["source_title"], rule["source_section"], rule["source_excerpt"], now_iso()),
                )
        if conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0] == 0:
            for fact in SEED_FACTS:
                conn.execute(
                    "INSERT INTO facts (id,title,content,source_title,source_section,created_at) VALUES (?,?,?,?,?,?)",
                    (fact["id"], fact["title"], fact["content"], fact["source_title"], fact["source_section"], now_iso()),
                )


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _decode_b64url(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def issue_token(user_id: str, *, demo: bool = False) -> str:
    now = int(time.time())
    header = _b64url(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    claims = {"sub": user_id, "iat": now, "exp": now + JWT_TTL_SECONDS}
    if demo:
        claims["demo"] = True
    payload = _b64url(json.dumps(claims, separators=(",", ":")).encode())
    signing_input = f"{header}.{payload}".encode("ascii")
    signature = _b64url(hmac.new(JWT_SECRET, signing_input, hashlib.sha256).digest())
    return f"{header}.{payload}.{signature}"


def decode_token(token: str) -> dict[str, Any]:
    try:
        header, payload, signature = token.split(".")
        signing_input = f"{header}.{payload}".encode("ascii")
        expected = _b64url(hmac.new(JWT_SECRET, signing_input, hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected):
            raise ValueError("Invalid token signature")
        claims = json.loads(_decode_b64url(payload))
        if claims.get("exp", 0) < int(time.time()) or not claims.get("sub"):
            raise ValueError("Token expired")
        return claims
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Session is invalid or expired. Please sign in again.") from exc


def get_current_user(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Sign in to access this workspace.")
    claims = decode_token(authorization.split(" ", 1)[1].strip())
    with connect() as conn:
        row = conn.execute(
            """SELECT u.id,u.email,u.name,u.role,u.workspace_id,u.created_at,w.name AS workspace_name,w.invite_code
               FROM users u JOIN workspaces w ON w.id=u.workspace_id WHERE u.id=?""",
            (claims["sub"],),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=401, detail="Account no longer exists. Please sign in again.")
    result = dict(row)
    result["is_demo"] = bool(claims.get("demo", False))
    return result


def require_role(user: dict[str, Any], *roles: str) -> None:
    if user.get("role") not in roles:
        raise HTTPException(status_code=403, detail="Your workspace role does not allow this action.")


def public_user(user: dict[str, Any]) -> dict[str, Any]:
    result = {key: user[key] for key in ("id", "email", "name", "role", "workspace_id", "workspace_name") if key in user}
    if "is_demo" in user:
        result["is_demo"] = bool(user["is_demo"])
    if user.get("role") == "brand_admin" and user.get("invite_code"):
        result["invite_code"] = user["invite_code"]
    return result


def password_hash(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 310_000)
    return f"pbkdf2_sha256$310000${_b64url(salt)}${_b64url(digest)}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, rounds, salt_value, digest_value = encoded.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        actual = password_hash(password, _decode_b64url(salt_value))
        return hmac.compare_digest(actual, encoded)
    except Exception:
        return False


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=10, max_length=200)
    invite_code: str = Field(default="", max_length=80)


class LoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=1, max_length=200)


class RoleUpdateRequest(BaseModel):
    role: str


class ReviewRequest(BaseModel):
    content: str = Field(min_length=5, max_length=12000)
    channel: str = Field(default="Website", max_length=80)


class RevisionRequest(BaseModel):
    content: str = Field(min_length=1, max_length=12000)


class DecisionRequest(BaseModel):
    decision: str
    reviewer: str = Field(default="Brand reviewer", max_length=120)
    comment: str = Field(default="", max_length=1200)


class RuleRequest(BaseModel):
    title: str = Field(min_length=3, max_length=180)
    category: str = Field(default="Brand guidelines", max_length=80)
    severity: str = Field(default="medium")
    pattern: str = Field(min_length=1, max_length=240)
    guidance: str = Field(min_length=3, max_length=1200)
    replacement: str = Field(default="", max_length=1200)
    source_title: str = Field(default="Uploaded brand guideline", max_length=180)
    source_section: str = Field(default="Uploaded guidance", max_length=120)
    source_excerpt: str = Field(min_length=3, max_length=1200)


def get_rules(workspace_id: str) -> list[dict[str, Any]]:
    with connect() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM rules WHERE active = 1 AND (workspace_id IS NULL OR workspace_id = ?) ORDER BY id",
            (workspace_id,),
        )]


def get_facts(workspace_id: str) -> list[dict[str, Any]]:
    with connect() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM facts WHERE workspace_id IS NULL OR workspace_id = ? ORDER BY id",
            (workspace_id,),
        )]


def severity_weight(severity: str) -> int:
    return {"critical": 28, "high": 18, "medium": 10, "low": 4}.get(severity, 8)


def is_fact_supported(text: str, facts: list[dict[str, Any]]) -> dict[str, Any] | None:
    normalized = re.sub(r"[^a-z0-9% ]", " ", text.lower())
    for fact in facts:
        fact_norm = re.sub(r"[^a-z0-9% ]", " ", fact["content"].lower())
        # A fact is treated as matched only when the reviewed text contains its important
        # numeric signature or several distinctive fact terms; this is a demo safeguard,
        # not a substitute for legal or factual verification.
        percent = re.search(r"\b\d+(?:\.\d+)?%", fact_norm)
        if percent and percent.group(0) in normalized and any(w in normalized for w in ["refill", "pouch", "packaging", "plastic"]):
            return fact
        if "2%" in fact_norm and "2%" in normalized and "niacinamide" in normalized:
            return fact
        if "30 days" in fact_norm and "30 days" in normalized and any(w in normalized for w in ["return", "unopened", "refund"]):
            return fact
    return None


def find_quote(content: str, match: re.Match[str]) -> str:
    start, end = match.span()
    left, right = max(0, start - 65), min(len(content), end + 65)
    quote = content[left:right].strip()
    if left > 0:
        quote = "…" + quote
    if right < len(content):
        quote = quote + "…"
    return quote


def analyze_content(content: str, rules: list[dict[str, Any]], facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    matched_spans: list[tuple[int, int]] = []

    for rule in rules:
        try:
            pattern = re.compile(rule["pattern"], re.IGNORECASE)
        except re.error:
            continue
        for match in pattern.finditer(content):
            key = (rule["id"], match.group(0).lower())
            if key in seen:
                continue
            seen.add(key)
            matched_spans.append(match.span())
            suggestion = rule["replacement"] or "Revise this sentence to align with the cited guidance."
            findings.append({
                "id": str(uuid.uuid4()), "title": rule["title"], "category": rule["category"],
                "severity": rule["severity"], "quote": match.group(0), "explanation": rule["guidance"],
                "source_title": rule["source_title"], "source_section": rule["source_section"],
                "source_excerpt": rule["source_excerpt"], "suggestion": suggestion,
                "confidence": 0.98 if rule["severity"] in ("critical", "high") else 0.93,
                "rule_id": rule["id"], "fact_id": None, "status": "open",
            })

    # Flag suspicious numerical/absolute statements only when they lack an approved fact match.
    # The finding cites the claims policy; it does not assume that the claim is false.
    unsupported_patterns = [
        re.compile(r"\b\d{1,3}(?:\.\d+)?\s*%(?!\w)", re.IGNORECASE),
        re.compile(r"\b(?:proven|guarantees?|guaranteed|clinically|scientifically validated)\b", re.IGNORECASE),
    ]
    for pattern in unsupported_patterns:
        for match in pattern.finditer(content):
            if any(a <= match.start() < b for a, b in matched_spans):
                continue
            local = content[max(0, match.start() - 100):min(len(content), match.end() + 100)]
            supported = is_fact_supported(local, facts)
            if supported:
                continue
            key = ("UNVERIFIED", match.group(0).lower())
            if key in seen:
                continue
            seen.add(key)
            findings.append({
                "id": str(uuid.uuid4()), "title": "Claim needs an approved source", "category": "Claims & evidence",
                "severity": "high", "quote": match.group(0),
                "explanation": "This wording contains a statistic or evidence-oriented term, but the approved knowledge base does not contain a matching fact. The claim is unverified, not automatically false.",
                "source_title": "LumaLeaf Claims Policy", "source_section": "§3.1 Evidence required",
                "source_excerpt": "Quantitative, scientific, and performance claims must be supported by an approved fact or evidence source before publication.",
                "suggestion": "Add the exact approved evidence and its scope, or remove the unsupported part of the claim.",
                "confidence": 0.86, "rule_id": None, "fact_id": None, "status": "open",
            })

    # Low-cost plain-language accessibility/formatting checks complement the approved rules.
    if len(re.findall(r"[A-Z]{5,}", content)) >= 2 and not any(f["title"] == "Use a calm, informative voice" for f in findings):
        findings.append({
            "id": str(uuid.uuid4()), "title": "Check all-caps wording", "category": "Tone of voice", "severity": "low",
            "quote": "All-caps wording", "explanation": "Several all-caps words can make copy feel more aggressive than the approved calm and informative voice.",
            "source_title": "LumaLeaf Brand Guide", "source_section": "§1.3 Tone of voice",
            "source_excerpt": "Be clear, calm, practical, and informative. Avoid all-caps promotional language.",
            "suggestion": "Use sentence case and describe the benefit plainly.", "confidence": 0.78,
            "rule_id": "R-005", "fact_id": None, "status": "open",
        })

    # De-duplicate overlapping findings while retaining a distinct issue type and source.
    return findings


def add_optional_llm_findings(content: str, channel: str, rules: list[dict[str, Any]], facts: list[dict[str, Any]], deterministic: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Optional LLM pass. Any candidate without a valid source ID or exact content quote is discarded.

    The local deterministic checks remain available when there is no API key or the model is down.
    Only the text being reviewed and the limited approved sources are sent to the configured provider.
    """
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return []
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, timeout=18.0, max_retries=1)
        source_catalog = []
        for rule in rules:
            source_catalog.append({"id": rule["id"], "kind": "rule", "title": rule["title"], "category": rule["category"],
                                   "severity": rule["severity"], "guidance": rule["guidance"], "source_title": rule["source_title"],
                                   "source_section": rule["source_section"], "source_excerpt": rule["source_excerpt"],
                                   "replacement": rule["replacement"]})
        for fact in facts:
            source_catalog.append({"id": fact["id"], "kind": "fact", "title": fact["title"], "content": fact["content"],
                                   "source_title": fact["source_title"], "source_section": fact["source_section"],
                                   "source_excerpt": fact["content"]})
        prompt = {
            "channel": channel,
            "content_to_review": content,
            "approved_sources": source_catalog,
            "existing_deterministic_findings": [{"quote": f["quote"], "title": f["title"]} for f in deterministic],
            "task": "Find only additional meaningful brand, tone, terminology, accessibility, or claim-evidence problems not already caught by the deterministic findings. Do not rewrite generally. Every finding must cite exactly one source ID from approved_sources. Never invent facts or policy. If no source supports a concern, omit it. Quotes must be verbatim substrings of content_to_review. A missing source is not proof that a claim is false. Return JSON with a findings array. Each finding needs title, category, severity (critical/high/medium/low), quote, explanation, source_id, suggestion, confidence (0 to 1)."
        }
        response = client.responses.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
            instructions="You are the evidence-constrained analysis layer for BrandLens, a brand compliance review tool. Be conservative. Cite only the supplied source catalog. Do not provide legal advice. Return valid JSON only.",
            input=json.dumps(prompt, ensure_ascii=False),
            text={"format": {"type": "json_object"}},
            max_output_tokens=1800,
        )
        payload = json.loads(response.output_text)
        candidates = payload.get("findings", [])
        source_by_id = {s["id"]: s for s in source_catalog}
        existing_quotes = {f["quote"].strip().lower() for f in deterministic}
        accepted = []
        for item in candidates[:8] if isinstance(candidates, list) else []:
            if not isinstance(item, dict):
                continue
            source_id = str(item.get("source_id", ""))
            source = source_by_id.get(source_id)
            quote = str(item.get("quote", "")).strip()
            if not source or not quote or quote not in content or quote.lower() in existing_quotes:
                continue
            # Reject results whose cited phrase overlaps an existing deterministic quote.
            if any(q and (q in quote.lower() or quote.lower() in q) for q in existing_quotes):
                continue
            severity = str(item.get("severity", "medium")).lower()
            if severity not in {"critical", "high", "medium", "low"}:
                severity = "medium"
            confidence = item.get("confidence", 0.72)
            try:
                confidence = max(0.0, min(1.0, float(confidence)))
            except (TypeError, ValueError):
                confidence = 0.72
            accepted.append({
                "id": str(uuid.uuid4()), "title": str(item.get("title", "Additional brand check"))[:180],
                "category": str(item.get("category", source.get("category", "Brand guidelines")))[:80],
                "severity": severity, "quote": quote,
                "explanation": str(item.get("explanation", "Review this wording against the cited approved source."))[:1200],
                "source_title": source["source_title"], "source_section": source["source_section"],
                "source_excerpt": source["source_excerpt"],
                "suggestion": str(item.get("suggestion", source.get("replacement", "Revise against the cited source.")))[:1200],
                "confidence": confidence, "rule_id": source_id if source.get("kind") == "rule" else None,
                "fact_id": source_id if source.get("kind") == "fact" else None, "status": "open",
            })
            existing_quotes.add(quote.lower())
        return accepted
    except Exception:
        # Keep the deterministic review responsive; API/network/model failures are non-fatal.
        return []


def run_full_analysis(content: str, channel: str, rules: list[dict[str, Any]], facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deterministic = analyze_content(content, rules, facts)
    return deterministic + add_optional_llm_findings(content, channel, rules, facts, deterministic)


def score_for(findings: list[dict[str, Any]]) -> int:
    penalty = sum(severity_weight(f["severity"]) for f in findings)
    return max(0, min(100, 100 - penalty))


def summary_for(findings: list[dict[str, Any]]) -> str:
    if not findings:
        return "No configured brand-rule violations were detected. Review approved facts and context before publishing."
    critical = sum(1 for f in findings if f["severity"] == "critical")
    high = sum(1 for f in findings if f["severity"] == "high")
    if critical:
        return f"Found {len(findings)} issue(s), including {critical} critical item(s). Human review is required before publishing."
    if high:
        return f"Found {len(findings)} issue(s), including {high} high-severity item(s). Resolve or explicitly review them before publishing."
    return f"Found {len(findings)} item(s) to review. Apply corrections where appropriate, then send the revised version for approval."


def persist_findings(conn: sqlite3.Connection, review_id: str, findings: list[dict[str, Any]]) -> None:
    for f in findings:
        conn.execute(
            """INSERT INTO findings (id,review_id,title,category,severity,quote,explanation,source_title,source_section,source_excerpt,suggestion,confidence,rule_id,fact_id,status)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (f["id"], review_id, f["title"], f["category"], f["severity"], f["quote"], f["explanation"], f["source_title"], f["source_section"], f["source_excerpt"], f["suggestion"], f["confidence"], f.get("rule_id"), f.get("fact_id"), f.get("status", "open")),
        )


def serialize_review(review_id: str, workspace_id: str) -> dict[str, Any]:
    with connect() as conn:
        review = conn.execute("SELECT * FROM reviews WHERE id = ? AND workspace_id = ?", (review_id, workspace_id)).fetchone()
        if not review:
            raise HTTPException(status_code=404, detail="Review not found")
        findings = conn.execute("SELECT * FROM findings WHERE review_id = ? ORDER BY CASE severity WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END", (review_id,)).fetchall()
        decisions = conn.execute("SELECT * FROM decisions WHERE review_id = ? ORDER BY created_at DESC", (review_id,)).fetchall()
        result = dict(review)
        result["findings"] = [dict(f) for f in findings]
        result["decisions"] = [dict(d) for d in decisions]
        return result


@app.get("/api/health")
def health() -> dict[str, Any]:
    storage = "PostgreSQL" if DATABASE_URL else ("SQLite (ephemeral hosted fallback)" if os.getenv("RENDER") else "SQLite (local development)")
    return {"status": "ok", "service": "BrandLens API", "storage": storage,
            "auth": "JWT bearer sessions", "ai_mode": "optional OpenAI enrichment" if os.getenv("OPENAI_API_KEY") else "deterministic rules (no API key configured)"}


@app.post("/api/auth/demo")
def create_demo_session() -> dict[str, Any]:
    """Create an isolated, short-lived demo workspace without requiring registration."""
    now = datetime.now(timezone.utc)
    timestamp = now.isoformat()
    cutoff = (now - timedelta(hours=24)).isoformat()
    user_id = str(uuid.uuid4())
    workspace_id = str(uuid.uuid4())
    invite_code = secrets.token_urlsafe(12)
    # The reserved .invalid domain and unusable password hash keep guest sessions
    # separate from real accounts. The only way to use this identity is its signed demo token.
    email = f"demo-{uuid.uuid4().hex}@guest.brandlens.invalid"

    with connect() as conn:
        # Bound database growth: delete demo sessions older than 24 hours, including their data.
        expired = conn.execute(
            "SELECT id,workspace_id FROM users WHERE email LIKE ? AND created_at < ?",
            ("demo-%@guest.brandlens.invalid", cutoff),
        ).fetchall()
        for expired_user in expired:
            old_reviews = conn.execute(
                "SELECT id FROM reviews WHERE workspace_id=?", (expired_user["workspace_id"],)
            ).fetchall()
            for old_review in old_reviews:
                conn.execute("DELETE FROM decisions WHERE review_id=?", (old_review["id"],))
                conn.execute("DELETE FROM findings WHERE review_id=?", (old_review["id"],))
            conn.execute("DELETE FROM reviews WHERE workspace_id=?", (expired_user["workspace_id"],))
            conn.execute("DELETE FROM guidelines WHERE workspace_id=?", (expired_user["workspace_id"],))
            conn.execute("DELETE FROM rules WHERE workspace_id=?", (expired_user["workspace_id"],))
            conn.execute("DELETE FROM facts WHERE workspace_id=?", (expired_user["workspace_id"],))
            conn.execute("DELETE FROM users WHERE id=?", (expired_user["id"],))
            conn.execute("DELETE FROM workspaces WHERE id=?", (expired_user["workspace_id"],))

        conn.execute(
            "INSERT INTO workspaces (id,name,invite_code,created_at) VALUES (?,?,?,?)",
            (workspace_id, "LumaLeaf Demo Workspace", invite_code, timestamp),
        )
        conn.execute(
            "INSERT INTO users (id,email,password_hash,name,role,workspace_id,created_at) VALUES (?,?,?,?,?,?,?)",
            (user_id, email, "demo_login_disabled", "Demo Visitor", "brand_reviewer", workspace_id, timestamp),
        )
        row = conn.execute(
            """SELECT u.id,u.email,u.name,u.role,u.workspace_id,u.created_at,w.name AS workspace_name,w.invite_code
               FROM users u JOIN workspaces w ON w.id=u.workspace_id WHERE u.id=?""",
            (user_id,),
        ).fetchone()

    user = dict(row)
    user["is_demo"] = True
    return {"token": issue_token(user_id, demo=True), "user": public_user(user)}


@app.post("/api/auth/register")
def register(request: RegisterRequest) -> dict[str, Any]:
    email = request.email.strip().lower()
    name = request.name.strip()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        raise HTTPException(status_code=422, detail="Enter a valid email address.")
    if len(request.password) < 10 or not re.search(r"[A-Za-z]", request.password) or not re.search(r"\d", request.password):
        raise HTTPException(status_code=422, detail="Use a password with at least 10 characters, including a letter and a number.")
    user_id = str(uuid.uuid4())
    timestamp = now_iso()
    invite_code = request.invite_code.strip()
    try:
        with connect() as conn:
            if conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone():
                raise HTTPException(status_code=409, detail="An account with this email already exists.")
            if invite_code:
                workspace = conn.execute("SELECT id FROM workspaces WHERE invite_code = ?", (invite_code,)).fetchone()
                if not workspace:
                    raise HTTPException(status_code=422, detail="That workspace invite code is not valid.")
                workspace_id = workspace["id"]
                role = "content_creator"
            else:
                workspace_id = str(uuid.uuid4())
                role = "brand_admin"
                workspace_invite = secrets.token_urlsafe(9)
                conn.execute("INSERT INTO workspaces (id,name,invite_code,created_at) VALUES (?,?,?,?)",
                             (workspace_id, f"{name}'s BrandLens workspace", workspace_invite, timestamp))
            conn.execute("INSERT INTO users (id,email,password_hash,name,role,workspace_id,created_at) VALUES (?,?,?,?,?,?,?)",
                         (user_id, email, password_hash(request.password), name, role, workspace_id, timestamp))
            row = conn.execute(
                """SELECT u.id,u.email,u.name,u.role,u.workspace_id,u.created_at,w.name AS workspace_name,w.invite_code
                   FROM users u JOIN workspaces w ON w.id=u.workspace_id WHERE u.id=?""", (user_id,)
            ).fetchone()
    except HTTPException:
        raise
    except Exception as exc:
        # A unique constraint is the final guard against duplicate concurrent sign-ups.
        if "unique" in str(exc).lower() or "duplicate" in str(exc).lower():
            raise HTTPException(status_code=409, detail="An account with this email already exists.") from exc
        raise
    user = dict(row)
    return {"token": issue_token(user_id), "user": public_user(user)}


@app.post("/api/auth/login")
def login(request: LoginRequest) -> dict[str, Any]:
    email = request.email.strip().lower()
    with connect() as conn:
        row = conn.execute("SELECT id,password_hash FROM users WHERE email = ?", (email,)).fetchone()
    if not row or not verify_password(request.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Email or password is incorrect.")
    user = get_user_for_auth(row["id"])
    return {"token": issue_token(user["id"]), "user": public_user(user)}


def get_user_for_auth(user_id: str) -> dict[str, Any]:
    with connect() as conn:
        row = conn.execute(
            """SELECT u.id,u.email,u.name,u.role,u.workspace_id,u.created_at,w.name AS workspace_name,w.invite_code
               FROM users u JOIN workspaces w ON w.id=u.workspace_id WHERE u.id=?""", (user_id,)
        ).fetchone()
    if not row:
        raise HTTPException(status_code=401, detail="Account no longer exists.")
    return dict(row)


@app.get("/api/auth/me")
def auth_me(current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    return {"user": public_user(current_user)}


@app.get("/api/team")
def list_team(current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    require_role(current_user, "brand_admin")
    with connect() as conn:
        rows = conn.execute("SELECT id,name,email,role,created_at FROM users WHERE workspace_id=? ORDER BY created_at", (current_user["workspace_id"],)).fetchall()
    return {"items": [dict(row) for row in rows], "invite_code": current_user["invite_code"]}


@app.patch("/api/team/users/{user_id}/role")
def update_team_role(user_id: str, request: RoleUpdateRequest, current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    require_role(current_user, "brand_admin")
    if request.role not in {"content_creator", "brand_reviewer", "brand_admin"}:
        raise HTTPException(status_code=422, detail="Role must be content_creator, brand_reviewer, or brand_admin.")
    if user_id == current_user["id"] and request.role != "brand_admin":
        raise HTTPException(status_code=422, detail="You cannot remove your own workspace admin role.")
    with connect() as conn:
        found = conn.execute("SELECT id FROM users WHERE id=? AND workspace_id=?", (user_id, current_user["workspace_id"])).fetchone()
        if not found:
            raise HTTPException(status_code=404, detail="Team member not found in this workspace.")
        conn.execute("UPDATE users SET role=? WHERE id=? AND workspace_id=?", (request.role, user_id, current_user["workspace_id"]))
        row = conn.execute("SELECT id,name,email,role,created_at FROM users WHERE id=?", (user_id,)).fetchone()
    return {"item": dict(row)}


@app.get("/api/brand")
def brand(current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    return {"name": "LumaLeaf", "description": "A fictional skincare brand created for the BrandLens demonstration.",
            "voice": ["Clear", "Calm", "Practical", "Informative"],
            "publishing_rule": "AI flags are advisory. A human reviewer makes the final decision."}


@app.get("/api/rules")
def list_rules(current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    items = get_rules(current_user["workspace_id"])
    return {"items": items, "count": len(items)}


@app.post("/api/rules")
def add_rule(request: RuleRequest, current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    require_role(current_user, "brand_admin", "brand_reviewer")
    if request.severity not in {"critical", "high", "medium", "low"}:
        raise HTTPException(status_code=422, detail="Severity must be critical, high, medium, or low")
    try:
        re.compile(request.pattern)
    except re.error as exc:
        raise HTTPException(status_code=422, detail=f"Invalid regular expression: {exc}") from exc
    rule_id = f"R-{uuid.uuid4().hex[:6].upper()}"
    with connect() as conn:
        conn.execute(
            """INSERT INTO rules (id,title,category,severity,pattern,guidance,replacement,source_title,source_section,source_excerpt,active,created_at,workspace_id)
               VALUES (?,?,?,?,?,?,?,?,?,?,1,?,?)""",
            (rule_id, request.title, request.category, request.severity, request.pattern, request.guidance, request.replacement,
             request.source_title, request.source_section, request.source_excerpt, now_iso(), current_user["workspace_id"]),
        )
    return {"item": next(r for r in get_rules(current_user["workspace_id"]) if r["id"] == rule_id)}


@app.get("/api/facts")
def list_facts(current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    facts = get_facts(current_user["workspace_id"])
    return {"items": facts, "count": len(facts)}


@app.get("/api/guidelines")
def list_guidelines(current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    with connect() as conn:
        rows = conn.execute("SELECT id,filename,created_at,length(content) AS characters FROM guidelines WHERE workspace_id=? ORDER BY created_at DESC", (current_user["workspace_id"],)).fetchall()
    return {"items": [dict(r) for r in rows], "count": len(rows)}


@app.post("/api/guidelines/upload")
async def upload_guideline(file: UploadFile = File(...), current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    filename = file.filename or "uploaded-guideline.txt"
    extension = Path(filename).suffix.lower()
    if extension not in {".txt", ".md", ".csv", ".pdf"}:
        raise HTTPException(status_code=415, detail="Upload a .txt, .md, .csv, or .pdf guideline file")
    raw = await file.read()
    if len(raw) > 3 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Maximum file size is 3 MB")
    if extension == ".pdf":
        try:
            from pypdf import PdfReader
            import io
            reader = PdfReader(io.BytesIO(raw))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as exc:
            raise HTTPException(status_code=422, detail="Could not extract text from this PDF. Try a text or Markdown file.") from exc
    else:
        text = raw.decode("utf-8", errors="replace")
    if not text.strip():
        raise HTTPException(status_code=422, detail="No text could be extracted from this file")
    document_id = str(uuid.uuid4())
    with connect() as conn:
        conn.execute("INSERT INTO guidelines (id,filename,content,created_at,workspace_id) VALUES (?,?,?,?,?)", (document_id, filename, text[:100000], now_iso(), current_user["workspace_id"]))
    return {"item": {"id": document_id, "filename": filename, "characters": len(text), "preview": text[:1200]},
            "message": "Guideline stored. Review its extracted text before converting guidance into an active rule."}


@app.get("/api/metrics")
def metrics(current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    workspace_id = current_user["workspace_id"]
    with connect() as conn:
        totals = conn.execute("SELECT COUNT(*) AS total, AVG(score) AS avg_score FROM reviews WHERE workspace_id=?", (workspace_id,)).fetchone()
        pending = conn.execute("SELECT COUNT(*) FROM reviews WHERE workspace_id=? AND status IN ('pending','needs_revision')", (workspace_id,)).fetchone()[0]
        approved = conn.execute("SELECT COUNT(*) FROM reviews WHERE workspace_id=? AND status = 'approved'", (workspace_id,)).fetchone()[0]
        open_findings = conn.execute("SELECT COUNT(*) FROM findings f JOIN reviews r ON r.id=f.review_id WHERE r.workspace_id=? AND f.status='open'", (workspace_id,)).fetchone()[0]
        by_severity = conn.execute("SELECT f.severity,COUNT(*) AS count FROM findings f JOIN reviews r ON r.id=f.review_id WHERE r.workspace_id=? AND f.status='open' GROUP BY f.severity", (workspace_id,)).fetchall()
        recent = conn.execute("SELECT r.id,r.channel,r.status,r.score,r.summary,r.created_at,substr(r.content,1,110) AS preview FROM reviews r WHERE r.workspace_id=? ORDER BY r.created_at DESC LIMIT 5", (workspace_id,)).fetchall()
    return {"total_reviews": totals["total"], "average_score": round(totals["avg_score"] or 0), "pending_reviews": pending,
            "approved_reviews": approved, "open_findings": open_findings, "by_severity": {r["severity"]: r["count"] for r in by_severity},
            "recent_reviews": [dict(r) for r in recent]}


@app.post("/api/reviews")
def create_review(request: ReviewRequest, current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    if not request.content.strip():
        raise HTTPException(status_code=422, detail="Content cannot be empty")
    workspace_id = current_user["workspace_id"]
    rules, facts = get_rules(workspace_id), get_facts(workspace_id)
    findings = run_full_analysis(request.content.strip(), request.channel, rules, facts)
    review_id = str(uuid.uuid4())
    score = score_for(findings)
    summary = summary_for(findings)
    timestamp = now_iso()
    with connect() as conn:
        conn.execute("INSERT INTO reviews (id,content,channel,status,score,summary,created_at,updated_at,workspace_id) VALUES (?,?,?,?,?,?,?,?,?)",
                     (review_id, request.content.strip(), request.channel, "pending", score, summary, timestamp, timestamp, workspace_id))
        persist_findings(conn, review_id, findings)
    return serialize_review(review_id, workspace_id)


@app.get("/api/reviews")
def list_reviews(limit: int = 50, current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    limit = max(1, min(limit, 100))
    with connect() as conn:
        reviews = conn.execute("""SELECT r.*, (SELECT COUNT(*) FROM findings f WHERE f.review_id=r.id AND f.status='open') AS finding_count
                                  FROM reviews r WHERE r.workspace_id=? ORDER BY r.created_at DESC LIMIT ?""", (current_user["workspace_id"], limit)).fetchall()
    return {"items": [dict(r) for r in reviews], "count": len(reviews)}


@app.get("/api/reviews/{review_id}")
def get_review(review_id: str, current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    return serialize_review(review_id, current_user["workspace_id"])


@app.post("/api/reviews/{review_id}/revise")
def revise_review(review_id: str, request: RevisionRequest, current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    if current_user["role"] not in {"content_creator", "brand_reviewer", "brand_admin"}:
        raise HTTPException(status_code=403, detail="Your workspace role does not allow this action.")
    content = request.content.strip()
    if not content:
        raise HTTPException(status_code=422, detail="Content cannot be empty")
    workspace_id = current_user["workspace_id"]
    rules, facts = get_rules(workspace_id), get_facts(workspace_id)
    findings = run_full_analysis(content, "Revision", rules, facts)
    score = score_for(findings)
    summary = summary_for(findings)
    with connect() as conn:
        existing = conn.execute("SELECT id FROM reviews WHERE id=? AND workspace_id=?", (review_id, workspace_id)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Review not found")
        conn.execute("UPDATE reviews SET content=?,status='pending',score=?,summary=?,updated_at=? WHERE id=? AND workspace_id=?", (content, score, summary, now_iso(), review_id, workspace_id))
        conn.execute("DELETE FROM findings WHERE review_id=?", (review_id,))
        persist_findings(conn, review_id, findings)
        conn.execute("INSERT INTO decisions (id,review_id,decision,reviewer,comment,created_at) VALUES (?,?,?,?,?,?)",
                     (str(uuid.uuid4()), review_id, "revised", current_user["name"], "Content updated and automatically rechecked.", now_iso()))
    return serialize_review(review_id, workspace_id)


@app.post("/api/reviews/{review_id}/decision")
def make_decision(review_id: str, request: DecisionRequest, current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    require_role(current_user, "brand_reviewer", "brand_admin")
    allowed = {"approved", "rejected", "needs_revision"}
    if request.decision not in allowed:
        raise HTTPException(status_code=422, detail=f"Decision must be one of: {', '.join(sorted(allowed))}")
    workspace_id = current_user["workspace_id"]
    with connect() as conn:
        exists = conn.execute("SELECT id FROM reviews WHERE id=? AND workspace_id=?", (review_id, workspace_id)).fetchone()
        if not exists:
            raise HTTPException(status_code=404, detail="Review not found")
        conn.execute("UPDATE reviews SET status=?,updated_at=? WHERE id=? AND workspace_id=?", (request.decision, now_iso(), review_id, workspace_id))
        conn.execute("INSERT INTO decisions (id,review_id,decision,reviewer,comment,created_at) VALUES (?,?,?,?,?,?)",
                     (str(uuid.uuid4()), review_id, request.decision, current_user["name"], request.comment.strip(), now_iso()))
    return serialize_review(review_id, workspace_id)


@app.get("/api/reviews/{review_id}/export")
def export_review(review_id: str, current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    review = serialize_review(review_id, current_user["workspace_id"])
    return {"exported_at": now_iso(), "brand": "LumaLeaf", "review": review,
            "disclaimer": "BrandLens findings are advisory and do not replace legal, regulatory, or human review."}


# Initialize local DB when imported by a simple ASGI server or test runner.
init_db()

# In production, the React bundle is built before the API process starts. Serving the SPA
# from the same origin makes deployment a single-service operation. Local development uses Vite.
FRONTEND_DIST = ROOT.parent / "frontend" / "dist"
if (FRONTEND_DIST / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="frontend-assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_frontend(full_path: str) -> FileResponse:
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API route not found")
        candidate = (FRONTEND_DIST / full_path).resolve()
        # Serve explicitly requested public files only if they stay inside dist.
        if candidate.is_file() and FRONTEND_DIST.resolve() in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")
