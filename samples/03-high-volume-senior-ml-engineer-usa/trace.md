# Routing trace

The path the agent took. Green boxes are Steps it ran, amber boxes are where it stopped and waited for you, and a label on an arrow is the decision it made there. `×2` means that move happened twice.

```mermaid
flowchart TD
    read["Read your request<br/>×5"]
    ask["Ask you<br/>×4<br/>⏸ waited for you"]
    plan["Plan the search"]
    approve["Your approval<br/>⏸ waited for you"]
    search["Search job boards<br/>×3"]
    filter["Filter postings<br/>×3"]
    widen["Widen the search<br/>×2"]
    postings["Read postings"]
    normalise["Tidy skill names"]
    stats["Compute the numbers"]
    write["Write the brief<br/>×2"]
    check["Check every claim<br/>×2"]
    finish["Finish"]
    read -->|"×4 asking seniority<br/>asking location"| ask
    ask -->|"×4"| read
    read -->|"request is final"| plan
    plan --> approve
    approve --> search
    search -->|"×3"| filter
    filter -->|"×2 136 of 217 Postings relevant → broaden<br/>158 of 293 Postings relevant → broaden"| widen
    widen -->|"×2"| search
    filter -->|"243 of 399 Postings relevant → analyse"| postings
    postings --> normalise
    normalise --> stats
    stats --> write
    write -->|"×2"| check
    check -->|"7 of 8 Insights supported → write_brief"| write
    check -->|"1 of 1 Insights supported → render"| finish
    class read,ask,plan,approve,search,filter,widen,postings,normalise,stats,write,check,finish done
    class approve,ask paused
    classDef done fill:#dbe8e3,stroke:#2f5d50,color:#1f2430
    classDef paused fill:#f7e8d3,stroke:#8a4206,color:#1f2430
```

Not needed in this Run: Too few postings?.
