import { useState } from "react"
import type { FormEvent } from "react"
import { ApiError, deleteCustomer, editCustomer } from "../api/client"
import type { Customer, RunRecord } from "../api/types"
import { Composer } from "../composer/Composer"
import { navigate } from "../router"
import { RunList } from "../sidebar/RunList"
import { refreshCustomers } from "../sidebar/useCustomers"
import { CustomerHeader } from "./CustomerHeader"
import { ProfilePanel } from "./ProfilePanel"

const TABS = [["runs", "Runs"], ["profile", "Profile"]] as const

function Edit({ customer, onDone }: { customer: Customer; onDone: () => void }) {
  const [name, setName] = useState(customer.name)
  const [note, setNote] = useState(customer.note ?? "")
  const [error, setError] = useState<string | null>(null)

  async function save(event: FormEvent) {
    event.preventDefault()
    try {
      await editCustomer(customer.id, { name, note })
      refreshCustomers()
      onDone()
    } catch {
      setError("That didn't save. A name is needed, and the note can be up to 200 characters.")
    }
  }

  return (
    <form className="add-customer" onSubmit={save}>
      <input value={name} onChange={(e) => setName(e.target.value)} maxLength={100} aria-label="Customer name" />
      <input value={note} onChange={(e) => setNote(e.target.value)} maxLength={200} aria-label="Customer note" placeholder="Note" />
      {error && <p className="error">{error}</p>}
      <button type="submit" className="start">Save</button> <button type="button" onClick={onDone}>Cancel</button>
    </form>
  )
}

export function CustomerPage({ customer, runs }: { customer: Customer; runs: RunRecord[] }) {
  const [editing, setEditing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [tab, setTab] = useState<(typeof TABS)[number][0]>("runs")

  async function remove() {
    if (!confirm(`Delete ${customer.name} and all of their Runs? This can't be undone.`)) return
    try {
      await deleteCustomer(customer.id)
      refreshCustomers()
      navigate("/")
    } catch (e) {
      setError(e instanceof ApiError && e.code === "run_live" ? "A Run is still going. Stop it first." : "That didn't delete. Try again.")
    }
  }

  return (
    <div className="column">
      <CustomerHeader customer={customer} />
      <div className="customer-tools no-print">
        {editing ? <Edit customer={customer} onDone={() => setEditing(false)} /> : <button type="button" onClick={() => setEditing(true)}>Rename</button>}
        <button type="button" className="danger" onClick={remove}>Delete Customer</button>
      </div>
      {error && <p className="error">{error}</p>}
      <div role="tablist" className="tabs no-print">
        {TABS.map(([key, label]) => (
          <button key={key} type="button" role="tab" aria-selected={tab === key} onClick={() => setTab(key)}>
            {label}
          </button>
        ))}
      </div>
      {tab === "profile" ? (
        <ProfilePanel customerId={customer.id} />
      ) : (
        <>
          <Composer customerId={customer.id} />
          <h2>Runs</h2>
          <RunList runs={runs} activeId={null} />
        </>
      )}
    </div>
  )
}
