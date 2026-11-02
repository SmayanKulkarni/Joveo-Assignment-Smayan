import { useEffect, useReducer, useRef, useState } from "react"
import type { DragEvent } from "react"
import { useGSAP } from "@gsap/react"
import { Check, FileUp, Plus, RefreshCw, Save, Trash2, Undo2, X } from "lucide-react"
import { ApiError, correctResume, deleteResume, getResume } from "../api/client"
import type { ResumeInfo, ResumeSeniority } from "../api/types"
import { ask } from "../confirm"
import { gsap } from "../motion"
import { ChipList } from "./ChipList"
import { LIMITS, changes, draftOf } from "./resumeForm"
import type { Draft } from "./resumeForm"
import { finishUpload, forgetReload, onUploadSettled, reloadWindowOver, reloadedUpload, startUpload, uploadOf } from "./uploads"

const LEVELS: ResumeSeniority[] = ["entry", "mid", "senior", "lead", "executive", "unknown"]

// The server's message already says what to do, so it is shown as it came. A 422 on a correction also lists the fields.
const refusal = (e: unknown) => (e instanceof ApiError ? [e.message, ...e.errors.map((x) => x.msg)].join(" ") : "Something went wrong. Try again.")

const day = (iso: string) => new Date(iso).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" })

// ponytail: the server answers once at the end, so the stages are paced on a typical read (about 20 s), not reported.
// Stream real stages from the PUT if the estimate ever misleads.
const EXPECTED_S = 22
const STAGES: [number, string][] = [
  [0, "Uploading the file"],
  [0.08, "Reading the text and removing contact details"],
  [0.25, "Pulling out roles, skills and locations"],
  [0.75, "Checking every fact against the Resume"],
]

function UploadProgress({ startedAt, finished, onShown }: { startedAt: number; finished: boolean; onShown: () => void }) {
  const fill = useRef<HTMLElement>(null)
  const percent = useRef<HTMLElement>(null)
  const tween = useRef<gsap.core.Tween>(null)
  const [stage, setStage] = useState(0)
  const shown = finished ? "Done. Showing what was found" : STAGES[stage][1]

  useGSAP(() => {
    const state = { v: 0 }
    const draw = () => {
      gsap.set(fill.current, { scaleX: state.v })
      if (percent.current) percent.current.textContent = `${Math.round(state.v * 100)}%`
      setStage(STAGES.filter(([at]) => state.v >= at).length - 1)
    }
    // Eases out and never reaches the end by itself, so a slow read slows down instead of sitting at 100%.
    tween.current = gsap.to(state, { v: 0.94, duration: EXPECTED_S, ease: "power3.out", onUpdate: draw })
    // Coming back to a running upload picks the bar up where the time says it is, not from zero.
    tween.current.seek(Math.min((Date.now() - startedAt) / 1000, EXPECTED_S))
    return () => tween.current?.kill()
  }, [])

  useGSAP(() => {
    if (!finished) return
    const state = { v: gsap.getProperty(fill.current, "scaleX") as number }
    tween.current?.kill()
    gsap.to(state, {
      v: 1, duration: 0.45, ease: "power2.inOut",
      onUpdate: () => {
        gsap.set(fill.current, { scaleX: state.v })
        if (percent.current) percent.current.textContent = `${Math.round(state.v * 100)}%`
      },
      onComplete: () => void gsap.delayedCall(0.35, onShown),
    })
  }, [finished])

  return (
    <div className="upload-progress" role="status" aria-live="polite">
      <div className="upload-progress-head">
        <span>{shown}</span>
        <b ref={percent}>0%</b>
      </div>
      <span className="bar big" aria-hidden>
        <i ref={fill} style={{ transform: "scaleX(0)" }} />
      </span>
      <ol className="stages">
        {STAGES.map(([, label], i) => (
          <li key={label} className={finished || i < stage ? "done" : i === stage ? "now" : ""}>
            {finished || i < stage ? <Check size={14} aria-hidden /> : <span className="dot-sm" aria-hidden />}
            {label}
          </li>
        ))}
      </ol>
    </div>
  )
}

type DropProps = { onSend: (body: Blob | string) => void; onCancel?: () => void; error: string | null }

