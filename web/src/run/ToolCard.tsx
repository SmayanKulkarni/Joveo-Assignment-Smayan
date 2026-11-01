import type { Tool } from "./reducer"

const SOURCES: Record<string, string> = { adzuna: "Adzuna", usajobs: "USAJOBS" }
const sourceName = (name: string) => SOURCES[name.replace(/^search_/, "")] ?? name

export function ToolCard({ tool }: { tool: Tool }) {
  const state = tool.result !== null ? "done" : tool.interrupted ? "interrupted" : "running"
  return (
    <div className={`tool ${state}`}>
      <span className="mark" aria-hidden>{state === "done" ? "✓" : state === "interrupted" ? "–" : ""}</span>
      <b>{sourceName(tool.name)}</b>
      <span>{tool.result ?? (state === "interrupted" ? "Interrupted" : tool.summary)}</span>
      {tool.pill && <span className="pill">{tool.pill}</span>}
    </div>
  )
}
