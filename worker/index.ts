/**
 * Krypto market API — proxies CoinGecko + Alternative.me with Cache API.
 * Upstream URLs are allowlisted; coin ids are constrained to [a-z0-9-].
 */

const COINGECKO = "https://api.coingecko.com/api/v3";
const FNG = "https://api.alternative.me/fng/";
const COIN_ID = /^[a-z0-9-]{1,80}$/;
const CACHE_TTL = {
  markets: 45,
  global: 60,
  search: 30,
  coin: 90,
  chart: 120,
  fng: 300,
};

function json(data: unknown, status = 200, ttl = 30): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": `public, max-age=${ttl}`,
    },
  });
}

function bad(message: string, status = 400): Response {
  return json({ error: message }, status, 0);
}

async function cachedGetAndStore(ctx: ExecutionContext, url: string, ttl: number): Promise<Response> {
  const cache = caches.default;
  const cacheKey = new Request(url, { method: "GET" });
  const hit = await cache.match(cacheKey);
  if (hit) {
    const headers = new Headers(hit.headers);
    headers.set("x-krypto-cache", "hit");
    return new Response(hit.body, { status: hit.status, headers });
  }

  const upstream = await fetch(url, {
    headers: {
      accept: "application/json",
      "user-agent": "Krypto/0.1 (markets desk)",
    },
  });

  if (!upstream.ok) {
    const status = upstream.status === 429 ? 429 : 502;
    return json(
      {
        error:
          upstream.status === 429
            ? "Market data is rate-limited. Try again in a minute."
            : "Market data is temporarily unavailable.",
      },
      status,
      5,
    );
  }

  const body = await upstream.arrayBuffer();
  const response = new Response(body, {
    status: 200,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": `public, max-age=${ttl}`,
      "x-krypto-cache": "miss",
    },
  });
  ctx.waitUntil(cache.put(cacheKey, response.clone()));
  return response;
}

export default {
  async fetch(request, _env, ctx): Promise<Response> {
    const url = new URL(request.url);
    if (request.method !== "GET") {
      return bad("Method not allowed", 405);
    }

    if (url.pathname === "/api/health") {
      return json({ ok: true, service: "krypto" }, 200, 10);
    }

    if (url.pathname === "/api/markets") {
      const page = Math.min(Math.max(Number(url.searchParams.get("page") ?? "1") || 1, 1), 4);
      const perPage = Math.min(Math.max(Number(url.searchParams.get("per_page") ?? "100") || 100, 10), 100);
      const ids = (url.searchParams.get("ids") ?? "").split(",").filter((id) => COIN_ID.test(id)).slice(0, 50);
      const params = new URLSearchParams({
        vs_currency: "usd",
        order: "market_cap_desc",
        per_page: String(perPage),
        page: String(page),
        sparkline: "true",
        price_change_percentage: "1h,24h,7d",
      });
      if (ids.length) params.set("ids", ids.join(","));
      return cachedGetAndStore(ctx, `${COINGECKO}/coins/markets?${params}`, CACHE_TTL.markets);
    }

    if (url.pathname === "/api/global") {
      return cachedGetAndStore(ctx, `${COINGECKO}/global`, CACHE_TTL.global);
    }

    if (url.pathname === "/api/search") {
      const q = (url.searchParams.get("q") ?? "").trim().slice(0, 80);
      if (q.length < 1) return json({ coins: [] }, 200, 10);
      return cachedGetAndStore(ctx, `${COINGECKO}/search?query=${encodeURIComponent(q)}`, CACHE_TTL.search);
    }

    const coinMatch = url.pathname.match(/^\/api\/coin\/([a-z0-9-]+)$/);
    if (coinMatch) {
      const id = coinMatch[1];
      if (!COIN_ID.test(id)) return bad("Invalid coin id");
      const params = new URLSearchParams({
        localization: "false",
        tickers: "false",
        market_data: "true",
        community_data: "false",
        developer_data: "false",
        sparkline: "true",
      });
      return cachedGetAndStore(ctx, `${COINGECKO}/coins/${id}?${params}`, CACHE_TTL.coin);
    }

    const chartMatch = url.pathname.match(/^\/api\/chart\/([a-z0-9-]+)$/);
    if (chartMatch) {
      const id = chartMatch[1];
      if (!COIN_ID.test(id)) return bad("Invalid coin id");
      const days = ["1", "7", "30", "90", "365"].includes(url.searchParams.get("days") ?? "")
        ? url.searchParams.get("days")!
        : "7";
      return cachedGetAndStore(
        ctx,
        `${COINGECKO}/coins/${id}/market_chart?vs_currency=usd&days=${days}`,
        CACHE_TTL.chart,
      );
    }

    if (url.pathname === "/api/fng") {
      return cachedGetAndStore(ctx, `${FNG}?limit=1`, CACHE_TTL.fng);
    }

    return bad("Not found", 404);
  },
} satisfies ExportedHandler<Env>;
