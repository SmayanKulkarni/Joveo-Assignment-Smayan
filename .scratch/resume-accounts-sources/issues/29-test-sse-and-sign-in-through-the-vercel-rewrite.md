# Test SSE and sign-in through the Vercel rewrite

Type: task
Status: open
Assignee: none
Blocked by: [Accounts and sign-in](14-accounts-and-sign-in.md)

## Question

Does the planned `/api` rewrite hold up on a real preview deployment? The LLD records the result, and [Accounts and sign-in](14-accounts-and-sign-in.md) names the `Partitioned` cookie fallback if it doesn't.

- Add the rewrite before the SPA catch-all, with `x-vercel-enable-rewrite-caching: 0` on `/api/:path*`.
- Does an SSE stream arrive event by event, or buffered? Time events against a real Run or a small test stream.
- Which `Host` header reaches Render, and does `TrustedHostMiddleware` accept it? Does `Origin` pass through for the `write_guard` check?
- Do `Set-Cookie` and `__Host-` cookies pass through unchanged, including through a redirect response?
- What does the proxy return while Render shows its spin-up page, and does the SPA cope?

Google sign-in isn't needed for this: a throwaway route that sets a cookie is enough. The agent drives what it can, and the user does what needs their Vercel and Render access. Record the facts in the Answer.
