# Research: holding Customers' personal data

Type: research
Status: resolved
Assignee: smayankulkarni05
Blocked by: none

## Question

What does it take to hold job seekers' resumes and search history when a CSM uploads them and the person never signs in?

- GDPR and UK GDPR, since Arbeitnow's countries put EU and UK job seekers in scope: who is the controller, the lawful basis for a CSM uploading someone's resume, what the person must be told, and rights of access, erasure and export when they have no login.
- How long recruitment and resume data may reasonably be kept, using regulator guidance such as the ICO or CNIL.
- Does building up a profile from a person's Runs, or ranking jobs for them, count as profiling or automated decision-making that adds duties?
- Sub-processors holding this data: OpenRouter and its providers (does `data_collection: "deny"` or `zdr: true` help?), LangSmith, Neon and Render. Check their current data-processing terms and regions. [Research: reading resume files](08-research-reading-resume-files.md) covers the mechanics of keeping resumes out of traces, so start from there.
- From that, the smallest set of features the product must have, such as delete-a-Customer and a retention limit, for the LLD to pin down.

This is reading and reporting, not legal advice. Say where a lawyer must confirm. Capture findings in this ticket's Answer, with long notes in `../assets/`.

## Answer

**Outcome:** the user said on 2026-11-02 that only test resumes will be used, never real people's. Three features stay, because they are cheap and useful anyway: deleting a Customer with everything stored about them, the CSM seeing, editing and removing what was learned, and never extracting or learning sensitive traits. The rest below is a record, and applies only if real resumes are ever used.

Researched 2026-11-02; all sources read that day. Long notes and every source: [research-customers-personal-data.md](../assets/research-customers-personal-data.md).

**This isn't legal advice.** It's a non-lawyer's reading of the texts. A lawyer must confirm the items listed under "A lawyer must confirm" before any real person's resume goes in.

### Recommendation

- **Decide first: fictional data, or real Customers?** With fictional data, almost none of this applies. Any real resume brings all of it, and "personal project" doesn't get round that, because holding strangers' resumes for a CSM's work isn't a "purely personal or household activity". Until a lawyer has confirmed the list below, seed only fictional Customers.
- **Roles:** the organisation employing the CSM is the controller, not the CSM personally. If the tool is sold to other firms, its operator is their processor. The vendors are processors or sub-processors.
- **Lawful basis:** contract or steps the person asked for, when they engaged the CSM. Consent for keeping them on file after the engagement. An upload about someone who doesn't know and didn't ask has no comfortable basis, so the product makes the CSM state the relationship first.
- **Telling the person:** the CSM gives them a notice, at collection or within one month at the latest. They need no login, and requests come through the CSM, answered within one month.
- **Retention:** 24 months from the last real contact at most, CNIL's ceiling. The ICO gives no number I could find, and wants a period set and stated.
- **Profiling:** learned preferences and matching are very likely profiling. They stay outside Art 22 only if a CSM genuinely reviews the output and can override it.
- **Transfers:** US hosting is allowed with safeguards, and nothing read makes EU hosting mandatory. Rely on each vendor's SCCs and UK Addendum plus a transfer risk assessment. Don't rely on the Data Privacy Framework alone, since its appeal is pending. Regions are fixed at creation on Render, Neon and LangSmith, so decide before real data exists.

Features the LLD must pin down:

