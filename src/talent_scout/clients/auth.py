from secrets import compare_digest, token_urlsafe
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Request, Response
from fastapi.responses import RedirectResponse

from talent_scout.clients.refusal import Refusal
from talent_scout.kernel.settings import Settings
from talent_scout.runtime.accounts import SESSION_DAYS, Accounts, Csm

GOOGLE_AUTH = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO = "https://openidconnect.googleapis.com/v1/userinfo"
STATE_SECONDS = 600


def _cookie(settings: Settings, name: str) -> tuple[str, dict]:
    # The __Host- prefix needs Secure, so it only applies where the site is served over https.
    secure = (settings.web_origin or "").startswith("https://")
    return (f"__Host-{name}" if secure else name), {"httponly": True, "secure": secure, "samesite": "lax", "path": "/"}


def _redirect_uri(request: Request) -> str:
    origin = request.app.state.settings.web_origin or str(request.base_url).rstrip("/")
    return f"{origin}/api/auth/google/callback"


async def current_csm(request: Request) -> Csm:
    settings: Settings = request.app.state.settings
    accounts: Accounts = request.app.state.controller.accounts
    if not settings.sign_in:
        return await accounts.local_csm()
    token = request.cookies.get(_cookie(settings, "session")[0])
    csm = await accounts.csm_of(token) if token else None
    if csm and csm.email.lower() not in settings.allowed_emails:
        # Taken off the list mid-session: their data stays, so adding them back restores everything.
        await accounts.end_sessions_of(csm.id)
        csm = None
    if csm is None:
        raise Refusal(401, "signed_out", "Sign in to continue")
    return csm


router = APIRouter(prefix="/auth")


@router.get("/google")
async def start_sign_in(request: Request):
    settings: Settings = request.app.state.settings
    state = token_urlsafe(16)
    query = urlencode({
        "client_id": settings.google_client_id, "redirect_uri": _redirect_uri(request), "response_type": "code",
        "scope": "openid email", "state": state,
    })
    response = RedirectResponse(f"{GOOGLE_AUTH}?{query}")
    name, flags = _cookie(settings, "state")
    response.set_cookie(name, state, max_age=STATE_SECONDS, **flags)
    return response


async def _identity(request: Request, code: str) -> dict:
    settings: Settings = request.app.state.settings
    # The transport is swapped for a fake in tests.
    async with httpx.AsyncClient(transport=request.app.state.google_transport, timeout=10) as http:
        tokens = await http.post(GOOGLE_TOKEN, data={
            "code": code, "client_id": settings.google_client_id, "client_secret": settings.google_client_secret,
            "redirect_uri": _redirect_uri(request), "grant_type": "authorization_code",
        })
        tokens.raise_for_status()
        info = await http.get(GOOGLE_USERINFO, headers={"Authorization": f"Bearer {tokens.json()['access_token']}"})
        info.raise_for_status()
        return info.json()


@router.get("/google/callback")
async def finish_sign_in(request: Request, code: str | None = None, state: str | None = None, error: str | None = None):
    settings: Settings = request.app.state.settings
    accounts: Accounts = request.app.state.controller.accounts
    state_name, state_flags = _cookie(settings, "state")

    def back(failure: str | None = None) -> RedirectResponse:
        response = RedirectResponse(f"/?signin={failure}" if failure else "/")
        response.delete_cookie(state_name, **state_flags)
        return response

    expected = request.cookies.get(state_name)
    if not (expected and state and compare_digest(expected.encode(), state.encode())):
        return back("bad_state")
    if error or not code:
        return back("google_failed")
    try:
        info = await _identity(request, code)
        email, sub = str(info["email"]).lower(), str(info["sub"])
    except (httpx.HTTPError, KeyError, ValueError):
        return back("google_failed")
    if info.get("email_verified") is not True:
        return back("unverified_email")
    if email not in settings.allowed_emails:
        return back("not_allowed")
    csm = await accounts.upsert_csm(sub, email)
    response = back()
    name, flags = _cookie(settings, "session")
    response.set_cookie(name, await accounts.new_session(csm.id), max_age=SESSION_DAYS * 86400, **flags)
    return response


@router.post("/logout", status_code=204)
async def log_out(request: Request) -> Response:
    settings: Settings = request.app.state.settings
    name, flags = _cookie(settings, "session")
    if token := request.cookies.get(name):
        await request.app.state.controller.accounts.end_session(token)
    response = Response(status_code=204)
    response.delete_cookie(name, **flags)
    return response
