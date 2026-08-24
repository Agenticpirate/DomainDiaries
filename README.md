# Krypto

Private crypto markets desk. Live tape, a watchlist, and a portfolio that never leaves the browser.

No login. Watchlist and holdings stay in `localStorage` on this device.

## What it does

- **Markets** — top coins by cap, 1h / 24h / 7d change, 7-day sparkline
- **Coin** — price chart, market stats, homepage link
- **Watchlist** — star names from the tape
- **Portfolio** — quantity + USD cost basis, live P&L

Market data is proxied through a Cloudflare Worker (`/api/*`) with short Cache API TTLs so the public CoinGecko demo API is not hammered from every browser tab.

## Run locally

```bash
npm install
npx wrangler types
npm run dev
```

Open [http://localhost:5173](http://localhost:5173).

```bash
npm run lint    # typecheck
npm run build   # client + worker
npm run deploy  # Cloudflare Workers (requires wrangler auth)
```

## Domain Diaries data

This repository also still holds the Domain Diaries tweet/sale collectors under `data/` and `scripts/`. Krypto is the product surface.

## License

Private / project-specific unless otherwise noted.
