#!/usr/bin/env python3
"""Domain Diaries wall-of-fame HTTP server.

Serves the static site in ./web and a small JSON API over the 2025–2026
tweet wall in data/tweets-2025-2026.jsonl.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

ROOT = Path(__file__).resolve().parent
WEB_DIR = ROOT / "web"
DATA_PATH = ROOT / "data" / "tweets-2025-2026.jsonl"

TIER_RANK = {"20k": 20, "30k": 30, "50k": 50}


def _iso(value: str | None) -> str:
    if not value:
        return ""
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%d")
    except ValueError:
        return value[:10]


def load_tweets(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            raw = json.loads(line)
            domains = [d for d in (raw.get("domains") or []) if d]
            text = raw.get("text") or ""
            username = raw.get("username") or ""
            haystack = " ".join(
                [
                    text,
                    username,
                    " ".join(domains),
                    str(raw.get("price_raw") or ""),
                    str(raw.get("price_usd") or ""),
                ]
            ).lower()
            rows.append(
                {
                    "id": str(raw.get("id") or ""),
                    "url": raw.get("url") or "",
                    "username": username,
                    "text": text,
                    "created_at": raw.get("created_at") or "",
                    "day": _iso(raw.get("created_at")),
                    "domains": domains,
                    "price_usd": raw.get("price_usd"),
                    "price_raw": raw.get("price_raw"),
                    "premium_tier": raw.get("premium_tier"),
                    "_hay": haystack,
                    "_tier": TIER_RANK.get(raw.get("premium_tier") or "", 0),
                    "_ts": raw.get("created_at") or "",
                    "_price": float(raw["price_usd"])
                    if isinstance(raw.get("price_usd"), (int, float))
                    else -1.0,
                }
            )
    rows.sort(key=lambda r: r["_ts"], reverse=True)
    return rows


class Catalog:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows
        users = {r["username"] for r in rows if r["username"]}
        priced = [r["_price"] for r in rows if r["_price"] > 0]
        days = [r["day"] for r in rows if r["day"]]
        self.stats = {
            "tweets": len(rows),
            "domainers": len(users),
            "premium": sum(1 for r in rows if r["_tier"] >= 20),
            "premium_20k": sum(1 for r in rows if r["_tier"] == 20),
            "premium_30k": sum(1 for r in rows if r["_tier"] == 30),
            "premium_50k": sum(1 for r in rows if r["_tier"] == 50),
            "with_price": len(priced),
            "date_min": min(days) if days else None,
            "date_max": max(days) if days else None,
        }

    def query(
        self,
        q: str,
        min_tier: int,
        sort: str,
        offset: int,
        limit: int,
    ) -> dict[str, Any]:
        needle = q.strip().lower()
        matched = [
            r
            for r in self.rows
            if r["_tier"] >= min_tier and (not needle or needle in r["_hay"])
        ]
        if sort == "price":
            matched.sort(key=lambda r: r["_price"], reverse=True)
        # newest is the default in-memory order
        total = len(matched)
        page = matched[offset : offset + limit]
        items = [
            {
                "id": r["id"],
                "url": r["url"],
                "username": r["username"],
                "text": r["text"],
                "created_at": r["created_at"],
                "day": r["day"],
                "domains": r["domains"],
                "price_usd": r["price_usd"],
                "price_raw": r["price_raw"],
                "premium_tier": r["premium_tier"],
            }
            for r in page
        ]
        return {"items": items, "total": total, "offset": offset, "limit": limit}


class Handler(SimpleHTTPRequestHandler):
    catalog: Catalog

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def log_message(self, fmt: str, *args: Any) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        if path == "/api/health":
            return self._json({"ok": True})
        if path == "/api/stats":
            return self._json(self.catalog.stats)
        if path == "/api/tweets":
            qs = parse_qs(parsed.query)
            q = (qs.get("q") or [""])[0]
            sort = (qs.get("sort") or ["newest"])[0]
            if sort not in {"newest", "price"}:
                sort = "newest"
            tier = (qs.get("tier") or ["all"])[0]
            min_tier = TIER_RANK.get(tier, 0) if tier != "all" else 0
            try:
                offset = max(0, int((qs.get("offset") or ["0"])[0]))
                limit = min(60, max(1, int((qs.get("limit") or ["24"])[0])))
            except ValueError:
                return self._json({"error": "bad pagination"}, 400)
            return self._json(self.catalog.query(q, min_tier, sort, offset, limit))
        if path == "/":
            self.path = "/index.html"
        return super().do_GET()

    def _json(self, payload: Any, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> int:
    parser = argparse.ArgumentParser(description="Domain Diaries wall server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=3000)
    parser.add_argument("--data", type=Path, default=DATA_PATH)
    args = parser.parse_args()

    if not args.data.exists():
        print(f"missing data file: {args.data}", file=sys.stderr)
        return 1

    print(f"loading {args.data} …", flush=True)
    rows = load_tweets(args.data)
    Handler.catalog = Catalog(rows)
    print(
        f"wall ready: {Handler.catalog.stats['tweets']} tweets, "
        f"{Handler.catalog.stats['domainers']} domainers",
        flush=True,
    )

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Domain Diaries → http://127.0.0.1:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped", flush=True)
        server.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
