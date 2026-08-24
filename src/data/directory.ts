import type { CategoryId, MarketStat, NetworkId, OutbidEvent, Project } from "../types";

export const NETWORKS: Array<{
  id: NetworkId;
  label: string;
  short: string;
  hue: string;
  projects: number;
}> = [
  { id: "ethereum", label: "Ethereum", short: "ETH", hue: "#8B9CFF", projects: 148 },
  { id: "solana", label: "Solana", short: "SOL", hue: "#14F195", projects: 121 },
  { id: "bnb", label: "BNB Chain", short: "BNB", hue: "#F3BA2F", projects: 86 },
  { id: "base", label: "Base", short: "BASE", hue: "#0052FF", projects: 74 },
  { id: "avalanche", label: "Avalanche", short: "AVAX", hue: "#E84142", projects: 52 },
  { id: "polygon", label: "Polygon", short: "POL", hue: "#8247E5", projects: 47 },
  { id: "arbitrum", label: "Arbitrum", short: "ARB", hue: "#28A0F0", projects: 41 },
  { id: "ton", label: "TON", short: "TON", hue: "#0098EA", projects: 33 },
];

export const CATEGORIES: Array<{
  id: CategoryId;
  label: string;
  projects: number;
}> = [
  { id: "defi", label: "DeFi", projects: 164 },
  { id: "memecoins", label: "Memecoins", projects: 118 },
  { id: "infrastructure", label: "Infrastructure", projects: 97 },
  { id: "ai", label: "AI", projects: 81 },
  { id: "nft", label: "NFT", projects: 64 },
  { id: "gaming", label: "Gaming", projects: 53 },
  { id: "payments", label: "Payments", projects: 38 },
  { id: "rwa", label: "RWA", projects: 27 },
];

export const STATS: MarketStat[] = [
  { label: "Total Volume (24h)", value: "$215,832", change: 12.4, spark: [18, 22, 19, 28, 26, 34, 31, 42], tone: "violet" },
  { label: "Active Projects", value: "642", change: 4.1, spark: [30, 32, 31, 36, 38, 37, 41, 44], tone: "cyan" },
  { label: "Total Clicks (24h)", value: "184.2K", change: 9.8, spark: [12, 18, 16, 24, 22, 29, 33, 38], tone: "gold" },
  { label: "Avg. Bid Amount", value: "$1,842", change: 6.2, spark: [20, 18, 22, 21, 26, 24, 28, 30], tone: "pink" },
];

