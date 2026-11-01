# Routing trace

The path the agent took. Green boxes are Steps it ran, amber boxes are where it stopped and waited for you, and a label on an arrow is the decision it made there. `×2` means that move happened twice.

```mermaid
flowchart TD
    read["Read your request<br/>×2"]
    ask["Ask you<br/>⏸ waited for you"]
    plan["Plan the search"]
    approve["Your approval<br/>⏸ waited for you"]
    search["Search job boards"]
    filter["Filter postings"]
    postings["Read postings"]
    normalise["Tidy skill names"]
    stats["Compute the numbers"]
    write["Write the brief"]
    check["Check every claim"]
    finish["Finish"]
    read -->|"asking location"| ask
    ask --> read
    read -->|"request is final"| plan
    plan --> approve
    approve --> search
    search --> filter
    filter -->|"30 of 31 Postings relevant → analyse"| postings
    postings --> normalise
    normalise --> stats
    stats --> write
    write --> check
    check -->|"8 of 8 Insights supported → render"| finish
    class read,ask,plan,approve,search,filter,postings,normalise,stats,write,check,finish done
    class approve,ask paused
    classDef done fill:#dbe8e3,stroke:#2f5d50,color:#1f2430
    classDef paused fill:#f7e8d3,stroke:#8a4206,color:#1f2430
```

Not needed in this Run: Widen the search, Too few postings?.
