import { API } from "../api/client"

export type Document = "brief" | "recommendation"

export const TABS: { key: Document; label: string }[] = [
  { key: "brief", label: "Market Brief" },
  { key: "recommendation", label: "Customer Recommendation" },
]

// The server serves each deliverable as JSON and Markdown under its own name.
export const downloadUrl = (id: string, doc: Document, kind: "json" | "md") => `${API}/runs/${id}/${doc}.${kind}`
