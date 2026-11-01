import type { SearchPlan } from "./api/types"
import { categoryName, countryName } from "./labels"

export const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? "" : "s"}`

// "5m", "3h", "2d": how long ago, for a sidebar row.
export function ago(iso: string, now = Date.now()): string {
  const minutes = Math.max(0, Math.floor((now - Date.parse(iso)) / 6e4))
  if (minutes < 1) return "now"
  if (minutes < 60) return `${minutes}m`
  if (minutes < 1440) return `${Math.floor(minutes / 60)}h`
  return `${Math.floor(minutes / 1440)}d`
}

export const where = (plan: SearchPlan) => `${plan.locations.join(", ") || "Country-wide"}, ${countryName(plan.country)}`

export const planLine = (p: SearchPlan) =>
  `${p.titles.join(", ")}; ${where(p)}; radius ${p.radius_km} km; up to ${p.max_days_old} days old; target ${p.target_postings}; ` +
  `category ${p.category ? categoryName(p.category) : "any"}`