| # | Feature | Marked |
|---|---|---|
| 1 | **Basis and notice on the Customer record:** how the person came to the CSM (direct or third party), the lawful basis and the date notice was given. No upload until they're filled in | Required |
| 2 | **Delete a Customer:** a hard delete reaching resume text, profile, Store memories, Run checkpoints, run registry and any replay cache, with an alert before Neon's 1 GB cap, past which deletes themselves fail | Required |
| 3 | **Export a Customer:** one JSON file holding everything kept about them | Required |
| 4 | **Retention limit:** a CSM-set `last_contact_at`, and automatic deletion at 24 months at most, including for a departed CSM's Customers. New Runs don't reset it | Required |
| 5 | **Correct the profile:** the CSM can see, edit and remove extracted facts and learned preferences | Required |
| 6 | **A human decides on Matches:** a reason shown for each ranking, low-ranked Postings still visible, CSM override, nothing sent automatically | Required |
| 7 | **No sensitive traits:** never extract or learn health, religion, ethnicity, union membership, orientation, age or gender | Required |
| 8 | **Private LLM routing for Customer data:** `zdr: true`, a provider allowlist through `only`, contact details redacted, failing closed rather than falling back. `data_collection: "deny"` alone isn't enough | Required |
| 9 | **Customer data stays out of LangSmith, logs and the replay cache**, in every node that sees it, not just the resume upload | Required |
| 10 | **No Customer identity or resume content in a Market Brief**, which goes to a Client | Required |
| 11 | Frankfurt regions (Render, Neon `aws-eu-central-1`, LangSmith EU) if real EU or UK Customers are expected | Advisable |
| 12 | A 12-month default within the 24-month ceiling, with a warning before deletion | Advisable |
| 13 | A log of Customer exports and deletions holding IDs and dates, no personal data | Advisable |
| 14 | A notice template the CSM can copy and send | Advisable |

Not features, but needed before real data: a DPIA, a record of processing, signed or accepted DPAs, a transfer risk assessment, a privacy notice, and an Art 27 representative if the operator is outside the EU and UK and Art 3(2) applies.

**A lawyer must confirm:**

- Who the controller is, and where it's established. That decides Art 3(2), Art 27 and whether vendor calls are restricted transfers.
- The lawful basis for each way a resume can arrive.
- Whether a stray health or religion mention on a resume brings the store under Art 9.
- Whether matching is "high-risk" under EU AI Act Annex III point 4(a). This could outweigh everything else here.
- Whether the EU approach to Art 22 also satisfies the UK's Arts 22A to 22D.
- Whether 24 months suits a job seeker's own service. CNIL's figure is for recruiters' candidate pools.
- The transfer risk assessment, and Swiss law, since Arbeitnow covers CH and it wasn't researched.

### Key findings

