from datetime import datetime

from fastapi import APIRouter, Depends, Request, Response

from talent_scout.analysis.resume import FactsPatch, ResumeFacts, UnknownType, Unreadable, parse_resume, patched
from talent_scout.clients.customers import own_customer
from talent_scout.clients.refusal import Refusal
from talent_scout.kernel.llm import LLMExhausted
from talent_scout.kernel.types import Model
from talent_scout.runtime.accounts import Accounts, Customer

MAX_RESUME_BYTES = 2 * 1024 * 1024

router = APIRouter(prefix="/customers/{customer_id}/resume")


class ResumeOut(Model):
    facts: ResumeFacts
    uploaded_at: datetime
    replaced: bool = False  # true when this upload overwrote one, and with it any CSM edits


def _accounts(request: Request) -> Accounts:
    return request.app.state.controller.accounts


async def _read_capped(request: Request) -> bytes:
    # Content-Length can lie or be absent, so the stream is counted too.
    if int(request.headers.get("content-length") or 0) > MAX_RESUME_BYTES:
        raise Refusal(413, "too_big", "This file is over 2 MB. Upload a smaller one or paste the text")
    body = bytearray()
    async for chunk in request.stream():
        body += chunk
        if len(body) > MAX_RESUME_BYTES:
            raise Refusal(413, "too_big", "This file is over 2 MB. Upload a smaller one or paste the text")
    return bytes(body)


async def _stored(request: Request, customer: Customer):
    stored = await _accounts(request).resume(customer.id)
    if stored is None:
        raise Refusal(404, "no_resume", "This Customer has no Resume yet")
    return stored


@router.put("")
async def upload(request: Request, customer: Customer = Depends(own_customer)) -> ResumeOut:
    body = await _read_capped(request)
    chain = request.app.state.resume_chain
    if chain is None:
        raise Refusal(503, "no_model", "Reading a Resume needs a model, and this install has none")
    try:
        text, facts = await parse_resume(chain, body)
    except UnknownType:
        raise Refusal(415, "unknown_type", "Upload a PDF or a Word document, or paste the text") from None
    except Unreadable as err:
        raise Refusal(422, "unreadable", str(err)) from None
    except LLMExhausted:
        raise Refusal(502, "parse_failed", "The Resume could not be read just now. Try again, or paste the text") from None
    accounts = _accounts(request)
    replaced = await accounts.resume(customer.id) is not None
    await accounts.save_resume(customer.id, text, facts)
    return ResumeOut(facts=facts, uploaded_at=(await accounts.resume(customer.id)).uploaded_at, replaced=replaced)


@router.get("")
async def read(request: Request, customer: Customer = Depends(own_customer)) -> ResumeOut:
    stored = await _stored(request, customer)
    return ResumeOut(facts=stored.facts, uploaded_at=stored.uploaded_at)


@router.patch("")
async def correct(body: FactsPatch, request: Request, customer: Customer = Depends(own_customer)) -> ResumeOut:
    stored = await _stored(request, customer)
    facts = patched(stored.facts, body, stored.text)
    await _accounts(request).save_resume(customer.id, stored.text, facts, keep_date=True)
    return ResumeOut(facts=facts, uploaded_at=stored.uploaded_at)


@router.delete("", status_code=204)
async def remove(request: Request, customer: Customer = Depends(own_customer)) -> Response:
    if not await _accounts(request).delete_resume(customer.id):
        raise Refusal(404, "no_resume", "This Customer has no Resume yet")
    return Response(status_code=204)
