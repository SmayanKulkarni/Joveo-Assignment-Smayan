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
  demo: boolean
}

export type RunRecord = {
  thread_id: string
  summary: string
  status: RunStatus
  error: string | null
  created_at: string
  updated_at: string
}

export type SearchPlan = {
  titles: string[]
  country: string
  location: string
  radius_km: number
  max_days_old: number
  target_postings: number
  category: string | null
}

export type Question = { about: string; text: string; options: string[]; answer: string | null }

export type Pause =
  | { kind: "clarify"; payload: { questions: Question[] } }
  | { kind: "plan_review"; payload: { plan: SearchPlan; assumptions: { about: string; value: string; reason: string }[] } }
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
  sample: PostingRef[]
}

export type PostingRef = {
  key: string
  title: string
  company: string | null
  location: string
  url: string | null
  posted_at: string
}

export type Evidence = { posting_keys: string[] }
export type Stat = { id: string; label: string; value: number | string; unit: string | null }
export type Confidence = "high" | "medium" | "low"
type Cited = { reason: string; stat_ids: string[]; evidence: Evidence }

export type Brief = {
  hiring_request: { role: string; location: string }
  replayed: boolean
  summary: string
  insights: { text: string; confidence: Confidence; confidence_reason: string; stat_ids: string[]; evidence: Evidence }[]
  recommendations: {
    job_title: (Cited & { title: string }) | null
    salary_band: (Cited & { low: number; high: number; unit: string }) | null
    top_skills: (Cited & { skills: string[] }) | null
  }
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
    attribution: string | null
  }
  stats: { sample_size: number; stats: Stat[] }
}

export type RunEvent =
  | { type: "node_started"; node: string }
  | { type: "node_done"; node: string; notes: string[] }
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
