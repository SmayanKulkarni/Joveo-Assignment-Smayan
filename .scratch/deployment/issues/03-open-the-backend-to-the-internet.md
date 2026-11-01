# Open the backend to the internet

Type: grilling
Status: open
Assignee:
Blocked by: [Research: running the backend on a Hugging Face Docker Space](01-research-hf-docker-spaces.md), [Research: serving the SPA from Vercel and reaching the backend](02-research-vercel-spa-and-cross-origin-sse.md)

## Question

`clients/web.py` assumes loopback: `TrustedHostMiddleware` allows only localhost, `same_origin` refuses another origin, and `scout serve` binds 127.0.0.1. There is no auth, and every Run spends the user's OpenRouter and Adzuna quota. What changes so a public host is safe from strangers spending that money, with the least code, and without weakening the local guards?
