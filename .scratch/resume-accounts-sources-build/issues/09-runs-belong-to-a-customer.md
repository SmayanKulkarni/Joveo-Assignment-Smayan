# 09: Runs belong to a Customer

**What to build:** Every Run is started from inside a Customer and is visible only to that Customer's CSM. A CSM can delete a stopped or finished Run, and can delete a Customer along with everything stored about them. [Runs that belong to a Customer](../../resume-accounts-sources/final-decisions.md#runs-that-belong-to-a-customer) and the Deleting part of [Customers](../../resume-accounts-sources/final-decisions.md#customers-and-what-a-csm-can-do-with-them) are the spec.

**Blocked by:** 08: Customers

**Status:** done

- [x] `runs` gains `customer_id`; no owner goes in the thread config or State
- [x] `POST /api/runs` requires `customer_id`: missing gives 422, and another CSM's gives 404
- [x] An `owned_run` dependency guards get, resume, cancel, delete, events and brief download with 404 `not_found`, checked before `attached`
- [x] The Controller stays unaware of accounts, and `list_runs` can filter by CSM and Customer
- [x] `DELETE /api/runs/{id}` removes a stopped or finished Run, and gives 409 if it's live
- [x] `DELETE /api/customers/{id}` needs a confirmation in the UI and gives 409 `run_live` while a Run is live
- [x] Deleting removes checkpoints and Brief files first, then the rows in one transaction, so an interrupted delete can be repeated
- [x] Local Runs with no Customer move to "Local", and `scripts/export_seed.py` is regenerated for the new column
- [x] The CLI files Runs under "Local" unless `--customer NAME` is given
- [x] The UI lists Runs under their Customer, and the current Customer stays in the header of every Customer, Run and New Run screen
- [x] Tests cover every endpoint as another CSM, two tabs on one Run, and a repeated interrupted delete

**Built with:** one deviation. Deleting a Customer removes checkpoints and files, then each Run row, then the Customer row, as separate steps rather than one transaction. Each step is repeatable, so an interrupted delete is finished by trying again. `export_seed.py` now clears `customer_id`, and `seed_runs` names its columns, so the existing seed still loads.
