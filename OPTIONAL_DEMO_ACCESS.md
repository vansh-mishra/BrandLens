# Optional sign-in: guest demo mode

The landing page now offers **Explore demo without signing up** above the sign-in/create-account form. Authentication remains available for users who need a registered, persistent team workspace.

## Guest demo behavior

- Opens the existing BrandLens workspace interface, including Overview, Review Studio, Brand Library, Review History, and Insights.
- Uses the same LumaLeaf sample rules and approved facts as the signed-in demo.
- Supports running a review, inspecting source-linked findings, applying a correction, uploading guideline text, adding custom rules, viewing history, and recording demo reviewer decisions.
- Creates a private demo workspace per visitor, so one visitor's changes do not appear in another visitor's history.
- Hides team administration in guest mode. Team membership and role management remain available to registered workspace administrators.
- Issues a signed 12-hour demo token. Demo workspace data older than 24 hours is cleaned up when a later demo session is created.

## Implementation

- `POST /api/auth/demo` creates the guest workspace and returns a token and a user marked `is_demo: true`.
- The token's signed `demo` claim preserves demo mode across refreshes.
- Guest sessions use the `brand_reviewer` role, so the existing review/decision flow works while the team-admin route remains unavailable.
- Built-in seed rules and facts are shared read-only data; reviews, custom rules, and uploaded guideline text are workspace-scoped.

## Verification

- Backend tests: 10 passed, including anonymous demo entry, review/approval, and isolation across demo sessions.
- Python syntax compilation: passed.
- Frontend JSX syntax parse: passed.
- Vite production bundle: still requires `npm install` and `npm run build:verify` on a machine that can reach the npm registry.
