import { useCallback, useEffect, useState } from "react"
import { listCustomers } from "../api/client"
import type { Customer } from "../api/types"

const REFRESH = "customers:refresh"

// Adding, renaming or deleting a Customer calls this, so the sidebar doesn't wait for a reload.
export const refreshCustomers = () => dispatchEvent(new Event(REFRESH))

// null until the first answer, so a page can tell "loading" from "none yet".
export function useCustomers(): Customer[] | null {
  const [customers, setCustomers] = useState<Customer[] | null>(null)
  const load = useCallback(() => {
    listCustomers().then(setCustomers, () => {})
  }, [])
  useEffect(() => {
    load()
    addEventListener(REFRESH, load)
    return () => removeEventListener(REFRESH, load)
  }, [load])
  return customers
}
