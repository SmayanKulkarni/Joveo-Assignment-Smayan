from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request, Response
from pydantic import ValidationError

from talent_scout.clients.customers import own_customer
from talent_scout.clients.refusal import Refusal
from talent_scout.kernel.types import Model
from talent_scout.runtime.accounts import Accounts, Customer, StoredProfile
from talent_scout.runtime.profile import PIN_TYPES, Field, ProfileOut, shown

router = APIRouter(prefix="/customers/{customer_id}/profile")


class ProfilePatch(Model):
    set: dict[Field, str | list[str]] = {}
    remove: list[Field] = []


def _accounts(request: Request) -> Accounts:
    return request.app.state.controller.accounts


def _out(profile: StoredProfile) -> ProfileOut:
    values, titles = shown(profile.learned, profile.pinned, profile.removed)
    return ProfileOut(values=values, titles=titles, earlier=profile.learned.earlier, cleared_at=profile.cleared_at)


@router.get("")
async def read(request: Request, customer: Customer = Depends(own_customer)) -> ProfileOut:
    return _out(await _accounts(request).profile(customer.id))


@router.patch("")
async def edit(body: ProfilePatch, request: Request, customer: Customer = Depends(own_customer)) -> ProfileOut:
    accounts = _accounts(request)
    profile = await accounts.profile(customer.id)
    pinned = dict(profile.pinned)
    try:
        for field, value in body.set.items():
            pinned[field] = PIN_TYPES[field].validate_python(value)
    except (KeyError, ValidationError):
        raise Refusal(422, "invalid_profile", "That value can't be set on the Profile") from None
    removed = [f for f in dict.fromkeys([*profile.removed, *body.remove]) if f not in body.set]
    pinned = {k: v for k, v in pinned.items() if k not in body.remove or k in body.set}
    profile = profile.model_copy(update={"pinned": pinned, "removed": removed})
    await accounts.save_profile(customer.id, profile)
    return _out(profile)


@router.delete("", status_code=204)
async def clear(request: Request, customer: Customer = Depends(own_customer)) -> Response:
    accounts = _accounts(request)
    # Runs before this moment stop counting, so a recompute can't bring them back.
    await accounts.save_profile(customer.id, StoredProfile(cleared_at=datetime.now(UTC)))
    return Response(status_code=204)
