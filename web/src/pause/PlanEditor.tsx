import { useState } from "react"
import type { FormEvent, KeyboardEvent } from "react"
import type { SearchPlan } from "../api/types"
import { categoryName, countryName } from "../labels"
import { Refusals } from "./parts"
import type { Refusal } from "./submit"

const has = (items: string[], item: string) => items.some((t) => t.toLowerCase() === item.toLowerCase())
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

type ChipFieldProps = {
  id: string
  label: string
  noun: string
  items: string[]
  draft: string
  onDraft: (text: string) => void
  onChange: (items: string[]) => void
  keepOne?: boolean
  placeholder: string
  invalid: object
}

// Chips with an always-open add box. Enter adds, and never submits the plan.
function ChipField({ id, label, noun, items, draft, onDraft, onChange, keepOne, placeholder, invalid }: ChipFieldProps) {
  const add = () => {
    const text = draft.trim()
    if (text && !has(items, text)) onChange([...items, text])
    onDraft("")
  }
  return (
    <>
      <label htmlFor={id}>{label}</label>
      <div className="chips field">
        {items.map((item, i) => (
          <span className="chip" key={item}>
            {item}
            <button
              type="button"
              disabled={keepOne && items.length === 1 && !draft.trim()}
              onClick={() => onChange(items.filter((_, j) => j !== i))}
              aria-label={`Remove ${noun} ${item}`}
            >
              ×
            </button>
          </span>
        ))}
        <input
          id={id}
          type="text"
          value={draft}
          placeholder={placeholder}
          onChange={(e) => onDraft(e.target.value)}
          onKeyDown={(e: KeyboardEvent) => {
            if (e.key !== "Enter") return
            e.preventDefault()
            add()
          }}
          {...invalid}
        />
      </div>
    </>
  )
}

export function PlanEditor({ plan, countries, categories, busy, refusal, onUse, onCancel }: Props) {
  const [titles, setTitles] = useState(plan.titles)
  const [draft, setDraft] = useState("")
  const [country, setCountry] = useState(plan.country)
  const [places, setPlaces] = useState(plan.locations)
  const [placeDraft, setPlaceDraft] = useState("")
  const [category, setCategory] = useState(plan.category ?? "")
  const [radius, setRadius] = useState(String(plan.radius_km))
  const [days, setDays] = useState(String(plan.max_days_old))
  // Kept as text while editing. A blank number goes to the server as null, which it refuses against its own field.
  const [target, setTarget] = useState(String(plan.target_postings))
  const fields = refusal?.fields ?? {}

  function use(event: FormEvent) {
    event.preventDefault()
    // Anything typed but not yet added still counts.
    const withTyped = (items: string[], typed: string) => (typed.trim() && !has(items, typed.trim()) ? [...items, typed.trim()] : items)
    onUse({
      titles: withTyped(titles, draft),
      country,
      locations: withTyped(places, placeDraft),
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
          <ChipField
            id="add-title" label="Job titles" noun="title" items={titles} draft={draft} onDraft={setDraft} onChange={setTitles}
            keepOne placeholder="Add a title, press Enter" invalid={invalid("titles")}
          />
          {error("titles")}
        </div>
        <div className="span2">
          <ChipField
            id="add-place" label="Places" noun="place" items={places} draft={placeDraft} onDraft={setPlaceDraft} onChange={setPlaces}
            placeholder="Add a place, or leave empty to search the whole country" invalid={invalid("locations")}
          />
          {error("locations")}
        </div>
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
          <Choice
            presets={RADII} unit="km" value={radius} onChange={(e) => setRadius(e.target.value)}
            disabled={places.length === 0 && !placeDraft.trim()} {...invalid("radius_km")}
          />
          {error("radius_km")}
        </label>
        <label>
          Posted in the last
          <Choice presets={DAYS} unit="days" value={days} onChange={(e) => setDays(e.target.value)} {...invalid("max_days_old")} />
          {error("max_days_old")}
        </label>
        <label>
          Target Postings
          <input type="number" min={20} max={600} value={target} onChange={(e) => setTarget(e.target.value)} {...invalid("target_postings")} />
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
