from fastapi import APIRouter, Depends, Request, Response

from talent_scout.clients.auth import current_csm
from talent_scout.clients.refusal import Refusal
from talent_scout.kernel.types import Model
from talent_scout.runtime.accounts import Accounts, Csm, Customer, CustomerName, CustomerNote
from talent_scout.runtime.controller import RunController, RunLive

router = APIRouter(prefix="/customers")


class NewCustomer(Model):
    name: CustomerName
    note: CustomerNote | None = None


class CustomerPatch(Model):
    name: CustomerName | None = None
    note: CustomerNote | None = None


def _accounts(request: Request) -> Accounts:
    return request.app.state.controller.accounts


async def own_customer(customer_id: str, request: Request, csm: Csm = Depends(current_csm)) -> Customer:
    customer = await _accounts(request).customer(csm, customer_id)
    if customer is None:
        raise Refusal(404, "not_found", "No such Customer")
    return customer


@router.get("")
async def list_customers(request: Request, csm: Csm = Depends(current_csm)) -> list[Customer]:
    return await _accounts(request).customers(csm)


@router.post("", status_code=201)
async def add_customer(body: NewCustomer, request: Request, csm: Csm = Depends(current_csm)) -> Customer:
    return await _accounts(request).add_customer(csm, body.name, body.note)


@router.get("/{customer_id}")
async def get_customer(customer: Customer = Depends(own_customer)) -> Customer:
    return customer


@router.patch("/{customer_id}")
async def patch_customer(body: CustomerPatch, request: Request, customer: Customer = Depends(own_customer)) -> Customer:
    fields = body.model_dump(exclude_unset=True)
    if fields.get("name") is None:
        fields.pop("name", None)  # a name can't be cleared; only a note can
    return await _accounts(request).update_customer(customer, fields)


@router.delete("/{customer_id}", status_code=204)
async def delete_customer(request: Request, customer: Customer = Depends(own_customer)) -> Response:
    controller: RunController = request.app.state.controller
    runs = await controller.list_runs(customer_id=customer.id)
    if any(controller.attached(run.thread_id) or run.status == "running" for run in runs):
        raise RunLive(customer.id)
    # Runs first, then the Customer: each step can be repeated, so an interrupted delete is finished by trying again.
    for run in runs:
        await controller.delete_run(run.thread_id)
    await _accounts(request).delete_customer(customer.id)
    return Response(status_code=204)
