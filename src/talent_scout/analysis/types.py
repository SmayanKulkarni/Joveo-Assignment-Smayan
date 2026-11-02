import re
from enum import StrEnum
from typing import Annotated

from pydantic import Field, StringConstraints

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


class Role(Model):
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    start: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=30)]
    end: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=30)]


class ResumeSkill(Model):
    name: str
    added: bool = False  # not in the resume text, so the CSM put it there


class ResumeFacts(Model):
    roles: list[Role]
    skills: list[ResumeSkill]
    seniority: Seniority
    locations: list[str]
    years: int | None  # computed from the role dates, never read from the model

    @property
    def latest_title(self) -> str | None:
        # The role that ends last, with "Present" ending after any year, so the order the resume lists them in doesn't matter.
        def ends(role: Role) -> int:
            years = re.findall(r"\b(?:19|20)\d{2}\b", role.end)
            return int(years[-1]) if years else 9999

        return max(self.roles, key=ends).title if self.roles else None


class Level(StrEnum):
    fits = "fits"
    stretch = "stretch"
    far = "far"
    not_judged = "not_judged"


class MatchedSkill(Model):
    posting: str  # as the Posting writes it
    resume: str  # as the Resume writes it; shown beside the other when they differ
    added: bool  # the CSM added it to the Resume


class Match(Model):
    posting_key: str
    score: int
    matched: list[MatchedSkill]
    missing: list[str]
    level: Level
    level_reason: str
