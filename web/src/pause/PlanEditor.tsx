import { useState } from "react"
import type { FormEvent } from "react"
import type { SearchPlan } from "../api/types"
import { Refusals } from "./parts"
import type { Refusal } from "./submit"

const MAX_TITLES = 4
const NUMBERS = [
  ["radius_km", "Radius (km)", 0, 100],
  ["max_days_old", "Posted within (days)", 1, 60],
  ["target_postings", "Target Postings", 20, 200],
] as const

type Props = {
  plan: SearchPlan
  countries: string[]
  categories: string[]
  busy: boolean
  refusal: Refusal | null
  onUse: (plan: SearchPlan) => void
  onCancel: () => void
}

export function PlanEditor({ plan, countries, categories, busy, refusal, onUse, onCancel }: Props) {
  const [titles, setTitles] = useState(plan.titles)
  const [country, setCountry] = useState(plan.country)
  const [location, setLocation] = useState(plan.location)
  const [category, setCategory] = useState(plan.category ?? "")
  // Kept as text while editing. A blank number goes to the server as null, which it refuses against its own field.
  const [numbers, setNumbers] = useState(() => Object.fromEntries(NUMBERS.map(([key]) => [key, String(plan[key])])))
  const fields = refusal?.fields ?? {}

  const setTitle = (i: number, value: string) => setTitles((all) => all.map((t, j) => (j === i ? value : t)))

  function use(event: FormEvent) {
    event.preventDefault()
    const number = (key: string) => (numbers[key].trim() === "" ? null : Number(numbers[key]))
    onUse({
      titles: titles.map((t) => t.trim()).filter(Boolean), // a blank row is an unused one
      country,
      location: location.trim(),
      radius_km: number("radius_km"),
      max_days_old: number("max_days_old"),
      target_postings: number("target_postings"),
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
    <form className="card" noValidate onSubmit={use}>
      <h2>Edit the search plan</h2>
      <Refusals refusal={refusal} />
      <fieldset {...invalid("titles")}>
        <legend>Job titles</legend>
        {titles.map((title, i) => (
          <div className="row" key={i}>
            <input type="text" value={title} onChange={(e) => setTitle(i, e.target.value)} aria-label={`Job title ${i + 1}`} />
            <button
              type="button"
              disabled={titles.length === 1}
              onClick={() => setTitles((all) => all.filter((_, j) => j !== i))}
              aria-label={`Remove title ${i + 1}`}
            >
              Remove
            </button>
          </div>
        ))}
        <button type="button" disabled={titles.length >= MAX_TITLES} onClick={() => setTitles((all) => [...all, ""])}>
          Add a title
        </button>
        {error("titles")}
      </fieldset>
      <label>
        Country
        <select value={country} onChange={(e) => setCountry(e.target.value)} {...invalid("country")}>
          {countries.map((c) => (
            <option key={c} value={c}>
              {c.toUpperCase()}
            </option>
          ))}
        </select>
        {error("country")}
      </label>
      <label>
        Location
        <input
          type="text"
          value={location}
          onChange={(e) => setLocation(e.target.value)}
          placeholder="Leave blank to search the whole country"
        />
        {error("location")}
      </label>
      {NUMBERS.map(([key, label, min, max]) => (
        <label key={key}>
          {label}
          <input
            type="number"
            min={min}
            max={max}
            value={numbers[key]}
            onChange={(e) => setNumbers((n) => ({ ...n, [key]: e.target.value }))}
            {...invalid(key)}
          />
          {error(key)}
        </label>
      ))}
      <label>
        Category
        <select value={category} onChange={(e) => setCategory(e.target.value)} {...invalid("category")}>
          <option value="">Any</option>
          {categories.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
        {error("category")}
      </label>
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
