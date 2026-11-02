# Research: job source terms for CSM use

Type: research
Status: resolved
Assignee: smayankulkarni05
Blocked by: none

## Question

Do the job sources' terms allow a CSM to use them, on behalf of customers, inside a company's tool?

- Arbeitnow: reread sections 2 and 11 of its terms. [What Arbeitnow does in the gateway](10-what-arbeitnow-does-in-the-gateway.md) judged the use to fit because the project was free and non-commercial. Does that reasoning survive a CSM serving customers? Showing individual Postings as Matches is also closer to republishing than Brief stats were.
- Adzuna: the HLD says commercial use past a 14-day evaluation needs a licence. Find the exact wording. How is a licence obtained and what does it cost? Are the display and attribution rules different for showing individual Postings?
- USAJOBS: any terms that limit this use.
- For each source: allowed, allowed with conditions, needs permission, or not allowed. Quote the clause, and list what we must do in each case.

This is reading and reporting, not legal advice. Say where a lawyer or the source itself must confirm. Capture findings in this ticket's Answer, with long notes in `../assets/`.

## Answer

**Outcome:** the user said on 2026-11-02 that this is a personal project, so licences block nothing. The plan keeps Adzuna, Arbeitnow and USAJOBS. The findings below stay as a record, and matter only if this ever stops being a personal project.

Researched 2026-11-02. All quotes were read that day. Long notes, fuller clauses, and draft questions for each source: [research-job-source-terms.md](../assets/research-job-source-terms.md).

**This isn't legal advice.** It's a reading of public pages. No source was contacted. The terms can change: none of the three pages shows a last-updated date.

### Recommendation

| Source | Verdict, paid or unpaid | What we must do |
| --- | --- | --- |
| Arbeitnow | **Needs permission** | Get written permission for this use, or take the paid private endpoint, or drop it. With permission: link back, keep Posting URLs on arbeitnow pages, and be ready for revocation. |
| Adzuna | **Needs permission** (a licence agreement) | Ask Adzuna for a licence covering Matches and Briefs. Keep the pre-licence use to its 14-day trial purpose: coverage, quality and usability testing. Display what the licence asks, by default an "Adzuna" label on each advert. |
| USAJOBS | **Allowed with conditions** | Keep registration accurate, imply no federal endorsement, use no seal, don't pass off changed text as official, and send applications to the announcement's own instructions. |

- Don't show Adzuna or Arbeitnow data to real Customers until each source has answered in writing. USAJOBS can go ahead.
- Decide what happens if Adzuna says no or the price is too high. It's the plan's main source, so this is a product decision, not a detail.
- Ticket 10 item 5 should be reversed: the courtesy email becomes a real permission request that the launch waits on.
- Whether paying customers exist doesn't change any verdict. It only affects how strong the Arbeitnow doubt is and what a licence may cost.

### Key findings

- **Arbeitnow, section 2** grants use for "personal, non-commercial transitory viewing only" and bars using the materials "for any commercial purpose, or for any public display (commercial or non-commercial)" and to "transfer the materials to another person or \"mirror\" the materials on any other server" ([terms](https://www.arbeitnow.com/terms)).
- **Arbeitnow, section 11** says "You also agree to providing a link back to Arbeitnow.com on your platform." and "We may revoke the permission to use API at any time." The API's `meta.terms` says "By using the API, you agree to the terms of service present on Arbeitnow.com" ([API](https://www.arbeitnow.com/api/job-board-api?page=99)). A link back on "your platform" suggests API data may appear elsewhere, but nothing says section 11 replaces section 2.
- **Ticket 10's reasoning doesn't survive.** It rested on free, non-commercial, no ads, and stats rather than listings. A company's tool undercuts the first, and individual Postings on a Match list undercut the last. Section 2's display ban also applies to non-commercial use, so being free never answered it.
- **Arbeitnow sells an alternative**: "I offer a custom, private, tailored API endpoint for you for a monthly fee." ([blog](https://www.arbeitnow.com/blog/job-board-api)). No price is published.
- **Adzuna's commercial clause** ([terms](https://developer.adzuna.com/docs/terms_of_service)): "Any use of the Adzuna API by a commercial, government or academic organisation, including any affiliates or individuals, is permitted subject to a 14 day trial period. This period is strictly for the purpose of validating the general coverage and quality of the data in addition to usability testing." It may not be used "in its original format or in aggregation (including but not limited to vacancy counts, average salaries etc) to deliver any ongoing work or research".
- **Adzuna's licence trigger**: "After the trial period ends, and for any use in a product or service that generates revenue or leads, a licence agreement is required." An unpaid company tool still needs one once the trial ends.
- **Market Briefs are caught as well as Matches.** "Any other use, including commercial analysis, resale of data, and sales prospecting or lead generation, requires our written agreement."
- **Adzuna licence route and cost.** The terms give only "Contact us here" (a [contact form](https://www.adzuna.co.uk/jobs/contact-us.html)). No price is published, and the paid plans are stated to be "for personal and academic use".
- **Adzuna display rules differ for individual Postings.** Each advert needs a label: "label each displayed advert with the phrase \"Adzuna\" at least 116 X 23 pixels in size, wherein the word \"Adzuna\" shall be hyperlinked". The repo's `Jobs data provided by The Adzuna API` follows the separate "Personal or academic research" form, so the shared footer in ticket 10 item 6 won't do for the Match list.
- **Other Adzuna duties that affect design.** On termination: "immediately remove all insertion codes and data acquired from Adzuna from all pages of its web sites". Contacting "a third party content provider" revokes access at once, which could matter if a CSM contacts an employer about a listing. One entity gets one account, so all CSMs share one key and quota.
- **USAJOBS is openly licensed** ([terms](https://developer.usajobs.gov/guides/terms-of-service)): "Public Data may be copied, stored, reformatted, adapted, analyzed, published, redistributed, and used for lawful commercial or noncommercial purposes. Prior OPM approval is not required." Showing individual Postings is fine, but it covers only US federal jobs.
- **USAJOBS limits**: no false claims of official status or endorsement, no seal or logo, and "Applications must be submitted according to the official instructions in the applicable job announcement." Consumers must keep registration "current and accurate" and verify "current job-announcement information against the official announcement". Attribution is encouraged, not required. Revocation "does not prohibit lawful reuse of Public Data already obtained".

### Not verified

- Adzuna's general [Terms and Conditions](https://www.adzuna.co.uk/terms-and-conditions.html), which bind API users. The page returned 403 to every fetch, as did the contact page. Someone should read them in a browser, and they may add limits.
- Adzuna's licence price, process and rules. Only Adzuna can answer.
- Whether Adzuna's "Publishing Adzuna ad listings" permission covers a company's tool despite the Commercial use section, what "leads" means, and whether `salary_is_predicted` figures count as Jobsworth estimates. **Adzuna must confirm.**
- Whether Arbeitnow's section 11 overrides section 2 for API users, and whether a screen for signed-in CSMs is "public display". **Arbeitnow must confirm.**
- Whether unpaid company use is a "commercial purpose" under Arbeitnow's Berlin-law terms, and what rights employers keep in advert text. **A lawyer must confirm.**
- Whether Arbeitnow's or Adzuna's terms allow sending Posting text to an LLM provider, or how long it may be cached. Neither addresses it directly.
- When Adzuna's 14 days began for this project, and how the existing keys were registered.
