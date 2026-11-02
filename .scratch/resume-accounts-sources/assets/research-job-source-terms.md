# Job source terms for CSM use: research notes

Read 2026-11-02 for [ticket 27](../issues/27-research-job-source-terms-for-csm-use.md). This is one reader's reading of public pages, not legal advice. Nobody was contacted and nothing was signed up for.

Quotes come from the raw HTML of each page, with line wrapping removed. None of the three terms pages shows a last-updated date, and all three say the terms can change, so reread them before relying on this.

## Arbeitnow

Sources, all read 2026-11-02:

- Terms: <https://www.arbeitnow.com/terms>
- API blog post: <https://www.arbeitnow.com/blog/job-board-api>
- Live API `meta.terms`: <https://www.arbeitnow.com/api/job-board-api?page=99>
- Imprint: <https://www.arbeitnow.com/imprint>

Who it is: the imprint names one person, Adithya Srinivasan, in Berlin, with a German VAT number. The site also sells job ads.

### Clauses

Section 2, Use License:

> Permission is granted to temporarily download one copy of the materials (information or software) on arbeitnow's website for personal, non-commercial transitory viewing only. This is the grant of a license, not a transfer of title, and under this license you may not:
>
> modify or copy the materials;
>
> use the materials for any commercial purpose, or for any public display (commercial or non-commercial);
>
> attempt to decompile or reverse engineer any software contained on arbeitnow's website;
>
> remove any copyright or other proprietary notations from the materials; or
>
> transfer the materials to another person or "mirror" the materials on any other server.
>
> This license shall automatically terminate if you violate any of these restrictions and may be terminated by arbeitnow at any time. Upon terminating your viewing of these materials or upon the termination of this license, you must destroy any downloaded materials in your possession whether in electronic or printed format.

Section 11, API:

> The API is provided by us on an "as is" and "as available" basis without any warranties of any kind, and we expressly disclaim any and all warranties, whether express or implied, including the implied warranties of fitness for a particular purpose, and non-infringement. You acknowledge that we do not warrant that the APIs will be uninterrupted, timely, secure, or error-free.
>
> You also agree to providing a link back to Arbeitnow.com on your platform.
>
> We may revoke the permission to use API at any time.

Section 7: "arbeitnow may revise these terms of service for its website at any time without notice."

Section 8: "These terms and conditions are governed by and construed in accordance with the laws of Berlin and you irrevocably submit to the exclusive jurisdiction of the courts in that State or location."

API `meta.terms`: "This is a free public API for jobs, please do not abuse. I would appreciate linking back to the site. By using the API, you agree to the terms of service present on Arbeitnow.com"

Blog: "I offer a custom, private, tailored API endpoint for you for a monthly fee. Reach out to me via email - contact at arbeitnow.com with what you would like, your traffic and other useful information."

### Reading

Two readings are both reasonable:

- **Section 2 governs API data.** `meta.terms` binds API users to the whole terms, and section 11 doesn't say it replaces section 2. Then copying, commercial use, public display and transfer are all barred.
- **Section 11 stands alone for the API.** Section 2 is written about viewing the website. A link back "on your platform" only makes sense if API data appears on someone else's platform, and the blog pitches the API for side projects and aggregators. Then a CSM tool is fine with a link back.

The terms don't choose between them, and only Arbeitnow can. Neither reading has any clause that expressly permits commercial use of the free API.

Why [ticket 10](../issues/10-what-arbeitnow-does-in-the-gateway.md) item 5 no longer holds:

| Ticket 10's reason | With a CSM |
| --- | --- |
| Free and non-commercial | A company serves customers with it. Whether unpaid company use is a "commercial purpose" is not settled by the text, and is a question for a lawyer. |
| No ads | Section 2 doesn't mention ads. |
| Stats and links, not republished descriptions | Matches show individual Postings: title, company, skills and a link. Section 2 bars public display even when non-commercial. Whether a screen limited to signed-in CSMs is "public" is unclear, but a Customer may receive the list. |

Other things that touch the plan:

- "transfer the materials to another person" may reach sending descriptions to OpenRouter's model providers, and passing Matches to a Customer.
- "copy" and "mirror" may reach the snapshot and any L2 or saved Match copy.
- Permission is revocable at any time with no notice period, and the terms can change without notice.

### If Arbeitnow says yes

