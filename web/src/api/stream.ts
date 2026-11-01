import type { WireEvent } from "./types"

const TERMINAL = new Set(["paused", "done", "stopped"])

type Handlers = {
  onEvent: (event: WireEvent) => void
  onOpen: () => void // a replay follows, so the caller starts again from its base
  onClosed: () => void // the server said there is nothing live (204 or 404)
}

export function openStream(id: string, { onEvent, onOpen, onClosed }: Handlers): () => void {
  const source = new EventSource(`/api/runs/${id}/events`)
  source.onopen = onOpen
  source.onmessage = (message) => {
    const event: WireEvent = JSON.parse(message.data)
    onEvent(event)
    // A stream that ended normally would otherwise reconnect and replay for ever.
    if (TERMINAL.has(event.type)) source.close()
  }
  source.onerror = () => {
    if (source.readyState === EventSource.CLOSED) onClosed()
  }
  return () => source.close()
}
