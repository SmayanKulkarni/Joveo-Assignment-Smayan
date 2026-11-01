# Research: running the backend on a Hugging Face Docker Space

Fetched from huggingface.co on 2026-11-01. Answers ticket `01-research-hf-docker-spaces.md`.

- **Documented**: stated in Hugging Face's own docs or pricing pages, linked on each claim.
- **Needs a live check**: the docs are silent, or too old to rely on. Checks are listed at the end.
- **Inference**: my own reasoning from documented facts, labelled where used.

## Headline findings

1. **A "free Docker Space" no longer exists for a free account.** CPU Basic has no hourly cost, but Docker Spaces need a paid plan. Without one, creating, duplicating or moving a Docker Space on `cpu-basic` fails with HTTP 402. PRO is listed at $9/month. **Documented.** ([overview](https://huggingface.co/docs/hub/spaces-overview), [manage Spaces](https://huggingface.co/docs/huggingface_hub/guides/manage-spaces), [pricing](https://huggingface.co/pricing))
2. **The old paid persistent storage tiers are gone.** The replacement is Storage Buckets mounted as volumes. **Documented.** ([config reference](https://huggingface.co/docs/hub/spaces-config-reference), [disk usage](https://huggingface.co/docs/hub/spaces-storage))
3. **Nothing documents how the Spaces proxy treats SSE.** This must be tested on a real Space before relying on it. **Needs a live check.**

## 1. README metadata, port, user, writable paths

| Item | Answer | Status |
|---|---|---|
| Required metadata | YAML block at the top of `README.md` with `sdk: docker`. `title`, `emoji`, `colorFrom`, `colorTo` appear in the example. | Documented ([Docker Spaces](https://huggingface.co/docs/hub/spaces-sdks-docker), [config reference](https://huggingface.co/docs/hub/spaces-config-reference)) |
| Port | `app_port`, default `7860`. One port is exposed; internal ports are unrestricted, and an Nginx-style reverse proxy is the suggested way to expose several. | Documented ([Docker Spaces](https://huggingface.co/docs/hub/spaces-sdks-docker)) |
| Bind address | The FastAPI tutorial runs `uvicorn main:app --host 0.0.0.0 --port 7860`. | Documented ([first demo](https://huggingface.co/docs/hub/spaces-sdks-docker-first-demo)) |
| Container user | Runs as UID 1000. Create that user and use `COPY --chown=user`. | Documented ([Docker Spaces](https://huggingface.co/docs/hub/spaces-sdks-docker)) |
| Writable paths | No list is published. The docs say to make paths writable yourself in the Dockerfile, for example `mkdir -p /data` and `chmod 777 /data`. A `/data` volume is available only at runtime, not during the build. | Documented guidance; exact defaults need a live check |
| Startup limit | `startup_duration_timeout`, default 30 minutes. | Documented ([config reference](https://huggingface.co/docs/hub/spaces-config-reference)) |
| Outbound network | Only ports 80, 443 and 8080. Other ports are blocked. | Documented ([overview](https://huggingface.co/docs/hub/spaces-overview#networking)) |

## 2. Hardware, sleep, disk, persistent storage

- **Free hardware:** CPU Basic has 2 vCPU, 16 GB RAM and 50 GB of non-persistent disk. **Documented.** ([GPU Spaces](https://huggingface.co/docs/hub/spaces-gpus))
- **Sleep:** on `cpu-basic`, a Space sleeps after more than 48 hours of inactivity, and the time cannot be changed. **Documented.** ([GPU Spaces](https://huggingface.co/docs/hub/spaces-gpus#sleep-time), [manage Spaces](https://huggingface.co/docs/huggingface_hub/guides/manage-spaces))
- **Wake:** anyone visiting the Space restarts it automatically. **Documented.** ([GPU Spaces](https://huggingface.co/docs/hub/spaces-gpus#sleep-time))
- **Manual pause:** a paused Space stays down until someone with write access restarts it, so a visit does not wake it. **Documented.** ([overview](https://huggingface.co/docs/hub/spaces-overview#lifecycle-management))
- **Disk:** ephemeral, and its contents are lost when the Space restarts or stops. **Documented.** ([disk usage](https://huggingface.co/docs/hub/spaces-storage), [Docker Spaces](https://huggingface.co/docs/hub/spaces-sdks-docker))
- **What triggers a restart:** every new commit causes a rebuild and restart, and any secret or hardware change restarts the app. Each of these wipes the disk. **Documented.** ([overview](https://huggingface.co/docs/hub/spaces-overview), [manage Spaces](https://huggingface.co/docs/huggingface_hub/guides/manage-spaces))
- **Persistent storage:** "no longer available", and the `suggested_storage` setting is ignored. **Documented.** ([config reference](https://huggingface.co/docs/hub/spaces-config-reference))
- **Replacement:** attach a Storage Bucket at a chosen path, read-write by default. **Documented.** ([disk usage](https://huggingface.co/docs/hub/spaces-storage), [manage Spaces](https://huggingface.co/docs/huggingface_hub/guides/manage-spaces#mount-volumes-in-your-space))
- **Bucket price:** billed per TB, with no per-tier Space fee. Base rates are $12/TB/month public and $18/TB/month private, with egress included up to an 8:1 ratio. **Documented.** ([storage pricing](https://huggingface.co/storage))
- **Free bucket allowance:** buckets have a free allowance under the account's storage limits: 100 GB private on a free account, 1 TB private on PRO. **Documented.** ([buckets](https://huggingface.co/docs/hub/storage-buckets#pricing), [storage limits](https://huggingface.co/docs/hub/storage-limits))
- **Other options:** a Dataset repo or an external database or S3. **Documented.** ([Docker Spaces](https://huggingface.co/docs/hub/spaces-sdks-docker))

Needs a live check:

- What counts as "activity" for the 48-hour timer, and whether API or SSE traffic alone resets it.
- What the first request to a sleeping Space returns. The docs only mention a "visitor", so a `fetch` or `EventSource` from another origin may behave differently from a page load.
- Whether a mounted bucket supports SQLite. The docs describe buckets as object storage and say nothing about locking or random writes. ([buckets](https://huggingface.co/docs/hub/storage-buckets), [access patterns](https://huggingface.co/docs/hub/storage-buckets-access))

## 3. SSE and idle connections through the proxy

**No Hugging Face page found describes buffering, idle timeouts or significant response headers for app traffic on `*.hf.space`. Needs a live check.**

Related evidence, none of which settles it:

- `custom_headers` in the README allows only COEP, COOP and CORP. It cannot set streaming headers, so those must come from the app. **Documented.** ([config reference](https://huggingface.co/docs/hub/spaces-config-reference))
- Hugging Face's own Hub API streams over SSE, but on `huggingface.co`, not through the Spaces proxy. Its bucket stream pings every 30 seconds and recycles connections about every 20 minutes. This shows their practice elsewhere, not a Spaces limit. ([GPU Spaces](https://huggingface.co/docs/hub/spaces-gpus#streaming), [buckets](https://huggingface.co/docs/hub/storage-buckets#live-follow))
- The Sandboxes proxy supports SSE, but that is a different product built on Jobs. ([sandboxes](https://huggingface.co/docs/huggingface_hub/guides/sandbox))
- Old forum threads (around 2021 to 2023) report cut-offs at about 60 seconds. These are not primary sources, may be out of date, and concern Gradio. ([thread](https://discuss.huggingface.co/t/is-there-a-timeout-max-runtime-for-spaces/12979))

Inference, not Hugging Face guidance: send `Content-Type: text/event-stream`, `Cache-Control: no-cache` and `X-Accel-Buffering: no`, emit a comment heartbeat, and support `Last-Event-ID` resume, because a restart or proxy cut will drop streams.

## 4. Visibility and what is exposed

| | Public | Protected | Private |
|---|---|---|---|
| Source on the Hub | Everyone | Owner and collaborators | Owner and collaborators |
| App at the `hf.space` URL | Yes | Yes | No |
| Custom domain | Yes | Yes | No |
| Clonable by others | Yes | No | No |

**Documented.** ([overview](https://huggingface.co/docs/hub/spaces-overview#space-visibility))

- **A private Space cannot serve a public browser app.** Other users get a 404. **Documented.**
- **The Space need not be public.** Protected visibility hides the source and leaves the app reachable, and needs PRO or Team and Enterprise. **Documented.** ([changelog](https://huggingface.co/docs/hub/spaces-changelog))
- **Token access to a private Space is not a workaround.** A private Space takes an HF token ([Spaces as agent tools](https://huggingface.co/docs/hub/en/spaces-agents)), but shipping one to browsers would leak it, and `EventSource` cannot set an `Authorization` header. **Inference.**
- **Files in a public Space:** every committed file is readable and clonable. **Documented.**
- **Variables:** publicly viewable, and copied to duplicates. **Documented.** ([secrets](https://huggingface.co/docs/hub/spaces-overview#managing-secrets))
- **Secrets:** cannot be read back from settings and are not copied to duplicates. Exposure through app output is the app's own responsibility. **Documented**, except that last sentence, which is inference.
- **Hard-coded secrets:** TruffleHog scans each push and emails on verified secrets. **Documented.** ([secrets scanning](https://huggingface.co/docs/hub/security-secrets))
- **Logs:** the 2021 changelog says raw build and container logs are viewable by users with write access, and today's log API requires authentication. Neither says who can see logs on a public Space today, so never print secrets. **Needs a live check.** ([changelog](https://huggingface.co/docs/hub/spaces-changelog), [GPU Spaces](https://huggingface.co/docs/hub/spaces-gpus#streaming))

## 5. Secrets, CLI and deploy

**Setting secrets. Documented.** ([CLI guide](https://huggingface.co/docs/huggingface_hub/guides/cli), [manage Spaces](https://huggingface.co/docs/huggingface_hub/guides/manage-spaces))

```bash
hf spaces secrets add username/my-space -s KEY=value
hf spaces secrets add username/my-space --secrets-file .env.secrets
hf spaces variables add username/my-space -e NAME=value
```

- The Settings page and `HfApi.add_space_secret` also work. Values are write-only.
- At runtime, secrets arrive as environment variables. At build time, they need `RUN --mount=type=secret,id=NAME,...`. ([Docker Spaces](https://huggingface.co/docs/hub/spaces-sdks-docker))

**Deploying chosen files. Documented.** ([CLI guide](https://huggingface.co/docs/huggingface_hub/guides/cli), [upload guide](https://huggingface.co/docs/huggingface_hub/guides/upload))

```bash
hf upload username/my-space . . --repo-type=space --include="..." --exclude="..." --delete="*" --commit-message="..."
```

- `--delete` removes remote files missing locally. The docs show it combined with `--exclude`, as a sync.
- A root `.gitignore` is honoured.
- Large folders split into several commits automatically.
- Every commit triggers a rebuild, so a split upload could trigger more than one. That last step is inference.

**File size. Documented, with a gap.**

- `hf upload` "handles large files automatically", using Xet.
- Over `git`, files above **10 MB** "should" be tracked with `git-xet`. ([getting started](https://huggingface.co/docs/hub/repositories-getting-started))
- The docs say "should", and give no rejection rule or error. The exact refusal behaviour over plain `git` needs a live check, and is irrelevant if deploying with `hf upload`.
- The hard limit for a single file is 500 GB, with under 200 GB recommended. ([limits](https://huggingface.co/docs/hub/storage-limits))

## 6. URL, CORS, Host

- **URL form:** `https://<space-subdomain>.hf.space`. For example, `NimaBoscarino/hotdog-gradio` becomes `https://nimaboscarino-hotdog-gradio.hf.space`. It is served from the root and changes only if the Space is moved or renamed. **Documented.** ([embed](https://huggingface.co/docs/hub/spaces-embed))
- **Exact host at runtime:** the `SPACE_HOST` environment variable holds it. Read this rather than rebuilding the name, since the docs give no rule for edge cases such as dots or underscores. **Documented**, except the advice. ([overview](https://huggingface.co/docs/hub/spaces-overview#built-in-environment-variables))
- **Custom domain:** PRO or above, public or protected only, via a CNAME to `hf.space`. **Documented.** ([custom domain](https://huggingface.co/docs/hub/spaces-custom-domain))
- **Cookies:** the Space page on `huggingface.co` embeds the app from `*.hf.space` in an iframe, so browsers restrict its cookies. Cookie-based XSRF protection is a known failure there. **Documented.** ([cookies](https://huggingface.co/docs/hub/spaces-cookie-limitations))
- **Proxy headers:** no page lists headers added by the proxy (`X-Forwarded-*`, `Host`) or says whether it adds or strips CORS headers. **Needs a live check.**
- **CORS:** `custom_headers` cannot set it, so a frontend on another origin needs CORS from the app, such as FastAPI's `CORSMiddleware`. **Inference.**

## Live checks to run on a real Space

1. Confirm the account can create a Docker Space on `cpu-basic`, or whether it gets a 402.
2. Stream SSE with `curl -N` for at least 10 minutes, with timestamps: once with heartbeats and once idle. This shows buffering and idle cut-off.
3. Repeat with and without `X-Accel-Buffering: no`.
4. Echo request headers from an endpoint to see `Host` and `X-Forwarded-*`. Inspect the response headers for any CORS header the proxy adds.
5. Send a cross-origin preflight and a real `EventSource` from the frontend origin.
6. Call the API of a sleeping Space, and record what it returns and how long it takes to wake. Sleep takes 48 hours, unless a manual pause and restart gives a similar cold start.
7. From inside the container, test which paths UID 1000 can write.
8. If a bucket is mounted: test SQLite and restart survival.
9. From a logged-out browser, check whether logs are visible on a public or protected Space.
