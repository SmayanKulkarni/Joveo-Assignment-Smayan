import { useSyncExternalStore } from "react"

// The same breakpoint as the stylesheet's, so the panel and the strip never both show.
const query = matchMedia("(max-width: 899px)")
const subscribe = (notify: () => void) => {
  query.addEventListener("change", notify)
  return () => query.removeEventListener("change", notify)
}

export const useNarrow = () => useSyncExternalStore(subscribe, () => query.matches)
