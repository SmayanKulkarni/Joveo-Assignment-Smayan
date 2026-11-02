import type { ReactNode } from "react"
import type { Customer } from "../api/types"
import { go } from "../router"

export const initials = (name: string) =>
  name.split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0].toUpperCase()).join("")

// On every Customer and Run screen, so a CSM always sees whose Run they are in.
export function CustomerHeader({ customer, children }: { customer: Customer; children?: ReactNode }) {
  return (
    <header className="customer-head">
      <span className="avatar" aria-hidden>{initials(customer.name)}</span>
      <div className="who">
        <a href={`/customers/${customer.id}`} onClick={go}>
          <strong>{customer.name}</strong>
        </a>
        {customer.note && <span className="muted">{customer.note}</span>}
      </div>
      {children}
    </header>
  )
}
