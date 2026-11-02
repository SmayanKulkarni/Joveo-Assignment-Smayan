import { useEffect, useState } from "react"
import type { DragEvent } from "react"
import { ApiError, correctResume, deleteResume, getResume, uploadResume } from "../api/client"
import type { ResumeInfo, ResumeSeniority } from "../api/types"
import { ChipList } from "./ChipList"
import { LIMITS, changes, draftOf } from "./resumeForm"
import type { Draft } from "./resumeForm"

const LEVELS: ResumeSeniority[] = ["entry", "mid", "senior", "lead", "executive", "unknown"]

// The server's message already says what to do, so it is shown as it came. A 422 on a correction also lists the fields.
const refusal = (e: unknown) => (e instanceof ApiError ? [e.message, ...e.errors.map((x) => x.msg)].join(" ") : "Something went wrong. Try again.")

function DropZone({ busy, error, onSend }: { busy: boolean; error: string | null; onSend: (body: Blob | string) => void }) {
  const [text, setText] = useState("")
  const drop = (event: DragEvent) => {
    event.preventDefault()
    const file = event.dataTransfer.files[0]
    if (file && !busy) onSend(file)
  }

  return (
    <div className="dropzone" onDragOver={(e) => e.preventDefault()} onDrop={drop}>
      {busy ? (
        <p>Reading the resume</p>
      ) : (
        <>
          <p>Drop a PDF or Word file here, or</p>
          <input type="file" accept=".pdf,.docx" aria-label="Resume file" onChange={(e) => e.target.files?.[0] && onSend(e.target.files[0])} />
          <p>or paste the text</p>
          <textarea value={text} onChange={(e) => setText(e.target.value)} aria-label="Resume text" rows={6} />
          <button type="button" className="start" disabled={!text.trim()} onClick={() => onSend(text)}>
            Read pasted text
          </button>
        </>
      )}
      {error && <p className="error">{error}</p>}
    </div>
  )
}

type FactsProps = {
  customerId: string
  info: ResumeInfo
  onChange: (info: ResumeInfo) => void
  onReplace: () => void
  onDelete: () => void
}

function Facts({ customerId, info, onChange, onReplace, onDelete }: FactsProps) {
  const [draft, setDraft] = useState<Draft>(draftOf(info.facts))
  const [error, setError] = useState<string | null>(null)
  const patch = changes(info.facts, draft)
  const added = new Set(info.facts.skills.filter((s) => s.added).map((s) => s.name))
  const setRole = (i: number, field: "title" | "start" | "end", value: string) =>
    setDraft({ ...draft, roles: draft.roles.map((r, j) => (j === i ? { ...r, [field]: value } : r)) })

  async function save() {
    setError(null)
    try {
      const saved = await correctResume(customerId, patch)
      onChange(saved)
      setDraft(draftOf(saved.facts))
    } catch (e) {
      setError(refusal(e))
    }
  }

  return (
    <section className="resume">
      <p className="muted">Resume uploaded on {new Date(info.uploaded_at).toLocaleDateString()}</p>
      <h3>Roles</h3>
      {draft.roles.map((role, i) => (
        <div key={i} className="inline">
          <input value={role.title} maxLength={LIMITS.title} aria-label="Role title" onChange={(e) => setRole(i, "title", e.target.value)} />
          <input value={role.start} maxLength={LIMITS.date} aria-label="Role start" onChange={(e) => setRole(i, "start", e.target.value)} />
          <input value={role.end} maxLength={LIMITS.date} aria-label="Role end" onChange={(e) => setRole(i, "end", e.target.value)} />
          <button type="button" onClick={() => setDraft({ ...draft, roles: draft.roles.filter((_, j) => j !== i) })}>
            Remove
          </button>
        </div>
      ))}
      <button
        type="button"
        disabled={draft.roles.length >= LIMITS.roles}
        onClick={() => setDraft({ ...draft, roles: [...draft.roles, { title: "", start: "", end: "" }] })}
      >
        Add role
      </button>
      <h3>Skills</h3>
      <ChipList label="skill" items={draft.skills} max={LIMITS.skills} maxChars={LIMITS.skill} added={added} onChange={(skills) => setDraft({ ...draft, skills })} />
      <h3>Seniority</h3>
      <select value={draft.seniority} aria-label="Seniority" onChange={(e) => setDraft({ ...draft, seniority: e.target.value as ResumeSeniority })}>
        {LEVELS.map((level) => (
          <option key={level}>{level}</option>
        ))}
      </select>
      <h3>Locations</h3>
      <ChipList label="location" items={draft.locations} max={LIMITS.locations} maxChars={LIMITS.location} onChange={(locations) => setDraft({ ...draft, locations })} />
      <h3>Years of experience</h3>
      <p>
        {info.facts.years ?? <span className="muted">not worked out</span>} <span className="muted">(counted from the role dates)</span>
      </p>
      {error && <p className="error">{error}</p>}
      <div className="actions no-print">
        <button type="button" className="start" disabled={Object.keys(patch).length === 0} onClick={save}>
          Save changes
        </button>
        <button type="button" onClick={onReplace}>
          Replace Resume
        </button>
        <button type="button" className="danger" onClick={onDelete}>
          Delete Resume
        </button>
      </div>
    </section>
  )
}

export function ResumePanel({ customerId }: { customerId: string }) {
  const [info, setInfo] = useState<ResumeInfo | null>(null)
  const [loaded, setLoaded] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    // A Customer with no Resume answers 404, which just means the drop zone shows.
    getResume(customerId)
      .then(setInfo, (e) => {
        if (!(e instanceof ApiError && e.code === "no_resume")) setError(refusal(e))
      })
      .finally(() => setLoaded(true))
  }, [customerId])

  async function send(body: Blob | string) {
    if (busy) return
    setBusy(true)
    setError(null)
    try {
      setInfo(await uploadResume(customerId, body))
    } catch (e) {
      setError(refusal(e))
    }
    setBusy(false)
  }

  async function remove() {
    if (!confirm("Delete this Resume? Runs will no longer use it.")) return
    try {
      await deleteResume(customerId)
      setInfo(null)
    } catch (e) {
      setError(refusal(e))
    }
  }

  if (!loaded) return <p>Loading…</p>
  if (!info) return <DropZone busy={busy} error={error} onSend={send} />
  return (
    <>
      {error && <p className="error">{error}</p>}
      <Facts
        // Keyed on the upload, so a fresh Resume starts from its own facts.
        key={info.uploaded_at}
        customerId={customerId}
        info={info}
        onChange={setInfo}
        onReplace={() => confirm("Replacing the Resume discards the CSM's edits to it. Continue?") && setInfo(null)}
        onDelete={remove}
      />
    </>
  )
}
