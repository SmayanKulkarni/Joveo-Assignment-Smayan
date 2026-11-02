import { useEffect, useState } from "react"
import type { FormEvent } from "react"
import { clearProfile, editProfile, getProfile } from "../api/client"
import type { Profile, ProfileField } from "../api/types"
import { plural } from "../util"

const LABELS: Record<ProfileField, string> = {
  role: "Role",
  country: "Country",
  places: "Places",
  currency: "Currency",
  seniority: "Seniority",
  employment_type: "Employment type",
  work_mode: "Work mode",
  focus: "Focus",
  titles: "Titles that worked",
}
const LISTS: ProfileField[] = ["places", "focus"]
const FIELDS = Object.keys(LABELS).filter((f) => f !== "titles") as ProfileField[]

const text = (value: string | string[]) => (Array.isArray(value) ? value.join(", ") : value)

function SetValue({ field, onSet }: { field: ProfileField; onSet: (value: string | string[]) => Promise<void> }) {
  const [value, setValue] = useState("")
  async function submit(event: FormEvent) {
    event.preventDefault()
    const parts = value.split(",").map((v) => v.trim()).filter(Boolean)
    if (parts.length === 0) return
    await onSet(LISTS.includes(field) ? parts : value.trim())
    setValue("")
  }
  return (
    <form onSubmit={submit} className="inline">
      <input value={value} onChange={(e) => setValue(e.target.value)} aria-label={`Set ${LABELS[field]}`} placeholder={LISTS.includes(field) ? "a, b" : "Set"} />
      <button type="submit">Set</button>
    </form>
  )
}

export function ProfilePanel({ customerId }: { customerId: string }) {
  const [profile, setProfile] = useState<Profile | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getProfile(customerId).then(setProfile, () => setError("The Profile didn't load."))
  }, [customerId])

  // One place for every change, so a refusal shows the same way and the screen always shows what the server holds.
  async function change(work: () => Promise<Profile | void>) {
    setError(null)
    try {
      setProfile((await work()) ?? (await getProfile(customerId)))
    } catch {
      setError("That didn't save. Check the value and try again.")
    }
  }

  async function clear() {
    if (!confirm("Clear everything learned about this Customer? Earlier Runs will no longer count.")) return
    await change(() => clearProfile(customerId))
  }

  if (!profile) return error ? <p className="error">{error}</p> : <p>Loading…</p>
  const titles = Object.entries(profile.titles)
  const empty = Object.keys(profile.values).length === 0 && titles.length === 0

  return (
    <section className="profile">
      <p className="muted">Worked out from this Customer's last 10 finished Runs. It doesn't change any Run yet.</p>
      {error && <p className="error">{error}</p>}
      {empty && <p>Nothing learned yet. It fills in as Runs finish.</p>}
      <table>
        <tbody>
          {FIELDS.map((field) => {
            const entry = profile.values[field]
            return (
              <tr key={field}>
                <th scope="row">{LABELS[field]}</th>
                <td>{entry ? text(entry.value) : <span className="muted">none</span>}</td>
                <td className="muted">{entry && (entry.runs === null ? "set by you" : `from ${plural(entry.runs, "Run")}`)}</td>
                <td className="no-print">
                  <SetValue field={field} onSet={(value) => change(() => editProfile(customerId, { set: { [field]: value } }))} />
                  {entry && (
                    <button type="button" onClick={() => change(() => editProfile(customerId, { remove: [field] }))}>
                      Remove
                    </button>
                  )}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
      {titles.length > 0 && (
        <>
          <h3>{LABELS.titles}</h3>
          <ul>
            {titles.map(([title, runs]) => (
              <li key={title}>
                {title} <span className="muted">({plural(runs, "Run")})</span>
              </li>
            ))}
          </ul>
          <button type="button" onClick={() => change(() => editProfile(customerId, { remove: ["titles"] }))}>
            Remove titles
          </button>
        </>
      )}
      {profile.earlier.length > 0 && (
        <>
          <h3>Earlier results</h3>
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Role</th>
                <th>Country</th>
                <th>Sample</th>
                <th>Median advertised pay</th>
              </tr>
            </thead>
            <tbody>
              {profile.earlier.map((e) => (
                <tr key={e.thread_id}>
                  <td>{e.date}</td>
                  <td>{e.role}</td>
                  <td>{e.country.toUpperCase()}</td>
                  <td>{e.sample_size}</td>
                  <td>{e.median_pay === null ? "not enough" : `${Math.round(e.median_pay).toLocaleString("en-US")} ${e.currency ?? ""}`}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
      <button type="button" className="danger no-print" onClick={clear}>
        Clear everything
      </button>
    </section>
  )
}