function DropZone({ onSend, onCancel, error }: DropProps) {
  const [text, setText] = useState("")
  const [over, setOver] = useState(false)
  const drop = (event: DragEvent) => {
    event.preventDefault()
    setOver(false)
    const file = event.dataTransfer.files[0]
    if (file) onSend(file)
  }

  return (
    <section className="panel">
      {onCancel && <p className="muted">The current Resume stays until the new one has been read.</p>}
      <div
        className={over ? "dropzone over" : "dropzone"}
        onDragOver={(e) => {
          e.preventDefault()
          setOver(true)
        }}
        onDragLeave={() => setOver(false)}
        onDrop={drop}
      >
        <FileUp size={28} aria-hidden />
        <p><b>Drop a PDF or Word file here</b></p>
        <p className="muted">Up to 2 MB. Contact details are removed before anything is stored.</p>
        <label className="btn primary">
          Choose a file
          <input type="file" accept=".pdf,.docx" className="sr-only" onChange={(e) => e.target.files?.[0] && onSend(e.target.files[0])} />
        </label>
      </div>
      <div className="or"><span>or paste the text</span></div>
      <textarea className="field" value={text} onChange={(e) => setText(e.target.value)} aria-label="Resume text" rows={6} placeholder="Paste the Resume here" />
      {error && <p className="error" role="alert">{error}</p>}
      <div className="actions">
        <button type="button" className="primary" disabled={!text.trim()} onClick={() => onSend(text)}>
          Read pasted text
        </button>
        {onCancel && (
          <button type="button" onClick={onCancel}>
            <X size={16} aria-hidden /> Keep the current Resume
          </button>
        )}
      </div>
    </section>
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
  const [saving, setSaving] = useState(false)
  const patch = changes(info.facts, draft)
  const dirty = Object.keys(patch).length > 0
  const added = new Set(info.facts.skills.filter((s) => s.added).map((s) => s.name))
  const setRole = (i: number, field: "title" | "start" | "end", value: string) =>
    setDraft({ ...draft, roles: draft.roles.map((r, j) => (j === i ? { ...r, [field]: value } : r)) })

  async function save() {
    setError(null)
    setSaving(true)
    try {
      const saved = await correctResume(customerId, patch)
      onChange(saved)
      setDraft(draftOf(saved.facts))
    } catch (e) {
      setError(refusal(e))
    }
    setSaving(false)
  }

  return (
    <section className="resume">
      <div className="panel-head">
        <p className="muted">Uploaded {day(info.uploaded_at)}{info.replaced && " · replaced the earlier one"}</p>
        <div className="actions no-print">
          <button type="button" onClick={onReplace}>
            <RefreshCw size={16} aria-hidden /> Replace Resume
          </button>
          <button type="button" className="danger" onClick={onDelete}>
            <Trash2 size={16} aria-hidden /> Delete Resume
          </button>
        </div>
      </div>

      <div className="panel">
        <h3>Roles</h3>
        <div className="roles">
          <span className="roles-head" aria-hidden>Title</span>
          <span className="roles-head" aria-hidden>Start</span>
          <span className="roles-head" aria-hidden>End</span>
          <span />
          {draft.roles.map((role, i) => (
            <div key={i} className="role-row">
              <input className="field" value={role.title} maxLength={LIMITS.title} aria-label="Role title" onChange={(e) => setRole(i, "title", e.target.value)} />
              <input className="field" value={role.start} maxLength={LIMITS.date} aria-label="Role start" onChange={(e) => setRole(i, "start", e.target.value)} />
              <input className="field" value={role.end} maxLength={LIMITS.date} aria-label="Role end" onChange={(e) => setRole(i, "end", e.target.value)} />
              <button type="button" className="icon-btn" aria-label={`Remove ${role.title || "role"}`} onClick={() => setDraft({ ...draft, roles: draft.roles.filter((_, j) => j !== i) })}>
                <Trash2 size={16} aria-hidden />
              </button>
            </div>
          ))}
        </div>
        <button
          type="button"
          className="ghost"
          disabled={draft.roles.length >= LIMITS.roles}
          onClick={() => setDraft({ ...draft, roles: [...draft.roles, { title: "", start: "", end: "" }] })}
        >
          <Plus size={16} aria-hidden /> Add role
        </button>
      </div>

      <div className="panel">
        <h3>Skills <span className="count-muted">{draft.skills.length}</span></h3>
        <ChipList label="skill" items={draft.skills} max={LIMITS.skills} maxChars={LIMITS.skill} added={added} onChange={(skills) => setDraft({ ...draft, skills })} />
      </div>

      <div className="panel-grid">
        <div className="panel">
          <h3>Seniority</h3>
          <select className="field" value={draft.seniority} aria-label="Seniority" onChange={(e) => setDraft({ ...draft, seniority: e.target.value as ResumeSeniority })}>
            {LEVELS.map((level) => (
              <option key={level}>{level}</option>
            ))}
          </select>
        </div>
        <div className="panel">
          <h3>Years of experience</h3>
          <p className="stat">{info.facts.years ?? "–"}</p>
          <p className="muted">{info.facts.years === null ? "Not worked out from the role dates" : "Counted from the role dates"}</p>
        </div>
      </div>

      <div className="panel">
        <h3>Locations</h3>
        <ChipList label="location" items={draft.locations} max={LIMITS.locations} maxChars={LIMITS.location} onChange={(locations) => setDraft({ ...draft, locations })} />
      </div>

      {error && <p className="error" role="alert">{error}</p>}
      {/* Only there while something is unsaved, so the page says when edits would be lost. */}
      {dirty && (
        <div className="save-bar no-print">
          <span>Unsaved changes</span>
          <div className="actions">
            <button type="button" className="ghost" onClick={() => setDraft(draftOf(info.facts))}>
              <Undo2 size={16} aria-hidden /> Discard
            </button>
            <button type="button" className="primary" disabled={saving} onClick={save}>
              <Save size={16} aria-hidden /> {saving ? "Saving…" : "Save changes"}
            </button>
          </div>
        </div>
      )}
    </section>
  )
}

// A note that sits over the page until it is closed, for news about an upload the CSM didn't watch finish.
function Toast({ tone, text, onClose }: { tone: "ok" | "bad"; text: string; onClose: () => void }) {
  return (
    <div className={`toast ${tone}`} role="status">
      {tone === "ok" ? <Check size={16} aria-hidden /> : <X size={16} aria-hidden />}
      <span>{text}</span>
      <button type="button" className="ghost icon-btn" aria-label="Dismiss" onClick={onClose}>
        <X size={14} aria-hidden />
      </button>
    </div>
  )
}

type Notice = { tone: "ok" | "bad"; text: string }

export function ResumePanel({ customerId }: { customerId: string }) {
  const [info, setInfo] = useState<ResumeInfo | null>(null)
  const [loaded, setLoaded] = useState(false)
  const [replacing, setReplacing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<Notice | null>(null)
  const [checking, setChecking] = useState(false)
  const [, rerender] = useReducer((n: number) => n + 1, 0)
  const upload = uploadOf(customerId)

  useEffect(() => {
    // A Customer with no Resume answers 404, which just means the drop zone shows.
    getResume(customerId)
      .then(setInfo, (e) => {
        if (!(e instanceof ApiError && e.code === "no_resume")) setError(refusal(e))
      })
      .finally(() => setLoaded(true))
  }, [customerId])

  // An upload that settled while this tab was closed is reported here; one that settles while it's open plays its bar.
  useEffect(() => {
    function settle(away: boolean) {
      const done = uploadOf(customerId)
      if (!done) return
      if (done.error) {
        finishUpload(customerId)
        if (away) setNotice({ tone: "bad", text: `The upload didn't finish: ${refusal(done.error)}` })
        else setError(refusal(done.error))
      } else if (done.result && away) {
        finishUpload(customerId)
        setInfo(done.result)
        setReplacing(false)
        setNotice({ tone: "ok", text: "The Resume finished reading while you were away." })
      }
      rerender()
    }
    settle(true)
    return onUploadSettled(customerId, () => settle(false))
  }, [customerId])

  // After a reload the upload's answer is lost, but the server may still save it, so the Resume is checked for a while.
  useEffect(() => {
    const stored = reloadedUpload(customerId)
    if (stored === null) return
    const startedAt = stored
    setChecking(true)
    const check = () =>
      getResume(customerId).then(
        (r) => {
          // A little slack, because the server's clock and this browser's needn't agree.
          if (new Date(r.uploaded_at).getTime() < startedAt - 30_000) return false
          setInfo(r)
          setNotice({ tone: "ok", text: "The Resume finished reading after the page reloaded." })
          return true
        },
        () => false,
      )
    const timer = setInterval(async () => {
      if ((await check()) || reloadWindowOver(startedAt)) stop()
    }, 3000)
    function stop() {
      clearInterval(timer)
      forgetReload(customerId)
      setChecking(false)
      if (reloadWindowOver(startedAt)) setNotice({ tone: "bad", text: "The last upload didn't finish. Upload the Resume again." })
    }
    check().then((found) => found && stop())
    return () => clearInterval(timer)
  }, [customerId])

  function send(body: Blob | string) {
    if (upload) return
    setError(null)
    setNotice(null)
    startUpload(customerId, body)
    rerender()
  }

  // Runs once the bar has reached the end, so the facts replace a finished bar rather than a jump.
  function shown() {
    const done = uploadOf(customerId)
    finishUpload(customerId)
    if (done?.result) setInfo(done.result)
    setReplacing(false)
    rerender()
  }

  async function remove() {
    if (!(await ask("Delete this Resume? Runs will no longer use it.", "Delete Resume"))) return
    try {
      await deleteResume(customerId)
      setInfo(null)
    } catch (e) {
      setError(refusal(e))
    }
  }

  async function replace() {
    if (await ask("A new Resume replaces this one and discards any edits made to it.", "Choose a new Resume")) setReplacing(true)
  }

  const toast = notice && <Toast tone={notice.tone} text={notice.text} onClose={() => setNotice(null)} />
  if (upload) return <UploadProgress startedAt={upload.startedAt} finished={upload.result !== null} onShown={shown} />
  if (!loaded) return <div className="panel skeleton" aria-busy="true" />
  if (checking && !info) return <div className="panel"><p className="muted">An upload was still being read when the page reloaded. Checking whether it finished…</p></div>
  if (!info || replacing)
    return (
      <>
        {toast}
        <DropZone onSend={send} error={error} onCancel={info ? () => setReplacing(false) : undefined} />
      </>
    )
  return (
    <>
      {toast}
      {error && <p className="error" role="alert">{error}</p>}
      <Facts
        // Keyed on the upload, so a fresh Resume starts from its own facts.
        key={info.uploaded_at}
        customerId={customerId}
        info={info}
        onChange={setInfo}
        onReplace={replace}
        onDelete={remove}
      />
    </>
  )
}
