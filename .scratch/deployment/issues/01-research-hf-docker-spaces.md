# Research: running the backend on a Hugging Face Docker Space

Type: research
Status: open
Assignee:
Blocked by: none

## Question

What do Hugging Face's own docs say about hosting a long-lived FastAPI process with SSE on a free Docker Space?

- Required `README.md` metadata, port, container user, and which paths are writable.
- Free hardware (CPU, RAM, disk), when a Space sleeps, how it wakes, and what happens to the disk on sleep and restart. Is persistent storage still paid, and at what price?
- Does the Spaces proxy buffer or time out SSE or idle connections? Which response headers matter?
- Can a private Space serve a public browser app, or must the Space be public? What is exposed in a public Space (files, build logs, secrets)?
- How are secrets set, and can a CLI set them? How does `hf upload` deploy a chosen set of files, and how large a file is refused without LFS?
- The exact public URL form, and any headers the proxy adds that affect CORS or Host checks.
