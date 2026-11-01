# Public backend settings

Status: done
Blocked by: none
Spec: [Open the backend to the internet](../../deployment/issues/03-open-the-backend-to-the-internet.md)

Add `access_code` and `web_origin` to `Settings`. In `clients/web.py`, add the `X-Access-Code` check to the POST routes' dependency, accept `web_origin` in `same_origin`, add `CORSMiddleware` when `web_origin` is set, and trust `RENDER_EXTERNAL_HOSTNAME` when it is set. Add `--host` to `scout serve`.

Done when `tests/test_web_api.py` covers: a POST with a wrong or missing code is 401 and with the right code is 201; GETs need no code; the configured origin passes and another gets 403; a preflight from the configured origin succeeds; and with neither setting, today's tests pass unchanged.
