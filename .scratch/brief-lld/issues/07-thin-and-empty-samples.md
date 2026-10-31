# Thin and empty Samples

Type: grilling
Status: open
Assignee: none
Blocked by: 03, 04, 05

## Question

What does the Market Brief say when a Run continues at `low_data_review` with a weak Sample, or with zero Postings and `MarketStats(sample_size=0, stats=[])`? Does `write_brief` still call the LLM at zero, and does `critic` run? What fills the required parts, such as the outlook and recommendations, when no Evidence exists?
