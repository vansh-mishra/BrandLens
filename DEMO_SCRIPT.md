# Suggested 2:30–2:50 judge demo

## 0:00–0:20 — Problem

“Marketing content is created by teams, agencies, and AI tools. One unsupported claim can create brand, trust, or compliance risk. BrandLens checks content against the organisation’s approved source of truth before publication. It does not replace the reviewer.”

## 0:20–0:55 — Run the check

On the landing page, click **Explore demo without signing up**. Open Review Studio, select **Problematic copy**, and run the review. Point at the flags for the absolute environmental claim, clinical/medical claim, prohibited terminology, and guaranteed results. Do not just read the badges: open the evidence block and show the exact policy passage.

## 0:55–1:25 — Fix and recheck

Apply one suitable suggestion. Show that the content changes, the review runs again, and the finding list/score is recalculated. Explain that a model suggestion is never silently applied or treated as proof.

## 1:25–1:55 — Human decision and audit

In the no-signup demo, choose “Request revision” or “Approve content” to demonstrate the review action. To show real team permissions, use a pre-created teammate account assigned the **Brand reviewer** role. Open Review history and reload the same review. Show that the decision is persisted. The backend rejects final decisions from content-creator accounts.

## 1:55–2:20 — Trust and scope

Open Brand Library. Explain that each rule has a source and that uploaded guideline text is stored for inspection rather than automatically turned into a live policy. Show the approved facts used in the demo.

## 2:20–2:45 — Technical implementation and next step

Explain the React interface, FastAPI API, PBKDF2 password hashing, signed bearer tokens, workspace-scoped permissions, SQLite for local use or managed PostgreSQL when `DATABASE_URL` is set, deterministic checks, and optional source-constrained OpenAI pass. State the current limitations accurately: email verification/password recovery/MFA are not implemented; accuracy should be measured on a labelled set; image and visual asset checks are next.

## Recording checklist

- Record the actual running product, not a mock-up.
- For a simple walkthrough, use the no-signup demo. If showing registered team permissions, prepare one admin and one reviewer account in the same workspace before recording; do not show personal credentials or the invite code publicly.
- Show at least one visible correction and one reviewer decision.
- Do not claim a measured accuracy rate or time saving unless it has been tested.
- Keep the recording below the exact time limit in your event rules.
