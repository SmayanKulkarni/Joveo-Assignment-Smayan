// Hand-written to match the API. The contract test keeps the Demo Run's events honest.
export type Dimension = "demand" | "compensation" | "skills" | "competition" | "titles_seniority"
export type RunStatus = "running" | "paused" | "done" | "aborted" | "failed"

export type Graph = {
  nodes: { id: string; owner: string }[]
  edges: { source: string; target: string }[]
}

export type Meta = {
  graph: Graph
  dimensions: Dimension[]
  countries: string[]
  categories: string[]
  confidence_key: string
  outlook_meaning: Record<Brief["outlook"]["rating"], string>
  demo: boolean
  sign_in: boolean
}

export type Me = { id: string; email: string }

export type Customer = {
  id: string
  csm_id: string
  name: string
  note: string | null
  created_at: string
  updated_at: string
}

export type RunRecord = {
  thread_id: string
  summary: string
  status: RunStatus
  error: string | null
  customer_id: string | null
  created_at: string
  updated_at: string
}

export type SearchPlan = {
  titles: string[]
  country: string
  locations: string[]
  radius_km: number
  max_days_old: number
  target_postings: number
  category: string | null
}

export type Question = { about: string; text: string; options: string[]; answer: string | null }

export type Pause =
  | { kind: "clarify"; payload: { questions: Question[] } }
  | { kind: "plan_review"; payload: { plan: SearchPlan; assumptions: { about: string; value: string; reason: string }[]; calls_left: number | null; from_profile: string[] } }
  | {
      kind: "low_data_review"
      payload: {
        count: number
        target: number
        attempts: number
        plans: SearchPlan[]
        fetched: number
        rejected: number
        calls_left: number | null
        blocked: string | null
      }
    }

export type RunDetail = {
  record: RunRecord
  request_text: string | null
  focus: Dimension[]
  pause: Pause | null
  stopped_at: string | null
  run_log: { node: string; kind: string; message: string }[]
  live_from: number | null
  brief: Brief | null
  recommendation: Recommendation | null
  sample: PostingRef[]
  matches: Match[]
  shown_keys: string[]
  glance: Glance | null
}

export type Level = "fits" | "stretch" | "far" | "not_judged"
export type Match = {
  posting_key: string
  score: number
  matched: { posting: string; resume: string; added: boolean }[]
  missing: string[]
  level: Level
  level_reason: string
}

export type ResumeInfo = { uploaded_at: string }

export type ProfileField = "role" | "country" | "currency" | "seniority" | "employment_type" | "work_mode" | "places" | "focus" | "titles"
export type Profile = {
  values: Partial<Record<ProfileField, { value: string | string[]; runs: number | null }>> // runs is null when the CSM set it
  titles: Record<string, number>
  earlier: { thread_id: string; date: string; role: string; country: string; sample_size: number; median_pay: number | null; currency: string | null }[]
  cleared_at: string | null
}

export type Row = { label: string; count: number; required: number | null; stat_ids: string[]; evidence: Evidence }
export type RowChart = { caption: string; rows: Row[] }
export type Glance = {
  reader_notes: string[]
  pay: { low: number; median: number; high: number; unit: string; postings: number; stat_ids: string[]; evidence: Evidence } | null
  skills: RowChart | null
  places: RowChart | null
  employers: RowChart | null
}

export type PostingRef = {
  key: string
  title: string
  company: string | null
  location: string
  url: string | null
  posted_at: string
  source: string
  pay: string
  labels: string[]
}

export type Evidence = { posting_keys: string[] }
export type Stat = { id: string; label: string; value: number | string; unit: string | null }
export type Confidence = "high" | "medium" | "low"
type Cited = { reason: string; stat_ids: string[]; evidence: Evidence }

export type Recommendation = {
  job_title: (Cited & { title: string }) | null
  salary_band: (Cited & { low: number; high: number; unit: string }) | null
  top_skills: (Cited & { skills: string[] }) | null
  matches_note: string
  compared: string | null
}

export type Brief = {
  hiring_request: { role: string; location: string }
  replayed: boolean
  summary: string
  insights: { text: string; confidence: Confidence; confidence_reason: string; stat_ids: string[]; evidence: Evidence }[]
  outlook: Cited & { rating: "favourable" | "competitive" | "hard_to_fill" }
  run_notes: {
    questions: Question[]
    assumptions: { about: string; value: string; reason: string }[]
    focus: Dimension[]
    final_plan: SearchPlan
    earlier_plans: SearchPlan[]
    postings_analysed: Evidence
    match_totals: string[]
    caveats: string[]
    resume_note: string | null
    from_profile: string[]
    attribution: string | null
    matches_note: string
  }
  stats: { sample_size: number; stats: Stat[] }
}

export type RunEvent =
  | { type: "node_started"; node: string }
  | { type: "node_done"; node: string; notes: string[]; results: string[] }
  | { type: "token"; node: string; text: string }
  | { type: "reasoning"; node: string; text: string }
  | { type: "tool_called"; name: string; summary: string }
  | { type: "tool_returned"; name: string; summary: string }
  | { type: "api_called"; source: string; cached: boolean; count: number; failed: boolean }
  | { type: "extract_progress"; done: number; total: number }
  | { type: "paused"; pause: Pause }
  | { type: "done"; status: "done" | "aborted"; paths: string[] }
  | { type: "stopped"; node: string | null; reason: string }

// caught_up is the one message the server adds: it ends the replay.
export type WireEvent = RunEvent | { type: "caught_up" }
