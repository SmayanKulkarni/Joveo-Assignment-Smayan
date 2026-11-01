import type { SearchPlan } from "./api/types"

export const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? "" : "s"}`

export const where = (plan: SearchPlan) => `${plan.location.trim() || "Country-wide"} (${plan.country.toUpperCase()})`

export const planLine = (p: SearchPlan) =>
  `${p.titles.join(", ")}; ${where(p)}; radius ${p.radius_km} km; up to ${p.max_days_old} days old; target ${p.target_postings}; ` +
  `category ${p.category ?? "any"}`
