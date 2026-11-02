import type { ResumeFacts, ResumePatch, ResumeRole, ResumeSeniority } from "../api/types"

// Caps from analysis/resume.py and analysis/types.py, so the form refuses what the API would.
export const LIMITS = { roles: 15, skills: 30, locations: 10, title: 100, date: 30, skill: 40, location: 100 }

export type Draft = { roles: ResumeRole[]; skills: string[]; seniority: ResumeSeniority; locations: string[] }

export const draftOf = (facts: ResumeFacts): Draft => ({
  roles: facts.roles,
  skills: facts.skills.map((s) => s.name),
  seniority: facts.seniority,
  locations: facts.locations,
})

// Only the fields that differ, so a correction never overwrites what it didn't touch.
export function changes(facts: ResumeFacts, draft: Draft): ResumePatch {
  const before: Draft = draftOf(facts)
  return Object.fromEntries(Object.entries(draft).filter(([key, value]) => JSON.stringify(value) !== JSON.stringify(before[key as keyof Draft])))
}
