import type { Customer } from "../api/types"
import { go } from "../router"

// On every Customer and Run screen, so a CSM always sees whose Run they are in.
export function CustomerHeader({ customer }: { customer: Customer }) {
  return (
    <header className="customer-head">
      <a href={`/customers/${customer.id}`} onClick={go}>
        <strong>{customer.name}</strong>
      </a>
      {customer.note && <span className="muted">{customer.note}</span>}
    </header>
  )
}