- Get it in writing, naming the use: a company's CSMs, on behalf of job seekers, signed in, showing individual Postings, with or without payment.
- Link back on the platform. Ticket 10 item 6 already does this.
- Keep Posting URLs pointing at arbeitnow pages. Show no full descriptions unless the permission covers them.
- Keep the "revoked" path: drop the source and delete its stored Postings.

The paid private endpoint is the obvious fallback. Its price and licence aren't published.

## Adzuna

Sources, all read 2026-11-02:

- API terms: <https://developer.adzuna.com/docs/terms_of_service>
- Contact link from those terms: <https://www.adzuna.co.uk/jobs/contact-us.html> (blocked, returned 403)
- General terms the API terms incorporate: <https://www.adzuna.co.uk/terms-and-conditions.html> (blocked, returned 403; also 403 on adzuna.com and through the Wayback Machine)

### Clauses

Opening: "Adzuna API users agree to abide by the following conditions and Adzuna's general Terms and Conditions. Adzuna has absolute discretion over granting access to users."

Permitted Use:

> The Adzuna API may be used for:
>
> Personal job search
>
> Publishing Adzuna ad listings
>
> Publishing Jobsworth salary estimates
>
> Personal and academic research
>
> Any other use, including commercial analysis, resale of data, and sales prospecting or lead generation, requires our written agreement.

Access and limits: "Every registered API user receives a free API key immediately, with no payment details required. The free tier is intended for evaluating the API." and "Paid plans are available for personal and academic use at higher volumes. The plans available to you, and their limits, are shown in your account. We may vary limits from time to time."

Commercial use:

> Any use of the Adzuna API by a commercial, government or academic organisation, including any affiliates or individuals, is permitted subject to a 14 day trial period. This period is strictly for the purpose of validating the general coverage and quality of the data in addition to usability testing. It may not be used in its original format or in aggregation (including but not limited to vacancy counts, average salaries etc) to deliver any ongoing work or research, apart from the purpose stated prior, without written consent.
>
> After the trial period ends, and for any use in a product or service that generates revenue or leads, a licence agreement is required. Contact us here for more details.

Partnerships: "We are very happy to increase limits well beyond our standard plans where there is mutual commercial benefit - our biggest API users do millions of hits per day! If you are driving substantial traffic to Adzuna listings, or there is a clear commercial fit, get in touch."

Attribution:

> Publishing Adzuna ad listings: An API user shall label each displayed advert with the phrase "Adzuna" at least 116 X 23 pixels in size, wherein the word "Adzuna" shall be hyperlinked to http://www.adzuna.co.uk or the relevant local domain

> Publishing Jobsworth salary estimates: An API user shall label every Jobsworth salary estimate that they publish with an icon at least 20 x 20 pixels in size and the word "Adzuna Jobsworth". Both elements will link to http://www.adzuna.co.uk/jobs/salary-predictor.html. An API user will add the following mouseover text to these links: "Salary estimate powered by Adzuna Jobsworth"

> Personal or academic research: An API user shall acknowledge Adzuna as the source of all salary and vacancies data wherever it is published. References should refer to: "The Adzuna API" and link to http://www.adzuna.co.uk/ or the relevant local domain.

Termination: "Either party may terminate this Agreement at any time. [...] Upon termination of this agreement, for any reason and by either party, an API user shall immediately remove all insertion codes and data acquired from Adzuna from all pages of its web sites."

Third parties: "An API user agrees to direct all queries via Adzuna. Any attempt to contact a third party, even where they provide listings content, will be considered a breach of these terms and conditions. If an API user contacts a third party content provider their access to the API will be revoked immediately."

Accounts: "Creation of multiple accounts for a single entity or individual will immediately be considered misuse and a breach of these terms and conditions."

Changes: "Adzuna reserves the right to change the Terms of Service at any time."

### Reading

