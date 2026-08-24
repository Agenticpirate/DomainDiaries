const money = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

const moneyExact = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const compact = new Intl.NumberFormat("en-US", {
  notation: "compact",
  maximumFractionDigits: 1,
});

export function formatUsd(value: number): string {
  return money.format(value);
}

export function formatUsdExact(value: number): string {
  return moneyExact.format(value);
}

export function formatCompact(value: number): string {
  return compact.format(value);
}

export function formatPct(value: number): string {
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(1)}%`;
}

export function minutesLabel(minutes: number): string {
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  return `${hours}h ago`;
}

export function slugFromUrl(url: string): string {
  try {
    const host = new URL(url.startsWith("http") ? url : `https://${url}`).hostname.replace(/^www\./, "");
    return host.split(".")[0]?.replace(/[^a-z0-9-]/gi, "").toLowerCase() || "project";
  } catch {
    return "project";
  }
}
