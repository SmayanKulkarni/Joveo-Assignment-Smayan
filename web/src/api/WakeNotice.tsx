import { useWake } from "./useMeta"

export function WakeNotice() {
  const state = useWake()
  if (state === "ok") return null
  return (
    <p className="wake-notice no-print" role="status">
      {state === "waking" ? "Waking the server, this can take a minute." : "The server didn't answer. Please reload the page in a minute."}
    </p>
  )
}