- **Payment doesn't decide it.** The trial clause covers "Any use" by a commercial organisation. A licence is needed "After the trial period ends, and for any use in a product or service that generates revenue or leads". The "and" gives two triggers, and an unpaid tool at a company still meets the first.
- **The HLD undersells it.** HLD line 178 says "Commercial use beyond a 14-day evaluation needs a licence". The text is narrower still: the 14 days cover only validating coverage and quality and usability testing, and bar delivering "any ongoing work". A pilot with real Customers looks outside the trial from day one.
- **Briefs are caught too.** "commercial analysis" needs written agreement, and the trial clause names "vacancy counts, average salaries". This isn't only about Matches.
- **"Publishing Adzuna ad listings" doesn't rescue it.** It's a listed use, and API users are "encouraged to publish", but the Commercial use section applies to any use by a commercial organisation. A lawyer or Adzuna should confirm how the two sections fit together. "Personal job search" reads as someone searching for themselves, not a CSM working for many people.
- **"Leads" is undefined.** A job seeker sent to an advert might or might not count.
- **Licence process and price.** The only published route is the "Contact us here" link and "get in touch" under Partnerships. No licence price is published, and the paid plans are stated to be "for personal and academic use", so they aren't a route. A G-Cloud listing for Adzuna Intelligence (<https://www.applytosupply.digitalmarketplace.service.gov.uk/g-cloud/services/211603942615607>) is a separate analytics product, which Adzuna stopped offering on 8 October 2026 per that page, so it tells us nothing about API licence terms.

### Display differences for individual Postings

| Use | Attribution the terms ask for | What the repo does today |
| --- | --- | --- |
| Each displayed advert | An "Adzuna" label, at least 116 x 23 px, hyperlinked, on every advert | Nothing per advert |
| Jobsworth estimate | Icon at least 20 x 20 px, "Adzuna Jobsworth", links, mouseover text | Nothing. Whether search's `salary_is_predicted` values count as Jobsworth estimates isn't stated |
| Personal or academic research | "The Adzuna API", linked, wherever published | `"Jobs data provided by The Adzuna API"` in Run Notes (`brief/nodes.py`), with no link |

The one-line footer in [ticket 10](../issues/10-what-arbeitnow-does-in-the-gateway.md) item 6 follows the research form. It doesn't satisfy the per-advert rule for the Match list in [ticket 20](../issues/20-resume-profile-and-sign-in-screens.md). A licence may set different rules, so settle this after the licence.

### Obligations that shape the design

- Removal on termination means stored Adzuna data must be findable and deletable by source, in Run history and saved Matches too. The clause says "all pages of its web sites", and whether it reaches stored copies that aren't displayed is unclear.
- The terms say nothing about cache length, or about sending Postings to an LLM provider. Ask.
- The third-party clause may conflict with the job itself: a CSM contacting an employer found through an Adzuna listing could be read as contacting a "third party content provider". A normal application is probably not what it means, but get that in writing.
- One account per entity: all CSMs at a company share one key and one quota. HLD's 25 calls a day won't support that, and neither do the limits of a free tier "intended for evaluating the API".

## USAJOBS

Sources, all read 2026-11-02:

- API terms: <https://developer.usajobs.gov/guides/terms-of-service> (the same text appears in the key request page, <https://developer.usajobs.gov/APIRequest/>; `/guides/terms-of-use` redirects here)
- Rate limits: <https://developer.usajobs.gov/guides/rate-limiting>
- Website terms: <https://usajobshelp.opm.gov/hc/en-us/articles/55069845301267-USAJOBS-terms-and-conditions>, dated September 03, 2026

### Clauses

Section 2:

> Consistent with 44 U.S.C. §§ 3502 and 3506(b)(6), OPM provides Public Data under an open license. Public Data may be copied, stored, reformatted, adapted, analyzed, published, redistributed, and used for lawful commercial or noncommercial purposes. Prior OPM approval is not required.

> API registration and credentials govern access to the API Service, not lawful downstream reuse of Public Data. Public Data does not include content separately identified in accompanying metadata or notice as subject to a specific legal or third-party intellectual-property restriction.

> OPM encourages users to identify USAJOBS as the source, link to the current official job announcement, include the date on which the data was retrieved, and disclose that an unofficial product or service is not operated, sponsored, approved, or endorsed by OPM.

> API Consumers and downstream users may modify, summarize, analyze, or combine Public Data but may not:
>
> Falsely present modified information as official or unaltered government information;
>
> Falsely represent that a product or service is operated, sponsored, approved, or endorsed by OPM or another federal agency;
>
> Use an official seal, logo, or insignia except as authorized by law, or otherwise use an agency name or identifier in a manner likely to falsely imply government affiliation;
>
> Falsely represent that an application has been transmitted to or received by USAJOBS or a hiring agency; or
>
> Engage in phishing, fraud, deceptive collection of applicant information, or other unlawful conduct.
>
> Applications must be submitted according to the official instructions in the applicable job announcement.

Section 1: "To request or maintain API credentials, an API Consumer must provide current and accurate registration and contact information."

Section 3: "Public job announcements may include names and business contact information for agency points of contact."

