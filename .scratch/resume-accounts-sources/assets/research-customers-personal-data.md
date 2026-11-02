# Research notes: holding Customers' personal data

Notes for [Research: holding Customers' personal data](../issues/28-research-holding-customers-personal-data.md). Everything was read on 2026-11-02 unless marked otherwise. This is reading and reporting by a non-lawyer, not legal advice.

How each source was read:

- **Read**: fetched the page or extracted the PDF's text.
- **Search excerpt**: the page refused fetching (ICO returns 403), so only the search tool's excerpt was seen. Treat these as weaker, and open the page before relying on them.

## 1. Does the GDPR apply, and who is the controller?

**"Personal project" isn't an exemption by itself.** [decisions.md](../decisions.md) records the user calling this a personal project, and that settled the job source licences. Data protection turns on something else. The GDPR excludes only processing "by a natural person in the course of a purely personal or household activity" ([Art 2(2)(c)](https://gdpr-info.eu/art-2-gdpr/)), and it still applies to those "which provide the means for processing personal data" for such activities ([Recital 18](https://gdpr-info.eu/recitals/no-18/)). Holding strangers' resumes for a CSM's work doesn't look purely personal or household. Unpaid doesn't help either: Art 3(2)(a) applies "irrespective of whether a payment of the data subject is required".

So there are two different worlds, and the product should pick one out loud:

- **Fictional or the developer's own data only:** nearly everything here is moot. No real third party, no controller problem, and Vercel Hobby stays arguable.
- **Any real Customer's resume:** everything here applies, paid or not.

**Scope.** Art 3(1) covers an establishment in the Union. Art 3(2) covers controllers elsewhere when processing relates to "the offering of goods or services, irrespective of whether a payment of the data subject is required" to people in the Union, or "the monitoring of their behaviour" there ([Art 3](https://gdpr-info.eu/art-3-gdpr/)). A non-EU operator whose CSMs serve job seekers in Germany or France plausibly meets Art 3(2)(a). Where it does, Art 27 requires a written EU representative unless processing is occasional and low risk ([Art 27](https://gdpr-info.eu/art-27-gdpr/)). The ticket doesn't say where the operating company is established, and the answer changes both this and the transfer analysis. **A lawyer must confirm.**

**Controller.** A controller "determines the purposes and means"; a processor processes "on behalf of the controller" ([Art 4](https://gdpr-info.eu/art-4-gdpr/)). The controller is "usually the organisation as such, and not an individual within the organisation", and employees are "persons acting under the authority of the controller" ([EDPB Guidelines 07/2020, final version](https://www.edpb.europa.eu/system/files/documents/2023-10/EDPB_guidelines_202007_controllerprocessor_final_en.pdf)).

Reading that across to this product:

| Set-up | Controller | Talent Market Scout's operator |
|---|---|---|
| One company runs the tool for its own CSMs | That company | Same company, so no separate processor |
| Tool sold to other CSM firms | Each firm, for its own Customers | Processor to each firm, which needs an Art 28 contract |
| A solo CSM working for themselves | The CSM | Processor, if someone else runs the tool |

The nearest regulator example is the recruitment agency. CNIL says an agency "peut être qualifié de responsable de traitement" for a candidate pool it builds for its normal placement business, and that an agency or employer who pulls CVs into its own base becomes a controller ([CNIL recruitment guide, 30 Jan 2023](https://www.cnil.fr/sites/cnil/files/atoms/files/guide_referentiel_recrutement.pdf)).

## 2. Lawful basis for a CSM uploading a resume

[Art 6(1)](https://gdpr-info.eu/art-6-gdpr/) offers three candidates:

| Basis | When it fits | Regulator's view |
|---|---|---|
| (b) contract or steps "at the request of the data subject" | The person engaged the CSM's firm to help them | CNIL accepts this for a temp agency's pool, because "c'est en effet le candidat qui est à l'origine de la démarche" |
| (a) consent | A longer-lived pool beyond the engagement | CNIL now prefers this for CV pools: "libre, spécifique, explicite et univoque". It warns that consent can't support recruitment processing where refusing could affect someone's chances |
| (f) legitimate interests | The person has no contract and didn't ask | Needs a balancing test and the person can object. CNIL moved away from this for pools. Its 2026 retention reference still accepts "sauf opposition de leur part" |

**The case that fails:** a CSM uploads the resume of someone who doesn't know and never asked. I found no regulator text supporting that, and legitimate interests would be weak. So the product should make a CSM state the relationship before any upload.

**Special categories.** Resumes can reveal health, religion, union membership, ethnicity or orientation, and processing those "shall be prohibited" unless an Art 9(2) exception applies, such as explicit consent ([Art 9](https://gdpr-info.eu/art-9-gdpr/)). Whether a stray mention on a resume brings the whole store under Art 9 is a question for **a lawyer**. The lazy defence is never to extract or learn such traits.

## 3. What the person must be told

CNIL distinguishes direct collection (the candidate sends the CV to the recruiter) from indirect (from a third party, a website or a colleague) ([CNIL guide](https://www.cnil.fr/sites/cnil/files/atoms/files/guide_referentiel_recrutement.pdf)).

- **Direct**, Art 13: told at collection.
- **Indirect**, Art 14: "within a reasonable period after obtaining the personal data, but at the latest within one month", or at first contact if sooner, or at first disclosure to another recipient if sooner ([Art 14](https://gdpr-info.eu/art-14-gdpr/)). CNIL says the same: "dès que possible" and "au plus tard" one month.
- **"Impossible or disproportionate effort"** in Art 14(5) is hard to claim, because a CSM by definition works for this person and can reach them.

A login isn't needed for any of this. The CSM can hand over a notice, by email or otherwise. The notice should cover the controller, purpose, basis, sub-processors and US transfers, retention, rights and how to complain. CNIL also lists the existence of automated decision-making, "y compris un profilage", "le cas échéant".

## 4. Rights when the person has no login

The rights attach to the person, not to an account. Requests reach the controller through the CSM or the firm's contact address. The answer is due "within one month of receipt of the request", extendable by "two further months where necessary", and the controller may ask for "additional information necessary to confirm the identity" ([Art 12](https://gdpr-info.eu/art-12-gdpr/)).

| Right | Article | What the product needs |
|---|---|---|
| Access | 15 (not re-read) | The whole Customer record can be produced |
| Correction | 16 (not re-read) | Facts and learned preferences can be edited or removed |
| Erasure | [17](https://gdpr-info.eu/art-17-gdpr/) | Delete everywhere. Art 17(1) grounds include "no longer necessary" and withdrawn consent |
| Portability | [20](https://gdpr-info.eu/art-20-gdpr/) | Data the person provided, "in a structured, commonly used and machine-readable format", where the basis is consent or contract |
| Objection | 21 (not re-read) | Applies under legitimate interests. In practice, stop and delete |

One export file and one delete action cover all of these except correction.

**Everywhere a Customer's data will live, so delete has to reach it:** Customer and profile rows, resume text, Store memories, checkpoints of that Customer's Runs, the run registry, the local replay cache if on, any LangSmith traces, and logs.

**Things that can stop a delete actually working:**

- **Neon's change history.** Free projects keep "6-hour limit, capped at 1 GB of change history", so deleted data remains restorable for up to 6 hours ([Neon plans](https://neon.com/docs/introduction/plans)). Short enough to state plainly in the notice.
- **Neon's storage cap.** The same page says that past the 1 GB cap, operations that increase storage fail, "including deletes". An erasure could fail on a full database, so storage needs an alert well before the cap, and Run pruning from [ticket 06](../issues/06-research-durable-storage-for-accounts-and-runs.md) matters here too.
- **LangSmith.** Deletes are "not instant" and "most deletes are hardened within 6 hours or sooner" ([data purging](https://docs.langchain.com/langsmith/data-purging-compliance)). The same page offers delete by metadata key, which only works if a Customer ID was attached. Keeping Customer data out of traces is simpler.

## 5. Retention

| Source | Says | Status |
|---|---|---|
| [CNIL retention reference, HR](https://www.cnil.fr/sites/default/files/2026-04/referentiel_durees_de_conservation_gestion_des_ressources_humaines.pdf) (published 2 Apr 2026, updated 20 May 2026; recruitment rows dated 29 Jan 2026) | CV pool: "Jusqu'à 2 ans à compter du dernier contact avec le candidat non retenu", covering intermediaries "(ex : cabinets de recrutement)" | Recommendation |
| Same | Evidence for discrimination claims: 5 years from filling the post | Rests on French labour code L.1134-5. Applies to employers and intermediaries in a hiring process, and doesn't obviously fit us |
| [CNIL guide](https://www.cnil.fr/sites/cnil/files/atoms/files/guide_referentiel_recrutement.pdf) | Five years for a pool "est en principe excessive"; "n'excède en principe pas deux ans à compter du dernier contact" | Recommendation |
| [CNIL Q&A](https://www.cnil.fr/fr/cnil-direct/question/recrutement-un-employeur-peut-il-conserver-mon-dossier) | "2 ans après votre dernier contact", or longer with formal agreement, once informed and agreed | Guidance |
| [ICO AI recruitment audit, Nov 2024](https://ico.org.uk/media2/migrated/4031620/ai-in-recruitment-outcomes-report.pdf) | Indefinite or over-long retention is unlikely to comply; put periods in contracts and privacy information | Search excerpt |
| [ICO vetting guidance](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/employment/recruitment-and-selection/pre-employment-vetting-of-candidates/) | Destroy vetting data obtained from third parties once recruitment is over | Search excerpt. A different context, about employers vetting candidates |
| [Old ICO Employment Practices Code](https://ico.org.uk/media2/migrated/1064/the_employment_practices_code.pdf) | Destroy vetting data within 6 months | Search excerpt, likely superseded |

**The ICO sets no fixed number that I could find, and CNIL's 2 years is a ceiling, not a target.** It's also measured from the last contact with the person, which isn't the same as last system activity. Running a new Search on a stale Customer mustn't restart the clock, so the CSM has to record the contact date separately.

## 6. Profiling and automated decisions

**Profiling: yes, almost certainly.** Art 4(4) is automated use of personal data "to evaluate" aspects, "in particular to analyse or predict" a person's "performance at work, economic situation, health, personal preferences, interests" ([Art 4](https://gdpr-info.eu/art-4-gdpr/)). Learned preferences and resume-to-Posting matching fit that wording. Profiling on its own isn't prohibited. It brings transparency, accuracy and, under legitimate interests, objection.

**Art 22: avoidable by keeping a real human in the loop.**

- The right is against "a decision based solely on automated processing" with legal or similarly significant effects ([Art 22](https://gdpr-info.eu/art-22-gdpr/)).
- Recital 71's example, as quoted in [WP251 rev.01](https://ec.europa.eu/newsroom/article29/redirection/document/49826), is "e-recruiting practices without any human intervention".
- Human oversight must be "meaningful, rather than just a token gesture" and done by "someone who has the authority and competence to change the decision" (WP251).
- CNIL warns that a ranking tool can become a solely automated decision if humans only ever look at the top: the rest are "de facto exclus du processus" by "le seul fonctionnement du logiciel de tri" ([CNIL guide](https://www.cnil.fr/sites/cnil/files/atoms/files/guide_referentiel_recrutement.pdf)). That example ranks candidates for a job, whereas ours ranks jobs for a person, which is arguably milder. The same logic still applies if the screen silently hides Postings.
- CNIL treats a tool where a human builds the profile and score as not solely automated, but here the LLM builds it, so that comfort doesn't carry over.

So the design needs: the CSM sees why, can see what ranked low, can override, and nothing is sent or applied for automatically.

**UK divergence.** Art 22 was replaced in the UK by Arts 22A to 22D by the Data (Use and Access) Act 2025 s.80. Commencement was 5 February 2026 under [SI 2026/82](https://legislation.gov.uk/uksi/2026/82) (search excerpt; the statute page returned no readable text). The UK permits such decisions more widely, with safeguards including information, challenge and human intervention ([GOV.UK](https://www.gov.uk/guidance/data-use-and-access-act-2025-data-protection-and-privacy-changes)). Meeting the EU rule should also cover the UK, but **a lawyer must confirm**. The ICO's matching [ADM recruitment guidance](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/employment/recruitment-and-selection/automated-decision-making-and-profiling-for-recruitment-and-selection) was blocked; the search excerpt says a DPIA is required for solely or partly automated recruitment decisions.

**DPIA.** Art 35(1) applies where processing is "likely to result in a high risk", and 35(3)(a) names systematic automated evaluation where decisions have significant effects ([Art 35](https://gdpr-info.eu/art-35-gdpr/)). LLM profiling of job seekers from US hosting, on data the person didn't directly enter, makes doing one the safe default. It's a document, not a feature.

**EU AI Act.** [Annex III point 4(a)](https://artificialintelligenceact.eu/annex/3/) lists AI "for the recruitment or selection of natural persons, in particular to place targeted job advertisements, to analyse and filter job applications, and to evaluate candidates" as high-risk. Does a tool helping a job seeker find jobs fall under this? I don't know, and evaluating a person's fit is close enough to ask. Not in the ticket's scope, and the current application dates weren't checked. **A lawyer must confirm**, because high-risk status would add far more than anything in this note.

## 7. Transfers outside the EU and UK

Mechanisms, in the order to rely on them:

1. **SCCs plus the UK Addendum in each vendor's DPA.** They're the stable base, though they bring a transfer risk assessment. The ICO now calls it a "data protection test" and offers a route based on the UK Government's analysis of the US ([ICO TRA](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/international-transfers/completing-a-transfer-risk-assessment/completing-a-tra-using-the-uk-government-s-analysis-us/), search excerpt).
2. **EU-US Data Privacy Framework.** Only for vendors actively listed. It survived the General Court on 3 Sep 2025 (T-553/23), and an appeal is pending as [C-703/25 P](https://eur-lex.europa.eu/eli/C/2025/6610/oj) ([June 2026 report](https://ieu-monitoring.com/editorial/microsoft-backs-eu-commission-in-eu-court-case-on-transatlantic-data-flows-and-privacy/1244467/), secondary). Don't build on it alone.
3. **UK Extension ("data bridge").** The recipient must be active on the DPF list, self-certified to the Extension, and registered for the type of data, HR or non-HR ([ICO](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/international-transfers/adequacy-regulations/how-does-the-uk-extension-to-the-eu-us-data-privacy-framework-work/), search excerpt). It stands independently of the EU decision.

EU to UK flow is fine: the Commission renewed UK adequacy to 27 Dec 2031 ([Hunton](https://www.hunton.com/privacy-and-cybersecurity-law-blog/european-commission-renews-uk-data-adequacy-decisions), secondary).

**Moving regions reduces rather than removes this.** Every vendor here is US-run, so an EU region still leaves US-company access and any account data in the US. Frankfurt regions exist:

| Vendor | EU option | Moving later | On free plan? |
|---|---|---|---|
| [Render](https://render.com/docs/regions) | Frankfurt | "doesn't currently support changing the region" | Not stated |
| [Neon](https://neon.com/docs/introduction/regions) | `aws-eu-central-1`, `aws-eu-west-2` | "You cannot change the region"; new project and migrate | Not stated |
| [LangSmith](https://docs.langchain.com/langsmith/regions-faq) | `eu.smith.langchain.com` | "do not support migration between regions" | Available on every plan |
| [OpenRouter](https://openrouter.ai/business/eu) | `eu.openrouter.ai` | Base URL change | Business plan, no minimum, 8% fee on credits |
| [Vercel](https://vercel.com/docs/functions/configuring-functions/region) | Function region only | Search excerpt says no permanent EU storage | One function region on Hobby |

All of these are fixed at creation, so this is cheap to decide before real data exists and costs a migration afterwards.

I didn't read [EDPB Guidelines 05/2021](https://www.edpb.europa.eu/our-work-tools/our-documents/guidelines/guidelines-052021-interplay-between-application-article-3_en) (final 24 Feb 2023), which define what counts as a transfer. Whether sending data to these vendors is a restricted transfer depends on where the controller is, so **a lawyer must confirm**.

## 8. Sub-processors

### OpenRouter and its providers

- [DPA, updated 26 Aug 2026](https://openrouter.ai/assets/data-processing-agreement.pdf): "forms a part of the Terms of Service", so appears to cover any accepting customer. Customer is controller, OpenRouter is processor. SCC Module 2 under Irish law, plus the UK Addendum.
- By default: "OpenRouter does not store your prompts or responses" unless logging is on ([data collection](https://openrouter.ai/docs/guides/privacy/data-collection)). DPA 2.4(a) commits to deleting inputs and outputs promptly, with an exception "as necessary to address malicious use", and allows automated classification before deletion.
- **`data_collection: "deny"`** means "use only providers which do not collect user data" ([provider selection](https://openrouter.ai/docs/guides/routing/provider-selection)).
- **`zdr: true`** routes only "to endpoints that have a Zero Data Retention policy". That's the stronger flag, so it should replace the `data_collection: "deny"` alone that [ticket 08](../issues/08-research-reading-resume-files.md) recommended.
- **Limits of ZDR:** the DPA says inclusion "reflects the AI Model Provider's published or represented policy" and "does not constitute OpenRouter's guarantee of AI Model Provider compliance" (2.4(b)). In-memory implicit caching still counts as ZDR ([ZDR](https://openrouter.ai/docs/guides/features/zdr)).
- **Neither flag controls country.** The [ZDR endpoint list](https://openrouter.ai/api/v1/endpoints/zdr) gives no country field, only tags such as `wafer/us`. In the first 9% of it, `z-ai/glm-5.3-flash` appears at Particle AI, Wafer (`us`) and InferenceNet (`us`), and DeepSeek flash variants at many providers including SiliconFlow. Pin with `only`, using `/us` endpoints where a slug offers it; the docs warn this "may significantly reduce fallback options".
- **Regional endpoints:** on Business, `eu.openrouter.ai` or `us.openrouter.ai` keeps prompts "processed entirely within that region", and fails closed. It covers Azure, Mistral, Bedrock, Google and Inceptron, 69 models. Whether a cheap model we'd use is among them wasn't checked. The strict contract is DPA Exhibit A, by written election only, and account and abuse metadata stay outside it.
- **Our code today:** [`kernel/llm.py:232`](../../../src/talent_scout/kernel/llm.py) sends `{"require_parameters": True, "sort": "price"}`, with no privacy filter, so the default `allow` means the cheapest provider wins, including one that retains or trains. Fine for public Postings. Not for resumes.
- **Sub-processor list:** Schedule 3 points to [trust.openrouter.ai](https://trust.openrouter.ai/), where only Customer.io, Coinbase, Cloudflare, ClickHouse and Clerk were visible without expanding. Whether model providers count as listed sub-processors is unclear.

### LangSmith

- [DPA v2, 31 Oct 2025](https://www.langchain.com/DPA): SCC Module 2 and UK Addendum, deletion on termination.
- [Terms, 2 Jun 2026](https://www.langchain.com/terms-of-service): s.2.1(C) applies a DPA where the platform processes personal data; s.2.5 gives free plans "AS IS" access without "data retention rights". Whether the DPA covers free accounts isn't stated. s.4.2 says customer data isn't used to train.
- Retention: base 14 days, extended up to 180 ([data purging](https://docs.langchain.com/langsmith/data-purging-compliance)).
- Regions: US, EU, APAC, not movable. Authoritative sub-processor list at [trust.langchain.com](https://trust.langchain.com/subprocessors) (search excerpt: Google Cloud, AWS, Supabase, Anthropic, OpenAI, Baseten, Fireworks and others).
- [Engine](https://docs.langchain.com/langsmith/engine-security), if turned on, sends trace content to further model sub-processors. Keep it off.
- Ticket 08 found that only `ls.tracing_context(enabled=False)` keeps a resume out, and the enclosing traced runnable still logs its input. The same trap applies to every graph node that sees a Customer's profile, findings or Assumptions, not only the resume upload. That's the wider risk this ticket adds.

### Neon

- [DPA](https://neon.com/pdf/DPA.pdf): attaches to the Neon Terms of Service, defines the DPF including the UK Extension, annexes the 2021 SCCs. It still points to `neon.tech`, and a search tool flagged it as old, so its currency is unconfirmed.
- [Security page](https://neon.com/security): "We offer Data Processing Agreements (DPA) and support compliant cross-border data transfers" (search excerpt).
- Compliance on Free rests on those general statements.

### Render

- [Compliance page](https://render.com/docs/certifications-compliance): "complies with the General Data Protection Regulation (GDPR)"; GDPR DPA available to all workspaces, in the dashboard.
- [`render.com/dpa`](https://render.com/dpa) returned no readable terms, and the Document Center needs a login, so **the actual DPA terms were not read**. The page doesn't mention the DPF.
- Application logs live here, so they must stay free of Customer text.

### Vercel: the one that doesn't fit

- [Hobby](https://vercel.com/docs/plans/hobby): "restricts users to non-commercial, personal use only".
- [Fair use](https://vercel.com/docs/limits/fair-use-guidelines): commercial means "for the purpose of financial gain of **anyone** involved in **any part of the production** of the project, including a paid employee or consultant writing the code".
- [DPA, 17 Mar 2026](https://vercel.com/legal/dpa): covers customers on "Enterprise and Pro plans", using 2021 SCCs and the UK addendum. [Terms](https://vercel.com/legal/terms) incorporate a DPA generally, per a search excerpt, so the Hobby position is murky at best.
- [Ticket 07](../issues/07-research-signing-in-across-vercel-and-render.md) proxies `/api` through a Vercel rewrite, so uploaded resumes and every Customer screen pass through Vercel. It's a processor, not merely a static host.

A purely personal, unpaid project with fictional data stays on the right side of Hobby. CSMs serving real Customers as paid work doesn't. Two ways out: Vercel Pro at $20 per developer seat per month, or drop Vercel by serving the SPA from Render. Render's free tier includes static sites, per a [Render article](https://render.com/articles/platforms-with-a-real-free-tier-for-developers-in-2026) (search excerpt). Same-origin hosting there would need re-checking against ticket 07's cookie and SSE design.

## 9. Sources that failed

| Source | What happened |
|---|---|
| All `ico.org.uk` guidance | 403 or Cloudflare challenge; search excerpts only |
| [Render DPA](https://render.com/dpa) and [privacy policy](https://render.com/privacy) | Navigation only, no terms |
| [DPF participant list](https://www.dataprivacyframework.gov/list) | Title only, so no vendor's listing was checked |
| [CJEU case page](https://curia.europa.eu/juris/liste.jsf?num=C-703/25) | No usable text |
| [DUAA s.80](https://www.legislation.gov.uk/ukpga/2025/18/section/80) | Empty, so Art 22A wording unread |

No account was created and nobody was contacted.
