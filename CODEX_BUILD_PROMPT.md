# Codex prompt to harden BrandLens for a hackathon demo

Use the existing repository as the source of truth. First inspect the code and run the tests. Do not replace the working stack or redesign the product before understanding the current flow.

## Objective

Make BrandLens a polished, reliable end-to-end demo of evidence-backed pre-publication brand review. The central path must work without setup surprises:

1. Let visitors enter the same core demo workflow without registration; keep sign-in/sign-up available for persistent workspaces. Demo sessions must be isolated from other visitors. Registered teammates join using a private invite code.
2. Run a content check on the supplied problematic sample.
3. Inspect findings with exact text, severity, confidence, and a valid source title/section/excerpt.
4. Apply one suggestion and automatically recheck the revised version.
5. Sign in as a workspace reviewer/admin, approve or request revisions, then load the same item from history and inspect the audit trail.

## Constraints

- Keep the no-API-key flow fully functional.
- Never invent a source, factual claim, confidence score, or benchmark.
- If the optional LLM is used, accept only findings whose source ID exists in the supplied source catalog and whose quote appears exactly in the reviewed content. Treat provider failures as non-fatal.
- Do not call an upload flow “rule ingestion” unless the extracted rules are shown for human review and explicit approval before activation.
- Keep role permissions enforced by the backend. Never let a frontend role selector confer reviewer/admin privileges.
- Keep the UI accessible, responsive, light, and calm. No neon colors, fake activity, or decorative metrics.
- Do not commit `.env`, API keys, user content, or database files.

## Work plan

1. Run backend tests and frontend production build; report failures before changing code.
2. Add tests for authentication, workspace isolation, role authorization, claim detection, evidence/source validation, revisions, decisions, and history persistence.
3. Fix UI states for loading, empty results, network errors, no findings, and failed uploads.
4. Improve keyboard accessibility and mobile layout without removing evidence text.
5. Ensure suggested corrections are easy to edit and never silently approve content.
6. Add a seeded evaluation set with at least 20 positive and negative examples, human labels, and a repeatable precision/recall report. Do not state accuracy until the tests actually run and output is observed.
7. Add deployment instructions and a health-check endpoint. Clearly document any production limitations.
8. Run all tests and a production build again; provide a concise change summary with exact commands and remaining issues.

## Definition of done

- A clean install can run locally using the README commands.
- The deterministic sample returns stable findings with valid source citations.
- An approved-fact example does not get flagged by the built-in high-level claim rules.
- Revising content persists and updates findings rather than silently mutating approval state.
- The audit table shows the decision after reloading the review.
- A creator cannot make a final decision, admins can assign team roles, and separate workspaces cannot read each other's reviews.
- Hosted deployments use a managed `DATABASE_URL` and a generated `JWT_SECRET` rather than relying on free-host SQLite files.
- No secret or generated database is committed.
- There is a public, accessible demo URL and an understandable README before submission.
