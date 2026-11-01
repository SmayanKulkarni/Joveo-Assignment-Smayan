# Research: running the backend on a Hugging Face Docker Space

Type: research
Status: resolved
Assignee: smayankulkarni05
Blocked by: none

## Question

What do Hugging Face's own docs say about hosting a long-lived FastAPI process with SSE on a free Docker Space?

- Required `README.md` metadata, port, container user, and which paths are writable.
- Free hardware (CPU, RAM, disk), when a Space sleeps, how it wakes, and what happens to the disk on sleep and restart. Is persistent storage still paid, and at what price?
- Does the Spaces proxy buffer or time out SSE or idle connections? Which response headers matter?
- Can a private Space serve a public browser app, or must the Space be public? What is exposed in a public Space (files, build logs, secrets)?
- How are secrets set, and can a CLI set them? How does `hf upload` deploy a chosen set of files, and how large a file is refused without LFS?
- The exact public URL form, and any headers the proxy adds that affect CORS or Host checks.

## Answer

Full findings, with sources: [research-hf-docker-spaces.md](assets/research-hf-docker-spaces.md). The paid-plan claim was re-read in the docs by the main session.

- **A Docker Space needs a paid plan.** `cpu-basic` has no hourly cost, but creating a Docker Space on it needs PRO ($9/month), or it fails with HTTP 402. Paid hardware needs only prepaid credits (`cpu-upgrade` is $0.03/hour).
- **Runtime.** `sdk: docker`, port 7860, UID 1000; 2 vCPU, 16 GB RAM, 50 GB disk; sleeps after 48 hours idle and a visitor wakes it.
- **Disk is lost on restart.** The old persistent storage is gone. Storage Buckets replace it, and SQLite on a bucket mount is unproven.
- **Visibility.** Private returns 404 to the public. Protected (PRO) hides the source and keeps the app reachable.
- **Deploying.** `hf spaces secrets add` and `hf upload --include` both work from a CLI. The URL is `https://<owner>-<space>.hf.space`, and `SPACE_HOST` holds that host.
- **Needs a live check.** SSE through the proxy (nothing is documented) and the Host header the app sees.
