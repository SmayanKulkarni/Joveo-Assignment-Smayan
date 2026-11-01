import { useState } from "react"
import type { FormEvent, KeyboardEvent } from "react"
import type { SearchPlan } from "../api/types"
import { categoryName, countryName } from "../labels"
import { Refusals } from "./parts"
import type { Refusal } from "./submit"

const MAX_TITLES = 4
const RADII = [5, 10, 25, 50, 100]
const DAYS = [7, 14, 30, 60]

type Props = {
  plan: SearchPlan
  countries: string[]
  categories: string[]
  busy: boolean
  refusal: Refusal | null
  onUse: (plan: SearchPlan) => void
  onCancel: () => void
}

// A plan's own value stays choosable when it isn't a preset, so opening the editor never changes it.
function Choice({ presets, value, unit, ...rest }: { presets: number[]; value: string; unit: string } & React.SelectHTMLAttributes<HTMLSelectElement>) {
  const options = presets.includes(Number(value)) ? presets : [...presets, Number(value)].sort((a, b) => a - b)
  return (
    <select value={value} {...rest}>
      {options.map((n) => (
        <option key={n} value={n}>
          {n} {unit}
        </option>
      ))}
    </select>
  )
}

export function PlanEditor({ plan, countries, categories, busy, refusal, onUse, onCancel }: Props) {
  const [titles, setTitles] = useState(plan.titles)
  const [draft, setDraft] = useState("")
  const [country, setCountry] = useState(plan.country)
  const [location, setLocation] = useState(plan.location)
  const [category, setCategory] = useState(plan.category ?? "")
  const [radius, setRadius] = useState(String(plan.radius_km))
  const [days, setDays] = useState(String(plan.max_days_old))
  // Kept as text while editing. A blank number goes to the server as null, which it refuses against its own field.
  const [target, setTarget] = useState(String(plan.target_postings))
  const fields = refusal?.fields ?? {}

  const addTitle = () => {
    const title = draft.trim()
    if (title && titles.length < MAX_TITLES && !titles.includes(title)) setTitles((all) => [...all, title])
    setDraft("")
  }

  function onKey(event: KeyboardEvent) {
    if (event.key !== "Enter") return
    event.preventDefault() // Enter adds the title; it doesn't submit the plan
    addTitle()
  }

  function use(event: FormEvent) {
    event.preventDefault()
    const typed = draft.trim() // a title typed but not yet added still counts
    onUse({
      titles: typed && !titles.includes(typed) ? [...titles, typed] : titles,
      country,
      location: location.trim(),
      radius_km: Number(radius),
      max_days_old: Number(days),
      target_postings: target.trim() === "" ? null : Number(target),
      category: category || null,
    } as SearchPlan)
  }

  const error = (key: string) =>
    fields[key] && (
      <p className="field-error" id={`err-${key}`}>
        {fields[key]}
      </p>
    )
  const invalid = (key: string) => ({ "aria-invalid": !!fields[key], "aria-describedby": fields[key] ? `err-${key}` : undefined })

  // noValidate: the HTML limits only guide, and the server is the check.
  return (
    <form className="card editor" noValidate onSubmit={use}>
      <h2>Edit the search plan</h2>
      <Refusals refusal={refusal} />
      <div className="grid">
        <div className="span2">
          <label htmlFor="add-title">Job titles</label>
          <div className="chips field" {...invalid("titles")}>
            {titles.map((title, i) => (
              <span className="chip" key={title}>
                {title}
                <button
                  type="button"
                  disabled={titles.length === 1 && !draft.trim()}
                  onClick={() => setTitles((all) => all.filter((_, j) => j !== i))}
                  aria-label={`Remove ${title}`}
                >
                  ×
                </button>
              </span>
            ))}
            <input
              id="add-title"
              type="text"
              value={draft}
              disabled={titles.length >= MAX_TITLES}
              placeholder={titles.length >= MAX_TITLES ? `Up to ${MAX_TITLES} titles` : "Add a title, press Enter"}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={onKey}
            />
          </div>
          {error("titles")}
        </div>
        <label className="span2">
          Location
          <input type="text" value={location} onChange={(e) => setLocation(e.target.value)} placeholder="Leave blank to search the whole country" />
          {error("location")}
        </label>
        <label>
          Country
          <select value={country} onChange={(e) => setCountry(e.target.value)} {...invalid("country")}>
            {countries.map((c) => (
              <option key={c} value={c}>
                {countryName(c)}
              </option>
            ))}
          </select>
          {error("country")}
        </label>
        <label>
          Within
          <Choice presets={RADII} unit="km" value={radius} onChange={(e) => setRadius(e.target.value)} {...invalid("radius_km")} />
          {error("radius_km")}
        </label>
        <label>
          Posted in the last
          <Choice presets={DAYS} unit="days" value={days} onChange={(e) => setDays(e.target.value)} {...invalid("max_days_old")} />
          {error("max_days_old")}
        </label>
        <label>
          Target Postings
          <input type="number" min={20} max={200} value={target} onChange={(e) => setTarget(e.target.value)} {...invalid("target_postings")} />
          {error("target_postings")}
        </label>
        <label className="span2">
          Category
          <select value={category} onChange={(e) => setCategory(e.target.value)} {...invalid("category")}>
            <option value="">Any</option>
            {categories.map((c) => (
              <option key={c} value={c}>
                {categoryName(c)}
              </option>
            ))}
          </select>
          {error("category")}
        </label>
      </div>
      <div className="actions">
        <button type="submit" className="start" disabled={busy}>
          Use this plan
        </button>
        <button type="button" disabled={busy} onClick={onCancel}>
          Cancel
        </button>
      </div>
    </form>
  )
}