Section 4, among the things a consumer may not do: "Violate the legal rights of others, including rights of privacy and publicity;", "Share or transfer API credentials or permit their use by an unauthorized person;", "Circumvent authentication requirements, rate limits, or other technical safeguards;"

Section 6: "OPM may establish or revise rate limits, transaction quotas, response-size limits, and other technical limits", which "will be described in the USAJOBS Developer documentation". That page lists "Maximum of 10,000 rows per query" and "Maximum of 500 rows per page".

Section 7: "Suspension or revocation affects access to the API Service and does not prohibit lawful reuse of Public Data already obtained."

Section 10: "API Consumers are responsible for protecting their own systems and for verifying current job-announcement information against the official announcement and application instructions."

Section 12: "Separate terms may govern the use of other USAJOBS services." The website terms limit the site itself to "job searching, applying for jobs, updating and completing a USAJOBS profile, managing documents and other standard uses available to all users on USAJOBS.gov", so stay on the API and don't automate the website.

A search result summary of the same site described an older-sounding ban on redistribution and a need for written approval. The current pages read on this date say the opposite. Trust the pages.

### Must do

- Keep registration accurate. The key request form asks for "Company or Agency" and how they "will use the jobs". If the existing key was registered for a personal or assessment project, update it for the CSM use.
- Keep the key server-side and shared only with authorised people.
- Never imply federal endorsement, and use no OPM seal or logo.
- Don't present a summarised Posting as official text.
- Don't claim to have applied for anyone. Send Customers to the announcement's own instructions. This matters if a future feature tracks applications.
- Tell the CSM to check the live announcement before acting on it.
- Don't show agency contact names without need, because section 4 protects privacy rights.

Encouraged, not required, and cheap: name USAJOBS, link the announcement, show the retrieval date, and state non-affiliation. The current repo requires no USAJOBS attribution in `ATTRIBUTION`, which the terms allow.

## Paid or unpaid

| Source | Company tool, nobody pays | Customers or companies pay |
| --- | --- | --- |
| Arbeitnow | Needs permission. "Commercial purpose" is unclear, and display is barred either way under section 2 | Needs permission, and the free API looks a poor fit |
| Adzuna | Needs a licence after a narrow 14-day trial | Needs a licence, by both triggers |
| USAJOBS | Allowed with conditions | Allowed with conditions, "lawful commercial or noncommercial purposes" |

## Questions to send, if the user chooses

Nothing has been sent. Each message should describe the real use: a company's CSMs sign in, keep job seekers as Customers, upload their resumes, and see ranked Postings and market Briefs.

Arbeitnow (contact at arbeitnow.com):

1. Does section 11 replace section 2 for API users, or do both apply?
2. Is this use allowed on the free API? If not, what would the private endpoint cost and permit?
3. May we keep the feed for 24 hours in a server cache, and store title, company, location and link with a saved Match?
4. May descriptions go to an LLM provider for skill extraction, and may a CSM pass Matches to a Customer?
5. Is a link in the footer enough, or does each Posting need one?

Adzuna (contact form linked from the terms):

1. What licence covers this use, and at what price and call volume? Does it differ if nobody pays?
2. Does it cover aggregated stats in market Briefs as well as individual Postings?
3. What attribution is required per Posting, and does it apply to `salary_is_predicted` figures?
4. How long may Postings be stored, for instance in a Customer's saved Matches, and may they go to an LLM provider?
5. Does the third-party clause stop a CSM or Customer contacting an employer about a listing?
6. Is using the API in development and test covered, and when did the 14 days start?

## Lawyer or source must confirm

- Whether Arbeitnow's section 2 applies to API use, and whether unpaid company use is a "commercial purpose" under its Berlin-law terms: Arbeitnow, or a lawyer for the legal meaning.
- How Adzuna's Permitted Use and Commercial use sections fit together, and what "leads" means: Adzuna.
- Adzuna's general Terms and Conditions, which bind API users and couldn't be read here: a person with a browser, then a lawyer.
- Rights in the adverts themselves, since both aggregators republish employers' text: a lawyer. USAJOBS excludes content carrying a separate restriction.
- Any contract terms between the CSM's company and its customers.

## Method

`curl` to a scratch directory, a small stdlib HTML-to-text script, and reading the output. WebFetch was used only as a first pass, because its summaries can't be quoted. The response bodies from the blocked pages were CloudFront error pages. No account or key was used.
