# Salary benchmarks in the Brief

Type: grilling
Status: out of scope
Assignee: none
Blocked by: [Research: Glassdoor Real-Time](05-research-glassdoor-real-time.md), [What Arbeitnow does in the gateway](10-what-arbeitnow-does-in-the-gateway.md)

## Question

If a salary-only source joins (Glassdoor Real-Time, or JSearch's salary endpoint), does its data enter the Market Brief, and as what?

- The glossary has Advertised pay and Estimated pay, and never pools them. Is reported pay a third kind (a Salary Benchmark)? What may it say next to the Stats from the Sample?
- Where it appears: a separate line in the salary Recommendation, a band on a chart, an Insight with its own Evidence, or only the Run Notes.
- Which node fetches it (Analysis or Brief), with what budget, and what happens when it's missing.
- How the Confidence Tag and Evidence rules apply to data that isn't Postings.

If [What Arbeitnow does in the gateway](10-what-arbeitnow-does-in-the-gateway.md) rules out every salary-only source, close this ticket as out of scope.

## Out of scope

Closed 2026-11-02: the user dropped every RapidAPI source and kept only Arbeitnow. The only salary-only sources were Glassdoor Real-Time and JSearch, both on RapidAPI.