export const PROJECTS: Project[] = [
  {
    id: "solanahub",
    name: "SolanaHub",
    tagline: "The liquidity layer for high-speed DeFi on Solana.",
    description:
      "SolanaHub routes swaps, restaking, and validator flows through a single desk built for speed. Rank #1 is paid visibility — the product underneath is a real routing engine.",
    url: "https://solanahub.xyz",
    network: "solana",
    category: "infrastructure",
    clicks7d: 128400,
    bidUsd: 17005,
    listedAt: "2026-08-12",
  },
  {
    id: "ethereummax",
    name: "EthereumMax",
    tagline: "Institutional ETH yield without leaving mainnet.",
    description:
      "EthereumMax packages staking, restaking, and structured yield into a single vault interface aimed at treasuries and funds.",
    url: "https://ethereummax.io",
    network: "ethereum",
    category: "defi",
    clicks7d: 110280,
    bidUsd: 16000,
    listedAt: "2026-08-10",
  },
  {
    id: "btcex",
    name: "BTCex",
    tagline: "Spot, perps, and vaults with a bitcoin-first order book.",
    description:
      "BTCex is a hybrid venue for BTC-collateralized markets. The listing bid buys the bronze podium; the book still has to earn the clicks.",
    url: "https://btcex.trade",
    network: "ethereum",
    category: "defi",
    clicks7d: 98012,
    bidUsd: 14028,
    listedAt: "2026-08-08",
  },
  {
    id: "orbitlend",
    name: "OrbitLend",
    tagline: "Cross-chain credit markets with isolated vaults.",
    description: "Borrow against LST collateral across Base and Ethereum with isolated risk buckets.",
    url: "https://orbitlend.fi",
    network: "base",
    category: "defi",
    clicks7d: 83005,
    bidUsd: 9800,
    listedAt: "2026-08-04",
  },
  {
    id: "pixelape",
    name: "PixelApe",
    tagline: "On-chain generative art drops with royalty routing.",
    description: "A mint desk for artists who want transparent royalties and instant secondary listings.",
    url: "https://pixelape.art",
    network: "ethereum",
    category: "nft",
    clicks7d: 76410,
    bidUsd: 8420,
    listedAt: "2026-08-02",
  },
  {
    id: "neonfox",
    name: "NeonFox",
    tagline: "The memecoin terminal that actually shows holders.",
    description: "Live holder maps, bundle detection, and launch pads for Solana memecoins.",
    url: "https://neonfox.fun",
    network: "solana",
    category: "memecoins",
    clicks7d: 91220,
    bidUsd: 7990,
    listedAt: "2026-08-15",
  },
  {
    id: "aetherai",
    name: "AetherAI",
    tagline: "Agentic trading research with on-chain execution.",
    description: "Research agents that cite sources, then route trades through your own wallet.",
    url: "https://aetherai.app",
    network: "ethereum",
    category: "ai",
    clicks7d: 70112,
    bidUsd: 7250,
    listedAt: "2026-07-28",
  },
  {
    id: "runegate",
    name: "RuneGate",
    tagline: "Modular sequencer kit for app-specific rollups.",
    description: "Spin up a rollup with shared proving and a built-in explorer in one afternoon.",
    url: "https://runegate.dev",
    network: "ethereum",
    category: "infrastructure",
    clicks7d: 65490,
    bidUsd: 6800,
    listedAt: "2026-07-21",
  },
  {
    id: "goldvault",
    name: "GoldVault",
    tagline: "Tokenized bullion with daily proof of reserves.",
    description: "RWA vaults backed by allocated gold, redeemable through licensed partners.",
    url: "https://goldvault.gold",
    network: "ethereum",
    category: "rwa",
    clicks7d: 44880,
    bidUsd: 6100,
    listedAt: "2026-07-18",
  },
  {
    id: "arcadeforge",
    name: "ArcadeForge",
    tagline: "On-chain seasons, off-chain gameplay, real rewards.",
    description: "A game studio toolkit for seasonal economies that settle on Base.",
    url: "https://arcadeforge.gg",
    network: "base",
    category: "gaming",
    clicks7d: 59210,
    bidUsd: 5450,
    listedAt: "2026-07-12",
  },
  {
    id: "paylane",
    name: "PayLane",
    tagline: "Stablecoin checkout that feels like Stripe.",
    description: "USDC and USDT rails for merchants, with automatic off-ramps where licensed.",
    url: "https://paylane.xyz",
    network: "polygon",
    category: "payments",
    clicks7d: 38740,
    bidUsd: 4980,
    listedAt: "2026-07-09",
  },
  {
    id: "frostswap",
    name: "FrostSwap",
    tagline: "Zero-fee stableswap on Avalanche.",
    description: "A curve-style pool tuned for frozen stables and RWA dollars.",
    url: "https://frostswap.fi",
    network: "avalanche",
    category: "defi",
    clicks7d: 33120,
    bidUsd: 4320,
    listedAt: "2026-07-04",
  },
  {
    id: "nibblenft",
    name: "NibbleNFT",
    tagline: "Tiny collections, huge floors, weekly burns.",
    description: "A curated NFT bazaar that retires supply every Friday.",
    url: "https://nibblenft.io",
    network: "ethereum",
    category: "nft",
    clicks7d: 29880,
    bidUsd: 3890,
    listedAt: "2026-06-30",
  },
  {
    id: "orbitbot",
    name: "OrbitBot",
    tagline: "Copy-trading bots with on-chain attestations.",
    description: "Follow wallets, not influencers. Every copy trade is signed and public.",
    url: "https://orbitbot.ai",
    network: "solana",
    category: "ai",
    clicks7d: 41200,
    bidUsd: 3550,
    listedAt: "2026-06-26",
  },
  {
    id: "tonplaza",
    name: "TON Plaza",
    tagline: "Mini-app marketplace inside Telegram.",
    description: "Discover TON mini apps with verified contracts and weekly leaderboards.",
    url: "https://tonplaza.app",
    network: "ton",
    category: "infrastructure",
    clicks7d: 27640,
    bidUsd: 3100,
    listedAt: "2026-06-20",
  },
  {
    id: "arbvault",
    name: "ArbVault",
    tagline: "Delta-neutral vaults on Arbitrum perps.",
    description: "Market-neutral strategies with weekly epochs and transparent PnL.",
    url: "https://arbvault.fi",
    network: "arbitrum",
    category: "defi",
    clicks7d: 25410,
    bidUsd: 2780,
    listedAt: "2026-06-14",
  },
  {
    id: "moonrice",
    name: "MoonRice",
    tagline: "The friendliest memecoin on BNB.",
    description: "Community raffles, daily burns, and a rice-themed launchpad.",
    url: "https://moonrice.fun",
    network: "bnb",
    category: "memecoins",
    clicks7d: 36890,
    bidUsd: 2410,
    listedAt: "2026-06-11",
  },
  {
    id: "silkroad",
    name: "SilkRoad",
    tagline: "Invoice rails for cross-border stables.",
    description: "Pay suppliers in USDC, settle locally, keep the audit trail.",
    url: "https://silkroad.pay",
    network: "polygon",
    category: "payments",
    clicks7d: 19880,
    bidUsd: 2100,
    listedAt: "2026-06-02",
  },
  {
    id: "questforge",
    name: "QuestForge",
    tagline: "On-chain quests that pay in points and tokens.",
    description: "Campaign infrastructure for protocols that want real users, not bots.",
    url: "https://questforge.app",
    network: "base",
    category: "gaming",
    clicks7d: 22110,
    bidUsd: 1860,
    listedAt: "2026-05-28",
  },
  {
    id: "lumenrwa",
    name: "LumenRWA",
    tagline: "Treasury bills on-chain, daily NAV.",
    description: "Short-duration T-bill exposure wrapped as a composable ERC-20.",
    url: "https://lumenrwa.com",
    network: "ethereum",
    category: "rwa",
    clicks7d: 17440,
    bidUsd: 1640,
    listedAt: "2026-05-20",
  },
];

