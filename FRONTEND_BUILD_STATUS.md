# Frontend production build status

The landing page now includes **Explore demo without signing up**. The existing core demo workspace remains available through the same React interface; sign-in/sign-up remain available for registered team workspaces.

A TypeScript JSX parser pass successfully parsed `frontend/src/App.jsx`, but full Vite dependency installation/build remains unverified in this environment because `npm install` previously failed while accessing the npm registry. A syntax check is not a production bundle.

Run locally from `frontend/`:

```bash
npm install
npm run build:verify
```

A successful check prints `Frontend production build verified.` The GitHub Actions workflow also runs the build on a network-enabled runner after code is pushed.
