# Domain Diaries

Wall of fame for domainers: sale tweets with backlinks to the original posts on X.

## Data

| File | What |
|---|---|
| `data/tweets.jsonl` | Unique sale tweets (`id`, `url` → `https://x.com/{user}/status/{id}`, handle, text, date, parsed domain/price, `premium_tier`) |
| `data/tweets-2025-2026.jsonl` | Same shape, dated 2025-01-01 through 2026-08-15 |
| `data/sales.jsonl` | Full collect (tweets + DNJournal chart rows) |
| `data/premium.jsonl` | Rows with `price_usd >= 20000` (`20k` / `30k` / `50k`) |
| `data/summary.json` | Collect stats |

Each tweet card on the future site should use `url` as the backlink to the original post.

## Counts (as of 2026-08-15)

- ~10k unique tweet IDs with original x.com links
- ~1.3k domainers
- ~4k premium ($20k+)
- Window 2025 → 15 Aug 2026 is the wall set in `tweets-2025-2026.jsonl`

## Scripts

Collectors under `scripts/` (nitter.poast.org / DNJournal). Official X API was not available.

Do not commit `.env`.
