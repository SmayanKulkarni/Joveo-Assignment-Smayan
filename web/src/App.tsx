import { useEffect, useState } from "react"
import { SIGNED_OUT, getMe } from "./api/client"
import type { Me } from "./api/types"
import { useMeta } from "./api/useMeta"
import { WakeNotice } from "./api/WakeNotice"
import { SignIn } from "./auth/SignIn"
import { CustomerPage } from "./customers/CustomerPage"
import { customerIdOf, go, runIdOf, usePath } from "./router"
import { RunPage } from "./run/RunPage"
import { Sidebar } from "./sidebar/Sidebar"
import { needsYou } from "./sidebar/group"
import { useCustomers } from "./sidebar/useCustomers"
import { useRuns } from "./sidebar/useRuns"

// Decides signed in or out before anything else loads, so a signed-out visitor never sees a failed request.
export function App() {
  const meta = useMeta()
  // undefined while asking, null when signed out
  const [me, setMe] = useState<Me | null | undefined>(undefined)

  useEffect(() => {
    if (!meta) return
    getMe().then(setMe, () => setMe(null))
    const out = () => setMe(null)
    addEventListener(SIGNED_OUT, out)
    return () => removeEventListener(SIGNED_OUT, out)
  }, [meta])

  if (me === undefined) return <WakeNotice />
  return me ? <Signed me={me} signIn={meta!.sign_in} /> : <SignIn />
}

function Signed({ me, signIn }: { me: Me; signIn: boolean }) {
  const path = usePath()
  const runId = runIdOf(path)
  const runs = useRuns()
  const customers = useCustomers()
  const [open, setOpen] = useState(false) // the slide-over, under about 900 px
  const waiting = runs.filter(needsYou).length

  // The Run's Customer comes from its row in the list, so a Run page shows it before its own details arrive.
  const listed = runs.find((run) => run.thread_id === runId)
  const customerId = customerIdOf(path) ?? listed?.customer_id ?? null
  const customer = customers?.find((c) => c.id === customerId)

  // Opening a Customer, or a Run, takes you out of the slide-over.
  useEffect(() => setOpen(false), [path])

  return (
    <div className="shell">
      <header className="topbar">
        <button onClick={() => setOpen(true)} aria-label={`Customers, ${waiting} Runs need you`}>
          Customers{waiting > 0 && <span className="count">{waiting}</span>}
        </button>
        <a href="/" onClick={go}>Talent Scout</a>
      </header>
      <Sidebar customers={customers} activeId={customerId} open={open} me={me} signIn={signIn} />
      {open && <div className="scrim" onClick={() => setOpen(false)} />}
      <main>
        <WakeNotice />
        {runId ? (
          <RunPage id={runId} key={runId} listed={listed} customer={customer} />
        ) : customerIdOf(path) ? (
          customer ? <CustomerPage customer={customer} runs={runs.filter((run) => run.customer_id === customer.id)} key={customer.id} /> : customers && <p>Customer not found. <a href="/" onClick={go}>Back</a></p>
        ) : (
          <div className="column"><h1>Choose a Customer</h1><p className="muted">Pick one in the list, or add a new one, then start a Run from their page.</p></div>
        )}
      </main>
    </div>
  )
}
