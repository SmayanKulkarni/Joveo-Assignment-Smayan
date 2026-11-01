import { API } from "./client"
import type { WireEvent } from "./types"

const TERMINAL = new Set(["paused", "done", "stopped"])
const GRACE_MS = 2000

export const isTerminal = (event: WireEvent) => TERMINAL.has(event.type)

type Handlers = {
  onEvent: (event: WireEvent) => void
  onOpen: () => void // a replay follows, so the caller starts again from its base
  onReconnecting: () => void // the browser has been retrying for longer than a blip
  onClosed: () => void // the server said there is nothing live (204 or 404)
}

export function openStream(id: string, { onEvent, onOpen, onReconnecting, onClosed }: Handlers): () => void {
  const source = new EventSource(`${API}/runs/${id}/events`)
  let grace: number | undefined
  source.onopen = () => {
    clearTimeout(grace)
    onOpen()
  }
  source.onmessage = (message) => {
    const event: WireEvent = JSON.parse(message.data)
    onEvent(event)
    // A stream that ended normally would otherwise reconnect and replay for ever.
    if (isTerminal(event)) source.close()
  }
  source.onerror = () => {
    if (source.readyState === EventSource.CLOSED) return onClosed()
    // readyState 0: the browser retries by itself, so only an outage past the grace is worth showing.
    clearTimeout(grace)
    grace = window.setTimeout(() => source.readyState === EventSource.CONNECTING && onReconnecting(), GRACE_MS)
  }
  return () => {
    clearTimeout(grace)
    source.close()
  }
}
