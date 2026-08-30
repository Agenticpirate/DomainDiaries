# Domain Diaries sale record (phase 1 — DNJournal)

One JSON object per line in `sales.jsonl` and `premium.jsonl`.

| Field | Type | Notes |
|---|---|---|
| `id` | string | `dnjournal|{domain}|{date}|{price}` |
| `source` | string | Always `dnjournal` |
| `url` | string | Chart page the row was parsed from |
| `domain` | string | As published (spaces collapsed). Redacted names → `[redacted]` |
| `price_usd` | number \| null | USD. Uses a printed `$` equivalent when the row is £/€ |
| `price_raw` | string | Price text as published |
| `venue` | string \| null | Where Sold / table title |
| `date` | string \| null | `YYYY-MM-DD` when parseable, else year or chart window |
| `premium_tier` | `"20k"` \| `"30k"` \| `"50k"` \| null | ≥50000 → `50k`, ≥30000 → `30k`, ≥20000 → `20k` |
| `text` | string \| null | Chart window snippet when present |
| `collected_at` | string | ISO-8601 UTC |

`premium.jsonl` is `premium_tier != null`.

## Tweets (`tweets.jsonl`)

One JSON object per sale tweet. `url` is always `https://x.com/{username}/status/{id}`.

Added 2026-08-31:

| Field | Type | Notes |
|---|---|---|
| `poster_kind` | `"individual"` \| `"company"` | Company = marketplace, escrow, registrar, news, or brand database account. From 2026-08-31, new collection prefers `individual`. |

Derived files:

- `tweets-individuals.jsonl` — `poster_kind=individual`
- `tweets-company.jsonl` — `poster_kind=company`
- `company-accounts.json` — denylist handles

