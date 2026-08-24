import type { CategoryId, OutbidEvent, Project } from "../types";
import { OUTBIDS, PROJECTS, ranked } from "../data/directory";
import { slugFromUrl } from "./format";

const KEY = "krypto.directory.v1";

type Store = {
  extras: Project[];
  bidOverrides: Record<string, number>;
  events: OutbidEvent[];
};

function empty(): Store {
  return { extras: [], bidOverrides: {}, events: [] };
}

function load(): Store {
  if (typeof localStorage === "undefined") return empty();
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return empty();
    const parsed = JSON.parse(raw) as Store;
    return {
      extras: Array.isArray(parsed.extras) ? parsed.extras : [],
      bidOverrides: parsed.bidOverrides ?? {},
      events: Array.isArray(parsed.events) ? parsed.events : [],
    };
  } catch {
    return empty();
  }
}

function save(store: Store): void {
  if (typeof localStorage === "undefined") return;
  localStorage.setItem(KEY, JSON.stringify(store));
}

export function loadDirectory(): { projects: Project[]; events: OutbidEvent[] } {
  const store = load();
  const merged = ranked([
    ...PROJECTS.map((project) =>
      store.bidOverrides[project.id] != null ? { ...project, bidUsd: store.bidOverrides[project.id] } : project,
    ),
    ...store.extras,
  ]);
  return { projects: merged, events: [...store.events, ...OUTBIDS].slice(0, 12) };
}

export function applyOutbid(input: {
  url: string;
  category: CategoryId;
  amount: number;
  name?: string;
}): { projects: Project[]; events: OutbidEvent[] } {
  const store = load();
  const host = slugFromUrl(input.url);
  const existing = [...PROJECTS, ...store.extras].find(
    (project) => project.id === host || project.url.includes(host),
  );
  const event: OutbidEvent = {
    id: `${Date.now()}`,
    projectId: existing?.id ?? host,
    projectName: existing?.name ?? input.name ?? host,
    amount: input.amount,
    minutesAgo: 0,
  };
  if (existing) {
    store.bidOverrides[existing.id] = input.amount;
  } else {
    store.extras.push({
      id: host,
      name: input.name ?? host.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
      tagline: "Newly listed on Krypto Directory.",
      description: "This listing was created from the Outbid desk. Replace the copy when the live catalog ships.",
      url: input.url.startsWith("http") ? input.url : `https://${input.url}`,
      network: "ethereum",
      category: input.category,
      clicks7d: 120,
      bidUsd: input.amount,
      listedAt: new Date().toISOString().slice(0, 10),
    });
  }
  store.events = [event, ...store.events].slice(0, 8);
  save(store);
  return loadDirectory();
}
