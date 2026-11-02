# 15: Ship to Render and Vercel

**What to build:** The hosted app runs on Neon with Google sign-in, so an allowed CSM can use it from the public URL and their data survives a redeploy. The Deployment part of [What was still fog on the map](../../resume-accounts-sources/final-decisions.md#what-was-still-fog-on-the-map) is the spec. Later tickets ship on top of this as they land.

**Blocked by:** 01: Arbeitnow Postings in a Run; 09: Runs belong to a Customer

**Status:** needs-human

- [ ] The user creates a Neon project in Oregon and a Google OAuth client with the production redirect URL, from a precise checklist
- [x] `render.yaml` declares `database_url`, `google_client_id`, `google_client_secret` and `allowed_emails`; `seed_dir` is unset on Render and the access code is gone
- [ ] Vercel's rewrite is in place, or the fallback ticket 05 named
- [ ] Verified live: sign in, add a Customer, finish a Run with live events, redeploy, and the Run is still there
- [ ] Verified live: a Google account not on `allowed_emails` is refused
- [ ] The Arbeitnow walk's memory stays within 512 MB on Render
- [ ] The Deployment docs match what shipped

Progress: `render.yaml` already declares the four variables and the access code is gone from the code and the LLD; the Dockerfile no longer copies the seed Runs or sets `SEED_DIR`. The Neon project, Google OAuth client, Vercel check and live verification are still the user's.