- **Scope:** the GDPR excludes only a natural person's "purely personal or household activity" ([Art 2(2)(c)](https://gdpr-info.eu/art-2-gdpr/)). Art 3(2)(a) reaches non-EU controllers offering services to people in the Union, "irrespective of whether a payment of the data subject is required" ([Art 3](https://gdpr-info.eu/art-3-gdpr/)).
- **Controller:** "usually the organisation as such, and not an individual within the organisation" ([EDPB 07/2020](https://www.edpb.europa.eu/system/files/documents/2023-10/EDPB_guidelines_202007_controllerprocessor_final_en.pdf)). CNIL treats an agency building its own candidate pool as a controller ([guide](https://www.cnil.fr/sites/cnil/files/atoms/files/guide_referentiel_recrutement.pdf)).
- **Basis:** CNIL accepts contract when "le candidat ... est à l'origine de la démarche", and asks for "libre, spécifique, explicite et univoque" consent for CV pools (same guide).
- **Notice:** "at the latest within one month" for data from a third party ([Art 14](https://gdpr-info.eu/art-14-gdpr/)). The disproportionate-effort exemption is hard to claim, since the CSM can reach the person.
- **Rights:** answers are due "within one month of receipt of the request" ([Art 12](https://gdpr-info.eu/art-12-gdpr/)). Portability covers provided data in a "structured, commonly used and machine-readable format" ([Art 20](https://gdpr-info.eu/art-20-gdpr/)).
- **Retention:** "Jusqu'à 2 ans à compter du dernier contact" ([CNIL reference, 2026](https://www.cnil.fr/sites/default/files/2026-04/referentiel_durees_de_conservation_gestion_des_ressources_humaines.pdf)); five years "est en principe excessive" (guide). The ICO's AI audit says indefinite retention is unlikely to comply ([ICO](https://ico.org.uk/media2/migrated/4031620/ai-in-recruitment-outcomes-report.pdf), search excerpt only).
- **Profiling:** Art 4(4) names "performance at work" and "personal preferences" ([Art 4](https://gdpr-info.eu/art-4-gdpr/)). Oversight must be "meaningful, rather than just a token gesture" ([WP251](https://ec.europa.eu/newsroom/article29/redirection/document/49826)). CNIL warns that low-ranked candidates can be "de facto exclus" by a ranking tool (guide), which is why low-ranked Postings stay visible.
- **OpenRouter:** the [DPA of 26 Aug 2026](https://openrouter.ai/assets/data-processing-agreement.pdf) forms part of its Terms and includes SCCs and a UK Addendum. `zdr: true` is stronger than `data_collection: "deny"`, but listing "does not constitute OpenRouter's guarantee", and neither flag controls country ([provider selection](https://openrouter.ai/docs/guides/routing/provider-selection)). `eu.openrouter.ai` fails closed, on the Business plan with no minimum and an 8% fee ([EU routing](https://openrouter.ai/business/eu)).
- **Our routing today:** `kernel/llm.py:232` sends `sort: "price"` with no privacy filter, so a resume would go to the cheapest provider, including one that retains or trains.
- **LangSmith:** free plans are "AS IS" without "data retention rights", and the [Terms](https://www.langchain.com/terms-of-service) don't say whether the DPA covers them. Deletes finish "within 6 hours or sooner" ([purging](https://docs.langchain.com/langsmith/data-purging-compliance)). The tracing trap in [ticket 08](08-research-reading-resume-files.md) applies to every node that sees Customer data.
- **Neon:** Frankfurt and London exist, but "You cannot change the region" ([regions](https://neon.com/docs/introduction/regions)). Deleted data stays restorable for up to 6 hours on Free, and past the cap writes fail, "including deletes" ([plans](https://neon.com/docs/introduction/plans)).
- **Render:** a GDPR DPA is available to all workspaces ([compliance](https://render.com/docs/certifications-compliance)). Frankfurt exists, but regions can't be changed later ([regions](https://render.com/docs/regions)).
- **Vercel threatens the plan if this becomes real work:** Hobby "restricts users to non-commercial, personal use only" ([Hobby](https://vercel.com/docs/plans/hobby)), and commercial includes "a paid employee or consultant writing the code" ([fair use](https://vercel.com/docs/limits/fair-use-guidelines)). The [DPA](https://vercel.com/legal/dpa) names "Enterprise and Pro plans". [Ticket 07](07-research-signing-in-across-vercel-and-render.md)'s rewrite sends resumes through Vercel, so it's a processor. Either pay for Pro ($20 a seat a month) or serve the SPA from Render and retest ticket 07's cookie and SSE design.
- **Transfers:** the EU-US framework's appeal is [pending as C-703/25 P](https://eur-lex.europa.eu/eli/C/2025/6610/oj). The UK bridge needs the recipient on the list and registered for that data type ([ICO](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/international-transfers/adequacy-regulations/how-does-the-uk-extension-to-the-eu-us-data-privacy-framework-work/), search excerpt only).

### Not verified

- **Render's actual DPA terms.** The public page returned no text and the Document Center needs a login.
- **Any vendor's Data Privacy Framework listing.** The participant list wouldn't load. Vercel's and Neon's claims come from their own pages.
- **The appeal's status after June 2026.** The latest source is a secondary report, the court's page gave no text, and one undated French headline suggests a verdict, which I couldn't confirm.
- **ICO guidance.** All `ico.org.uk` pages refused fetching, so ICO points rest on search excerpts, including its recruitment ADM guidance and its DPIA statement.
- **The UK's Arts 22A to 22D wording.** The statute page came back empty. The 5 February 2026 commencement rests on an excerpt of SI 2026/82 and law-firm summaries.
- **EDPB Guidelines 05/2021** on what counts as a transfer. Only the landing page was read.
- **Whether the Neon DPA is current.** It still points to `neon.tech`, and a search tool flagged it as old.
- **Whether LangSmith's DPA covers free accounts, and whether trace deletion is available on the free plan.**
- **Whether model providers count as OpenRouter's listed sub-processors.** Only five names were visible at its trust centre.
- **Where each ZDR endpoint is located.** Only the first 9% of the list was read, and most entries carry no region. Also untested: whether strict `json_schema` still works once `zdr: true` and `only` are set on the cheap models.
- **Free-plan availability of Frankfurt** on Render and Neon. Their region pages don't say.
- **AI Act dates**, and Swiss, Indian or other national law.