export const OUTBIDS: OutbidEvent[] = [
  { id: "1", projectId: "solanahub", projectName: "SolanaHub", amount: 17005, minutesAgo: 2 },
  { id: "2", projectId: "ethereummax", projectName: "EthereumMax", amount: 16000, minutesAgo: 8 },
  { id: "3", projectId: "neonfox", projectName: "NeonFox", amount: 7990, minutesAgo: 14 },
  { id: "4", projectId: "btcex", projectName: "BTCex", amount: 14028, minutesAgo: 21 },
  { id: "5", projectId: "orbitlend", projectName: "OrbitLend", amount: 9800, minutesAgo: 36 },
  { id: "6", projectId: "aetherai", projectName: "AetherAI", amount: 7250, minutesAgo: 44 },
];

export const TOP_BID = PROJECTS[0].bidUsd + 1;
export const PROJECTS_ONLINE = 642;
export const SPENT_24H = 215832.72;
export const WEEKLY_CLICKS = "1.2M+";

export function networkOf(id: NetworkId) {
  return NETWORKS.find((item) => item.id === id)!;
}

export function categoryOf(id: CategoryId) {
  return CATEGORIES.find((item) => item.id === id)!;
}

export function ranked(projects: Project[]): Project[] {
  return [...projects].sort((a, b) => b.bidUsd - a.bidUsd || b.clicks7d - a.clicks7d);
}
