// Wire values stay raw slugs and codes; these are only what a reader sees.
const CATEGORIES: Record<string, string> = {
  "accounting-finance-jobs": "Accounting & Finance Jobs",
  "admin-jobs": "Admin Jobs",
  "consultancy-jobs": "Consultancy Jobs",
  "creative-design-jobs": "Creative & Design Jobs",
  "domestic-help-cleaning-jobs": "Domestic Help & Cleaning Jobs",
  "engineering-jobs": "Engineering Jobs",
  "healthcare-nursing-jobs": "Healthcare & Nursing Jobs",
  "hospitality-catering-jobs": "Hospitality & Catering Jobs",
  "hr-jobs": "HR & Recruitment Jobs",
  "it-jobs": "IT Jobs",
  "legal-jobs": "Legal Jobs",
  "logistics-warehouse-jobs": "Logistics & Warehouse Jobs",
  "maintenance-jobs": "Maintenance Jobs",
  "manufacturing-jobs": "Manufacturing Jobs",
  "pr-advertising-marketing-jobs": "PR, Advertising & Marketing Jobs",
  "property-jobs": "Property Jobs",
  "scientific-qa-jobs": "Scientific & QA Jobs",
  "social-work-jobs": "Social Work Jobs",
  "teaching-jobs": "Teaching Jobs",
  "trade-construction-jobs": "Trade & Construction Jobs",
}

export const categoryName = (slug: string) => CATEGORIES[slug] ?? slug

const regions = new Intl.DisplayNames(["en"], { type: "region" })

export function countryName(code: string): string {
  try {
    return regions.of(code.toUpperCase()) ?? code.toUpperCase()
  } catch {
    return code.toUpperCase() // a code Intl rejects shows as typed
  }
}
