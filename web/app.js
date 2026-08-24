const wall = document.getElementById("wall");
const empty = document.getElementById("empty");
const count = document.getElementById("count");
const status = document.getElementById("status");
const sentinel = document.getElementById("sentinel");
const form = document.getElementById("filters");

const PAGE = 24;
let offset = 0;
let total = 0;
let loading = false;
let done = false;
let controller = null;

function fmt(n) {
  return new Intl.NumberFormat("en-US").format(n);
}

function money(usd, raw) {
  if (typeof usd === "number" && Number.isFinite(usd) && usd > 0) {
    if (usd >= 1_000_000) {
      const m = usd / 1_000_000;
      return `$${m >= 10 ? m.toFixed(0) : m.toFixed(1).replace(/\.0$/, "")}M`;
    }
    if (usd >= 10_000) return `$${Math.round(usd / 1000)}k`;
    return `$${fmt(Math.round(usd))}`;
  }
  return raw || "Price n/a";
}

function escapeHtml(s) {
  return String(s)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function params() {
  const data = new FormData(form);
  return {
    q: (data.get("q") || "").toString().trim(),
    tier: (data.get("tier") || "all").toString(),
    sort: document.getElementById("sort").value,
  };
}

async function loadStats() {
  const res = await fetch("/api/stats");
  const s = await res.json();
  document.getElementById("stat-tweets").textContent = fmt(s.tweets);
  document.getElementById("stat-domainers").textContent = fmt(s.domainers);
  document.getElementById("stat-premium").textContent = fmt(s.premium);
  if (s.date_min && s.date_max) {
    const a = s.date_min.slice(0, 7);
    const b = s.date_max.slice(0, 7);
    document.getElementById("stat-window").textContent = `${a} – ${b}`;
  }
}

function card(item) {
  const domains = (item.domains || [])
    .slice(0, 4)
    .map((d) => `<span>${escapeHtml(d)}</span>`)
    .join("");
  const tier = item.premium_tier ? ` tier-${item.premium_tier}` : "";
  const handle = item.username ? `@${item.username}` : "unknown";
  const href = item.url || "#";
  return `<a class="card" href="${escapeHtml(href)}" target="_blank" rel="noopener noreferrer">
    <div class="card-top">
      <span class="user">${escapeHtml(handle)}</span>
      <time datetime="${escapeHtml(item.created_at || "")}">${escapeHtml(item.day || "")}</time>
    </div>
    <p class="price${tier}">${escapeHtml(money(item.price_usd, item.price_raw))}</p>
    ${domains ? `<div class="domains">${domains}</div>` : ""}
    <p class="text">${escapeHtml(item.text || "")}</p>
    <span class="open">Open original on X ↗</span>
  </a>`;
}

async function fetchPage(reset) {
  if (loading) return;
  if (!reset && done) return;
  loading = true;
  status.textContent = "Loading…";
  if (controller) controller.abort();
  controller = new AbortController();
  const { q, tier, sort } = params();
  const url = new URL("/api/tweets", location.origin);
  url.searchParams.set("q", q);
  url.searchParams.set("tier", tier);
  url.searchParams.set("sort", sort);
  url.searchParams.set("offset", String(reset ? 0 : offset));
  url.searchParams.set("limit", String(PAGE));
  try {
    const res = await fetch(url, { signal: controller.signal });
    const data = await res.json();
    total = data.total;
    const items = data.items || [];
    if (reset) {
      wall.innerHTML = "";
      offset = 0;
      done = false;
    }
    wall.insertAdjacentHTML("beforeend", items.map(card).join(""));
    offset += items.length;
    done = offset >= total || items.length === 0;
    count.textContent = `${fmt(total)} matching sales`;
    empty.hidden = total !== 0;
    sentinel.hidden = done;
    status.textContent = done && total ? "End of the wall." : "";
  } catch (err) {
    if (err.name !== "AbortError") {
      status.textContent = "Could not load the wall.";
    }
  } finally {
    loading = false;
  }
}

function resetAndLoad() {
  done = false;
  offset = 0;
  fetchPage(true);
}

let timer = 0;
document.getElementById("q").addEventListener("input", () => {
  clearTimeout(timer);
  timer = setTimeout(resetAndLoad, 180);
});
form.addEventListener("change", resetAndLoad);

const observer = new IntersectionObserver((entries) => {
  if (entries.some((e) => e.isIntersecting)) fetchPage(false);
});
observer.observe(sentinel);

loadStats().catch(() => {
  status.textContent = "Could not load stats.";
});
resetAndLoad();
