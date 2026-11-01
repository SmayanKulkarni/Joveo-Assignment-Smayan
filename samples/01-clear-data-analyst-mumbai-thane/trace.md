# Routing trace

The path the agent took. Green boxes are Steps it ran, amber boxes are where it stopped and waited for you, and a label on an arrow is the decision it made there. `×2` means that move happened twice.

```mermaid
flowchart TD
    read["Read your request"]
    plan["Plan the search"]
    approve["Your approval<br/>⏸ waited for you"]
    search["Search job boards"]
    filter["Filter postings"]
    few["Too few postings?<br/>⏸ waited for you"]
    postings["Read postings"]
    normalise["Tidy skill names"]
    stats["Compute the numbers"]
    write["Write the brief"]
    check["Check every claim"]
    finish["Finish"]
    read -->|"request is final"| plan
    plan --> approve
    approve --> search
    search --> filter
    filter -->|"27 of 28 Postings relevant → low_data_review"| few
    few --> postings
    postings --> normalise
    normalise --> stats
    stats --> write
    write --> check
    check -->|"8 of 8 Insights supported → render"| finish
    class read,plan,approve,search,filter,few,postings,normalise,stats,write,check,finish done
    class approve,few paused
    classDef done fill:#dbe8e3,stroke:#2f5d50,color:#1f2430
    classDef paused fill:#f7e8d3,stroke:#8a4206,color:#1f2430
```

Not needed in this Run: Ask you, Widen the search.
