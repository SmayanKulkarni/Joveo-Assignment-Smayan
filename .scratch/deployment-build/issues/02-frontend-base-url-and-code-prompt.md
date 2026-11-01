# Frontend base URL and access code prompt

Status: done
Blocked by: [Public backend settings](01-public-backend-settings.md)
Spec: [Point the frontend at the backend](../../deployment/issues/05-point-the-frontend-at-the-backend.md)

Use `VITE_API_URL` in `client.ts`, `stream.ts` and `BriefView.tsx`. Handle `access_denied` in `call()` with `window.prompt`, a stored code and one retry. When `/api/meta` fails, show the one-line waking message and retry every 5 seconds for 2 minutes. Add `web/vercel.json`.

Done when `npm --prefix web test` and `npm --prefix web run build` pass, with one Vitest case for the 401 prompt and retry, and a local `scout serve --demo` still works with no variable set.
