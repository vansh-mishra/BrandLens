# BrandLens hackathon submission checklist

## Before you connect the project to a public repo

- [ ] Extract the ZIP and open `brandlens-mvp` in Codex.
- [ ] Run the backend with the README commands and confirm `GET /api/health` returns `status: ok`.
- [ ] Install frontend dependencies with `npm install` and confirm `npm run build` finishes successfully.
- [ ] Run `pytest -q` and keep the real output; the supplied backend tests have passed in the build environment.
- [ ] Test both supplied samples and inspect the actual rule/source passages.
- [ ] Run the full flow: review → apply correction → recheck → reviewer decision → reopen from history.
- [ ] If enabling the optional model, use an API key stored only as a local environment variable or deployment secret. Never commit it.
- [ ] Test the deployed service in a fresh incognito window and on mobile. Test the health endpoint and the review flow, not only the landing page.
- [ ] Create an admin account, invite a second account, assign it the Brand reviewer role, and verify a creator receives HTTP 403 when trying to approve content.
- [ ] Configure `DATABASE_URL` with a managed PostgreSQL connection string for hosted persistent data; verify a review remains after restarting/redeploying the web service.
- [ ] Set a strong `JWT_SECRET` in the deployment environment; never commit the database URL, JWT secret, or OpenAI API key.
- [ ] Verify that a second workspace cannot read the first workspace's reviews or uploaded guidelines.

## Evidence that helps judges assess quality

- [ ] Include 20–50 clearly labelled examples: compliant copy, known violations, borderline wording, and unsupported claims.
- [ ] Report observed precision/recall by issue type and document how labels were made. Do not invent accuracy numbers.
- [ ] Show a false-positive dismissal/edit path and explain how the team will improve the rules.
- [ ] Show the exact source excerpt behind a finding and confirm the cited source ID exists.
- [ ] Keep the live URL, source repository, README, test instructions, and a short demo video easy to find.
- [ ] Explain what Codex was used for honestly. Keep relevant session or commit evidence if the event asks for it.
- [ ] Use only permitted APIs, tools, datasets, and libraries; disclose external services according to the official event rules.

## Final 3-minute story

**Problem** → show a risky sentence → reveal a source-linked finding → apply a correction → re-run review → reviewer approval/revision → show audit record → explain what is tested and what is still a prototype.

A public URL that loads is not sufficient: the judge should be able to complete the core workflow without assistance.
