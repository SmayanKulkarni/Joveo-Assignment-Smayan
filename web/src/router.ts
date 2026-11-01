import type { MouseEvent } from "react"
import { useSyncExternalStore } from "react"

export function navigate(path: string) {
  history.pushState(null, "", path)
  dispatchEvent(new PopStateEvent("popstate"))
}

// For an <a href>: client navigation, while the href still works in a new tab.
export function go(event: MouseEvent<HTMLAnchorElement>) {
  event.preventDefault()
  navigate(event.currentTarget.getAttribute("href")!)
}

const subscribe = (notify: () => void) => {
  addEventListener("popstate", notify)
  return () => removeEventListener("popstate", notify)
}

export const usePath = () => useSyncExternalStore(subscribe, () => location.pathname)

export const runIdOf = (path: string) => path.match(/^\/runs\/([^/]+)$/)?.[1] ?? null
