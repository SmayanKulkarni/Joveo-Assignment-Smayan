from enum import StrEnum

from pydantic import Field

from talent_scout.kernel.types import (
    Assumption, ClarifyingQuestion, Dimension, Evidence, HiringRequest, MarketStats, Model, SearchPlan,
)


class Confidence(StrEnum):
    high = "high"
    medium = "medium"
    low = "low"


class OutlookRating(StrEnum):
    favourable = "favourable"
    competitive = "competitive"
    hard_to_fill = "hard_to_fill"


class InsightDraft(Model):
    text: str = Field(description="One finding of at most 20 words, phrased in plain descriptive words and copying figures exactly as given.")
    stat_ids: list[str] = Field(description="Ids of every Stat the finding relies on, and only those.")


class BriefDraft(Model):
    summary: str = Field(description="Two to three sentences on the market, with at most three figures.")
    summary_stat_ids: list[str] = Field(description="Ids of the Stats the summary relies on.")
    insights: list[InsightDraft] = Field(description="The findings, each about one thing.")


class BriefRevision(Model):
    insights: list[InsightDraft] = Field(description="Replacements for the flagged findings only, each a single simple finding.")


class InsightVerdict(Model):
    supported: bool
    p_yes: float


class Insight(Model):
    text: str
    dimension: Dimension  # the first cited Stat's
    stat_ids: list[str]
    evidence: Evidence
    confidence: Confidence
    confidence_reason: str


class HiringOutlook(Model):
    rating: OutlookRating
    reason: str
    stat_ids: list[str]  # empty at the default
    evidence: Evidence


class _Recommendation(Model):
    reason: str
    stat_ids: list[str]
    evidence: Evidence


class TitleRecommendation(_Recommendation):
    title: str


class BandRecommendation(_Recommendation):
    low: float
    high: float
    unit: str


class SkillsRecommendation(_Recommendation):
    skills: list[str]


class ClientRecommendations(Model):
    job_title: TitleRecommendation | None
    salary_band: BandRecommendation | None
    top_skills: SkillsRecommendation | None


class RunNotes(Model):
    questions: list[ClarifyingQuestion]
    assumptions: list[Assumption]
    focus: list[Dimension]
    final_plan: SearchPlan  # state.current_plan
    earlier_plans: list[SearchPlan]
    postings_analysed: Evidence  # the Sample
    match_totals: list[str]  # labelled disclosure, never a Stat
    caveats: list[str]  # messages: state.py imports this file, so no RunLogEntry
    attribution: str | None


class MarketBrief(Model):
    hiring_request: HiringRequest
    replayed: bool
    summary: str
    summary_stat_ids: list[str]
    insights: list[Insight]  # no minimum: zero Postings gives none
    recommendations: ClientRecommendations
    outlook: HiringOutlook
    run_notes: RunNotes
    stats: MarketStats  # whole, so every cited id can be checked
