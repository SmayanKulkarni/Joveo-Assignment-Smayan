import { useState } from "react"
import type { FormEvent } from "react"
import { LogOut, Plus, Search } from "lucide-react"
import { addCustomer, logOut } from "../api/client"
import type { Customer, Me } from "../api/types"
import { go, navigate } from "../router"
import { initials } from "../customers/CustomerHeader"
import { ThemeToggle } from "../ThemeToggle"
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
      <div className="actions">
        <button type="submit" className="primary">Add Customer</button>
        <button type="button" className="ghost" onClick={onDone}>Cancel</button>
      </div>
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
      <div className="brand-row">
        <a href="/" onClick={go} className="brand"><span className="logo" aria-hidden>TS</span>Talent Scout</a>
        <ThemeToggle />
      </div>
      {adding ? (
        <AddCustomer onDone={() => setAdding(false)} />
      ) : (
        <button type="button" className="primary new-run" onClick={() => setAdding(true)}>
          <Plus size={16} aria-hidden /> Add Customer
        </button>
      )}
      <label className="find">
        <Search size={16} aria-hidden />
        <input type="search" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Find a Customer" aria-label="Find a Customer" />
      </label>
      <h2>Customers{customers && <span className="count-muted">{customers.length}</span>}</h2>
      <ul>
        {shown.map((c) => (
          <li key={c.id}>
            <a href={`/customers/${c.id}`} onClick={go} aria-current={c.id === activeId ? "page" : undefined} className="row customer-row">
              <span className="avatar sm" aria-hidden>{initials(c.name)}</span>
              <span className="who">
                <span className="title">{c.name}</span>
                {c.note && <span className="meta">{c.note}</span>}
              </span>
            </a>
          </li>
        ))}
      </ul>
      {customers && customers.length > 0 && shown.length === 0 && <p className="muted">No Customer matches.</p>}
      {signIn && (
        <footer className="account">
          <span title={me.email}>{me.email}</span>
          <button type="button" className="ghost" onClick={() => logOut().finally(() => location.assign("/"))}>
            <LogOut size={16} aria-hidden /> Log out
          </button>
        </footer>
      )}
    </nav>
  )
}
