# 08: Customers

**What to build:** A CSM can add, find, rename and open their own Customers in the sidebar, and can't see anyone else's. Deleting comes in ticket 09, because it must reach Runs. [Customers and what a CSM can do with them](../../resume-accounts-sources/final-decisions.md#customers-and-what-a-csm-can-do-with-them) is the spec.

**Blocked by:** 07: Sign in with Google

**Status:** done

- [x] A `customers` table holds `id`, `csm_id`, `name` (required, up to 100 characters), `note` (optional, up to 200) and timestamps
- [x] `GET` and `POST /api/customers`, and `GET` and `PATCH /api/customers/{id}`, work with 422 on a blank or overlong field
- [x] Another CSM's Customer gets 404
- [x] Names may repeat, and the list shows the note
- [x] The sidebar has a search box, "Add Customer" and the Customer list; a Customer page has its name and note in the header
- [x] In local mode the same tables serve one fixed local CSM, with a Customer named "Local"
- [x] Tests cover two CSMs, refusals, and local mode
