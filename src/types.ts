export type NetworkId =
  | "ethereum"
  | "solana"
  | "bnb"
  | "base"
  | "avalanche"
  | "polygon"
  | "arbitrum"
  | "ton";

export type CategoryId =
  | "defi"
  | "nft"
  | "memecoins"
  | "infrastructure"
  | "ai"
  | "gaming"
  | "payments"
  | "rwa";

export type Project = {
  id: string;
  name: string;
  tagline: string;
  description: string;
  url: string;
  network: NetworkId;
  category: CategoryId;
  clicks7d: number;
  bidUsd: number;
  listedAt: string;
};

export type OutbidEvent = {
  id: string;
  projectId: string;
  projectName: string;
  amount: number;
  minutesAgo: number;
};

export type MarketStat = {
  label: string;
  value: string;
  change: number;
  spark: number[];
  tone: "violet" | "cyan" | "gold" | "pink";
};
