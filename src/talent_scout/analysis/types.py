from enum import StrEnum

from pydantic import Field

from talent_scout.kernel.types import Model, Posting


class Seniority(StrEnum):
    entry = "entry"
    mid = "mid"
    senior = "senior"
    lead = "lead"
    executive = "executive"
    unknown = "unknown"


class EmployerType(StrEnum):
    direct = "direct"
    agency = "agency"
    unknown = "unknown"


class Requirement(StrEnum):
    must = "must"
    nice = "nice"
    unstated = "unstated"


class SkillMention(Model):
    name: str = Field(description="The skill, copied exactly from the posting.")
    requirement: Requirement = Field(description="must or nice only if the posting's wording says so, otherwise unstated.")


class _Facts(Model):
    skills: list[SkillMention] = Field(description="Skills a person could list on a CV, at most 12, one per entry.")
    seniority: Seniority = Field(description="Level from the title or explicit wording, never inferred from years; unknown if unclear.")
    years_min: int | None = Field(description="Minimum years of experience if the posting states one; null if not stated.")
    employer_type: EmployerType = Field(description="agency if the poster fills the job for a client, direct if it hires for itself, otherwise unknown.")


class Extraction(_Facts):
    # Branches can't log, so the count of skills the grounding check dropped travels with the Extraction.
    ungrounded: int = Field(description="Skills dropped because they were not in the posting text. Filled by code.")


class PostingFacts(_Facts):
    ref: int = Field(description="The ref number of the posting these facts describe.")


class BatchFacts(Model):
    items: list[PostingFacts] = Field(description="One item per posting, each with its ref.")


class ExtractBatch(Model):
    # The Send payload: State can't reach it, so it has its own allowlist entry.
    postings: list[Posting] = Field(description="The postings extracted in one call.")


class SkillGroup(Model):
    canonical: str = Field(description="The best name for the skill, chosen from the variants.")
    variants: list[str] = Field(description="Input spellings of the same skill, copied exactly.")


class SkillGroups(Model):
    groups: list[SkillGroup] = Field(description="Groups of two or more spellings of one skill.")
