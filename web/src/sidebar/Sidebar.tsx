import { useState } from "react"
import type { FormEvent } from "react"
import { addCustomer, logOut } from "../api/client"
import type { Customer, Me } from "../api/types"
import { go, navigate } from "../router"
import { refreshCustomers } from "./useCustomers"

function AddCustomer({ onDone }: { onDone: () => void }) {
  const [name, setName] = useState("")
  const [note, setNote] = useState("")
  const [error, setError] = useState<string | null>(null)

  async function submit(event: FormEvent) {
    event.preventDefault()
    try {
      const customer = await addCustomer(name, note)
      refreshCustomers()
      onDone()
      navigate(`/customers/${customer.id}`)
    } catch (e) {
      setError(name.trim() ? "That didn't save. The note can be up to 200 characters." : "Give the Customer a name.")
    }
  }

  return (
    <form className="add-customer" onSubmit={submit}>
      <input value={name} onChange={(e) => setName(e.target.value)} maxLength={100} placeholder="Name" aria-label="Customer name" autoFocus />
      <input value={note} onChange={(e) => setNote(e.target.value)} maxLength={200} placeholder="Note, to tell two apart" aria-label="Customer note" />
      {error && <p className="error">{error}</p>}
      <button type="submit" className="start">Add</button>
    </form>
  )
}

type Props = { customers: Customer[] | null; activeId: string | null; open: boolean; me: Me; signIn: boolean }

export function Sidebar({ customers, activeId, open, me, signIn }: Props) {
  const [query, setQuery] = useState("")
  const [adding, setAdding] = useState(false)
  const shown = (customers ?? []).filter((c) => `${c.name} ${c.note ?? ""}`.toLowerCase().includes(query.trim().toLowerCase()))

  return (
    <nav className={open ? "sidebar open" : "sidebar"} aria-label="Customers">
      <a href="/" onClick={go} className="brand">Talent Scout</a>
      <input type="search" className="find" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Find a Customer" aria-label="Find a Customer" />
      {adding ? <AddCustomer onDone={() => setAdding(false)} /> : <button type="button" className="new-run" onClick={() => setAdding(true)}>+ Add Customer</button>}
      <ul>
        {shown.map((c) => (
          <li key={c.id}>
            <a href={`/customers/${c.id}`} onClick={go} aria-current={c.id === activeId ? "page" : undefined} className="row">
              <span className="title">{c.name}</span>
              {c.note && <span className="meta">{c.note}</span>}
            </a>
          </li>
        ))}
      </ul>
      {customers && customers.length > 0 && shown.length === 0 && <p className="muted">No Customer matches.</p>}
      {signIn && (
        <footer className="account">
          <span title={me.email}>{me.email}</span>
          <button type="button" onClick={() => logOut().finally(() => location.assign("/"))}>Log out</button>
        </footer>
      )}
    </nav>
  )
}
