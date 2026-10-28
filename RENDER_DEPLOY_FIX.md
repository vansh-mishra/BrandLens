# Render deployment fix

The earlier Blueprint used a Python native runtime while its build command also ran `npm` to compile React. If Render's Python build environment does not include Node/npm, that command fails before the web service starts. This version uses a Docker multi-stage build so Node builds the React assets and Python runs FastAPI in the same deployed service.

## Apply this fix to the existing GitHub repository

1. Replace `render.yaml` at the repository root with the version in this package.
2. Add `Dockerfile` at the repository root.
3. Ensure `backend/` and `frontend/` are also at the repository root, not nested inside another `brandlens-mvp/` folder.
4. Commit and push to the same `main` branch linked to the Render Blueprint.
5. In Render, open the existing Blueprint and sync the latest changes if prompted. Check the pending changes before applying them; the existing `brandlens-db` should be reused, not duplicated.
6. Open the `brandlens-demo` service and check Deploys. Once it says Live, open `/api/health` and confirm `status` is `ok` and `storage` is `PostgreSQL`.

If deployment still fails, open the failed deploy and copy the first error from its logs. The screenshot that shows a red failed status does not contain the underlying error, so a definitive diagnosis requires the deploy logs.

Do not commit `.env`, API keys, database passwords, or JWT secrets.
