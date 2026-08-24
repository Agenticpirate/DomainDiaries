# Krypto Directory

Premium crypto project leaderboard. Rank is an auction.

This is a high-fidelity sample of the directory: gold / silver / bronze podium, live outbid ticker, network and category boards, and a listing desk. Bids in this build stay on the device (`localStorage`) until real payments ship.

## Run

```bash
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173).

```bash
npm run lint
npm run build
```

## Product surface

| Path | What |
|---|---|
| `/` | Leaderboard, podium, ticker, table, market widgets |
| `/networks` | Chain boards |
| `/categories` | Category boards |
| `/promote` | Listing pitch |
| `/project/:id` | Project page |
| `/about` `/resources` | Editorial |

Domain Diaries collectors remain under `data/` and `scripts/`.
