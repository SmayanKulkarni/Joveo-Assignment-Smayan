# 02: Shared domain types

**What to build:** the cross-component vocabulary every stage and the Gateway import: Posting (with Salary, Source, PayPeriod), Hiring Request, Clarifying Question, Assumption, Search Plan, Evidence, Stat and Market stats. Invalid values are refused at construction, and those validator errors are what later feed the LLM's retry. Spec: [Kernel LLD](../../../docs/lld/kernel.md) §2, §3, §16 step 3.

Types read inside a single component (Extraction, Insight, Market Brief and so on) stay out of this ticket.

**Blocked by:** 01: Project skeleton and settings.

**Status:** done

- [x] All types and fields in LLD §3 exist, each model frozen with `extra="forbid"`
- [x] Enums are `StrEnum`, money is `float`, dates are `date`
- [x] LLM-filled types carry a `Field(description=...)` on every field, and optional fields are `T | None` with no default
- [x] Test: Posting `key` is `source:source_id`
- [x] Test: Salary rejects no bounds, `min > max` and a bad currency code
- [x] Test: Evidence sorts and dedupes its keys, and `count` matches
- [x] Test: Market stats reject duplicate Stat ids
- [x] Test: Search Plan rejects empty titles, a bad country code and out-of-range numbers; Hiring Request rejects a blank role or location
