# What is the node-level graph shape?

Type: grilling
Status: resolved

## Question

What nodes, fixed edges, conditional edges and Pauses make up the StateGraph?

## Answer

Resolved during charting. Solid = fixed edge, dotted = conditional edge (label is the router outcome). Exact caps (re-asks, attempts, revisions) are LLD.

```mermaid
flowchart TD
  START([START])
  END_([END])
  intake[intake · parse request, load prefs]
  clarity_check[clarity_check · Jev ambiguity + LLM drafts questions]
  clarify[/clarify · PAUSE 1/]
  plan[plan · LLM search plan]
  plan_review[/plan_review · PAUSE 2/]
  fetch_agent[fetch_agent · LLM with bound tools]
  tools[tools · custom executor]
  collect[collect · dedupe, normalise, store]
  relevance[relevance · Jev per posting]
  broaden[broaden · LLM revises plan]
  low_data_review[/low_data_review · PAUSE 3/]
  batch_extract[batch_extract x N · LLM]
  stats[stats · python]
  write_brief[write_brief · LLM structured output]
  critic[critic · Jev per insight]
  render[render · JSON + Markdown]

  subgraph outside [outside the graph]
    gw[(Jobs Data Gateway · L1 cache, L2 store, budget guard)]
  end

  START --> intake --> clarity_check
  clarity_check -.->|"clear, or re-ask cap hit"| plan
  clarity_check -.->|"ambiguous"| clarify
  clarify --> clarity_check
  plan --> plan_review
  plan_review -.->|"approve / edit"| fetch_agent
  plan_review -.->|"reject + feedback"| plan
  plan_review -.->|"abort"| END_
  fetch_agent -.->|"has tool_calls"| tools
  fetch_agent -.->|"no tool_calls"| collect
  tools --> fetch_agent
  tools <-.-> gw
  collect --> relevance
  relevance -.->|"enough: Send x N"| batch_extract
  relevance -.->|"too few, attempts left"| broaden
  relevance -.->|"attempts exhausted"| low_data_review
  broaden --> fetch_agent
  low_data_review -.->|"broaden"| broaden
  low_data_review -.->|"continue: Send x N"| batch_extract
  low_data_review -.->|"continue with 0 postings"| stats
  low_data_review -.->|"abort"| END_
  batch_extract -->|"reducer merges"| stats
  stats --> write_brief --> critic
  critic -.->|"unsupported, revisions left"| write_brief
  critic -.->|"supported, or revision cap hit"| render
  render --> END_

  classDef pause fill:#fde7c8,stroke:#d9822b,color:#000
  classDef jev fill:#e6defc,stroke:#6b4fd8,color:#000
  classDef code fill:#ececec,stroke:#888,color:#000
  class clarify,plan_review,low_data_review pause
  class clarity_check,relevance,critic jev
  class intake,collect,stats,render,tools code
```

Notes:
- The `continue with 0 postings → stats` edge exists because a zero-length `Send` fan-out never reaches `stats`; without it the Run would stall silently.
- A vague answer to a Clarifying Question is re-asked at most once, then the Run proceeds with a recorded Assumption.
- Plan rejection returns to `plan` with the user's feedback; abort ends the Run cleanly.
