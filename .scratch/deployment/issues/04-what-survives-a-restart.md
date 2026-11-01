# What survives a restart

Type: grilling
Status: open
Assignee:
Blocked by: [Research: running the backend on a Hugging Face Docker Space](01-research-hf-docker-spaces.md)

## Question

`gateway_db`, `runs_db` and `runs_dir` are local files. Given what a Space keeps across sleep and restart, what should hold Run history and the Gateway's quota counter and cache? In particular, does losing `adzuna_daily_limit`'s counter risk the real Adzuna quota?
