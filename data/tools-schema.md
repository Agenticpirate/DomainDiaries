# Domain Diaries — tools catalog schema

Data files for a curated catalog of **domain-industry tools** (product data, not a website UI).

| File | Format |
|---|---|
| `tools.jsonl` | One JSON object per tool (newline-delimited) |
| `tools.json` | Summary wrapper: `updated_at`, `count`, `categories`, `tools` |

## Fields (`tools.jsonl` / `tools[]`)

| Field | Type | Notes |
|---|---|---|
| `id` | string | Stable slug: `{name-slug}--{registrable-host}` |
| `name` | string | Display name |
| `url` | string | Canonical homepage or tool URL (https) |
| `category` | string | One of the category keys below |
| `description` | string | One-line what it does for domainers |
| `free_tier` | bool \| null | `true` if usable without paying; `false` if paid-only; `null` unknown / credits / freemium unclear |
| `source` | `"seed"` \| `"research"` | Seed = Ravi/Domaining Jul 2026 examples; research = added in catalog pass |
| `verified_at` | string | ISO-8601 timestamp with offset when HTTP check ran (Asia/Calcutta) |
| `http_status` | int | Last observed HTTP status (after redirects). `403` often means Cloudflare/WAF bot block, not necessarily dead |
| `notes` | string \| null | Redirects, paywall, Domaining sidebar provenance, caveats |

## Categories

| Key | Meaning |
|---|---|
| `lead_gen` | Outbound / buyer prospecting |
| `naming_brandability` | Naming, brandability, financing calculators |
| `parking_landers` | Parking and for-sale landers |
| `news_blogs` | Industry news and blogs |
| `whois_history` | WHOIS, RDAP, ownership / IQ history |
| `traffic_seo` | Traffic estimates and SEO metrics |
| `appraisal` | Automated appraisals |
| `sales_comps` | Historical sales / comps databases |
| `archives` | Web archives / prior content |
| `ssl_security` | SSL and website security checks |
| `udrp_trademark` | UDRP cases and trademark search |
| `company_intel` | Company / funding / people intel |
| `keyword_trends` | Keyword volume and trend tools |
| `forums` | Domainer forums |
| `auctions_dropcatch` | Auctions, drop-catch, expired marketplaces |
| `escrow` | Transaction escrow |
| `registrars` | Registrars commonly used by domainers |

## Provenance

Domaining.com **DOMAINER TOOLS** sidebar (archived 2026-07-16):  
https://web.archive.org/web/20260716031459/https://www.domaining.com/

Updated: `2026-09-19T16:34:06+05:30`
