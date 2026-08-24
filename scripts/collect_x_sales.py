#!/usr/bin/env python3
"""Domain Diaries Phase 1 — collect domain-sale posts via official X API v2.

Official endpoints only:
  GET https://api.x.com/2/tweets/search/all
  GET https://api.x.com/2/tweets/search/recent

Does not scrape x.com HTML. Exits 2 if no bearer token is configured.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from parse_sale import parse_sale  # noqa: E402

API_HOST = "https://api.x.com/2/tweets"
SEARCH_ALL = f"{API_HOST}/search/all"
SEARCH_RECENT = f"{API_HOST}/search/recent"

TWEET_FIELDS = "created_at,public_metrics,author_id,lang,entities"
USER_FIELDS = "username,name"
EXPANSIONS = "author_id"
MAX_RESULTS = 100
USER_AGENT = "DomainDiariesCollector/1.0 (official-x-api-v2; no-scrape)"


def load_bearer_token(env_file: Path) -> tuple[str, str]:
    """Return (token, source). source is 'env' or the .env path."""
    env = os.environ.get("X_BEARER_TOKEN", "").strip()
    if env:
        return env, "env"
    if env_file.is_file():
        for raw in env_file.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            if key.strip() != "X_BEARER_TOKEN":
                continue
            token = val.strip().strip("'").strip('"')
            if token:
                return token, str(env_file)
    print(
        "No X API bearer token. Set X_BEARER_TOKEN or put it in "
        f"{env_file} (gitignored). Official X API v2 only — this collector "
        "will not scrape x.com.",
        file=sys.stderr,
    )
    sys.exit(2)


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def build_query_list(queries_path: Path, accounts_path: Path) -> list[dict[str, str]]:
    payload = load_json(queries_path)
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in payload.get("queries", []):
        q = (item.get("query") or "").strip()
        if not q or q in seen:
            continue
        seen.add(q)
        out.append({"id": item.get("id") or q, "query": q})

    accounts = load_json(accounts_path).get("accounts", [])
    usernames = []
    for acc in accounts:
        u = (acc.get("username") or "").strip().lstrip("@")
        if u:
            usernames.append(u)
    # Per-account timeline-style search (sale-filtered).
    for u in usernames:
        q = f'from:{u} (sold OR sale OR closed OR "sold for" OR acquired) -is:retweet lang:en'
        if q not in seen:
            seen.add(q)
            out.append({"id": f"from_{u}", "query": q})
    return out


def existing_ids(path: Path) -> set[str]:
    ids: set[str] = set()
    if not path.is_file() or path.stat().st_size == 0:
        return ids
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            tid = obj.get("id")
            if tid:
                ids.add(str(tid))
    return ids


def iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def api_get(
    url: str,
    params: dict[str, str],
    token: str,
    errors: list[dict[str, Any]],
    sleep_s: float,
) -> tuple[int, dict[str, Any] | None]:
    """GET with polite 429 retries. Returns (status, json_or_none)."""
    qs = urllib.parse.urlencode(params, safe=",:")
    full = f"{url}?{qs}"
    req = urllib.request.Request(
        full,
        headers={
            "Authorization": f"Bearer {token}",
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        },
        method="GET",
    )
    attempts = 0
    while True:
        attempts += 1
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                body = resp.read().decode("utf-8")
                status = resp.getcode()
                data = json.loads(body) if body else {}
                if sleep_s > 0:
                    time.sleep(sleep_s)
                return status, data
        except urllib.error.HTTPError as exc:
            status = exc.code
            retry_after = exc.headers.get("Retry-After") if exc.headers else None
            raw = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
            payload: dict[str, Any] = {}
            try:
                payload = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                payload = {"raw": raw[:500]}
            if status == 429 and attempts <= 8:
                wait = 60.0
                if retry_after:
                    try:
                        wait = max(1.0, float(retry_after))
                    except ValueError:
                        wait = 60.0
                errors.append(
                    {
                        "at": iso_now(),
                        "status": 429,
                        "url": url,
                        "query": params.get("query"),
                        "retry_after_s": wait,
                        "attempt": attempts,
                    }
                )
                time.sleep(wait)
                continue
            errors.append(
                {
                    "at": iso_now(),
                    "status": status,
                    "url": url,
                    "query": params.get("query"),
                    "body": payload,
                }
            )
            return status, payload
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            errors.append(
                {
                    "at": iso_now(),
                    "status": 0,
                    "url": url,
                    "query": params.get("query"),
                    "error": str(exc),
                }
            )
            return 0, None


def metrics_of(tweet: dict[str, Any]) -> dict[str, int]:
    m = tweet.get("public_metrics") or {}
    return {
        "likes": int(m.get("like_count") or 0),
        "reposts": int(m.get("repost_count") or m.get("retweet_count") or 0),
        "quotes": int(m.get("quote_count") or 0),
        "replies": int(m.get("reply_count") or 0),
    }


def record_from_tweet(
    tweet: dict[str, Any],
    users: dict[str, dict[str, Any]],
    query: str,
) -> dict[str, Any]:
    tid = str(tweet.get("id") or "")
    author_id = str(tweet.get("author_id") or "")
    user = users.get(author_id) or {}
    username = user.get("username")
    name = user.get("name")
    if username:
        url = f"https://x.com/{username}/status/{tid}"
    else:
        url = f"https://x.com/i/web/status/{tid}"
    parsed = parse_sale(tweet.get("text") or "")
    rec = {
        "id": tid,
        "url": url,
        "text": tweet.get("text") or "",
        "created_at": tweet.get("created_at"),
        "author_id": author_id or None,
        "username": username,
        "name": name,
        "domains": parsed["domains"],
        "price_usd": parsed["price_usd"],
        "price_raw": parsed["price_raw"],
        "premium_tier": parsed["premium_tier"],
        **metrics_of(tweet),
        "query": query,
    }
    return rec


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    tmp.replace(path)


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def rebuild_premium(sales_path: Path, premium_path: Path) -> dict[str, int]:
    counts = {"20k": 0, "30k": 0, "50k": 0}
    rows: list[dict[str, Any]] = []
    if sales_path.is_file() and sales_path.stat().st_size:
        with sales_path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                tier = obj.get("premium_tier")
                if tier in counts:
                    counts[tier] += 1
                    rows.append(obj)
    write_jsonl(premium_path, rows)
    return counts


def summarize(
    sales_path: Path,
    premium_counts: dict[str, int],
    extra: dict[str, Any],
) -> dict[str, Any]:
    total = 0
    with_domain = 0
    with_price = 0
    earliest: str | None = None
    latest: str | None = None
    if sales_path.is_file() and sales_path.stat().st_size:
        with sales_path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                total += 1
                if obj.get("domains"):
                    with_domain += 1
                if obj.get("price_usd") is not None:
                    with_price += 1
                created = obj.get("created_at")
                if created:
                    if earliest is None or created < earliest:
                        earliest = created
                    if latest is None or created > latest:
                        latest = created
    out = {
        "collected_at": iso_now(),
        "total_posts": total,
        "with_domain": with_domain,
        "with_price": with_price,
        "premium": {
            "20k": premium_counts.get("20k", 0),
            "30k": premium_counts.get("30k", 0),
            "50k": premium_counts.get("50k", 0),
            "total": sum(premium_counts.values()),
        },
        "date_range": {"earliest": earliest, "latest": latest},
    }
    out.update(extra)
    return out


def collect(args: argparse.Namespace) -> int:
    env_file = Path(args.env_file)
    token, token_source = load_bearer_token(env_file)
    queries = build_query_list(Path(args.queries), Path(args.accounts))
    sales_path = Path(args.sales)
    premium_path = Path(args.premium)
    summary_path = Path(args.summary)
    sales_path.parent.mkdir(parents=True, exist_ok=True)

    seen = existing_ids(sales_path)
    errors: list[dict[str, Any]] = []
    queries_run: list[str] = []
    new_count = 0

    if args.endpoint == "recent":
        endpoint = SEARCH_RECENT
    else:
        endpoint = SEARCH_ALL
    endpoint_name = "all" if endpoint.endswith("/all") else "recent"
    used_fallback = False

    def run_query(url: str, qid: str, query: str) -> str:
        """Page a query. Returns the endpoint name actually used."""
        nonlocal new_count, used_fallback
        used = "all" if url.endswith("/all") else "recent"
        next_token: str | None = None
        pages = 0
        while new_count < args.max_posts:
            params = {
                "query": query,
                "max_results": str(MAX_RESULTS),
                "tweet.fields": TWEET_FIELDS,
                "expansions": EXPANSIONS,
                "user.fields": USER_FIELDS,
            }
            if args.start_time:
                params["start_time"] = args.start_time
            if args.end_time:
                params["end_time"] = args.end_time
            if next_token:
                params["next_token"] = next_token
            status, data = api_get(url, params, token, errors, args.sleep)
            if status in (402, 403) and url.endswith("/all"):
                used_fallback = True
                return run_query(SEARCH_RECENT, qid, query)
            if status != 200 or not data:
                break
            users = {
                str(u.get("id")): u
                for u in (data.get("includes") or {}).get("users") or []
                if u.get("id")
            }
            rows = data.get("data") or []
            if not rows:
                break
            for tweet in rows:
                if new_count >= args.max_posts:
                    break
                tid = str(tweet.get("id") or "")
                if not tid or tid in seen:
                    continue
                rec = record_from_tweet(tweet, users, query)
                append_jsonl(sales_path, rec)
                seen.add(tid)
                new_count += 1
            pages += 1
            next_token = (data.get("meta") or {}).get("next_token")
            if not next_token:
                break
            if args.max_pages and pages >= args.max_pages:
                break
        return used

    for item in queries:
        if new_count >= args.max_posts:
            break
        queries_run.append(item["id"])
        endpoint_name = run_query(endpoint, item["id"], item["query"])
        if used_fallback:
            endpoint = SEARCH_RECENT

    premium_counts = rebuild_premium(sales_path, premium_path)
    summary = summarize(
        sales_path,
        premium_counts,
        {
            "endpoint_used": endpoint_name,
            "fell_back_to_recent": used_fallback,
            "new_posts_this_run": new_count,
            "queries_run": queries_run,
            "errors": errors,
            "token_source": token_source,
            "max_posts": args.max_posts,
        },
    )
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(
        f"wrote {new_count} new posts "
        f"(total {summary['total_posts']}) via search/{endpoint_name} "
        f"-> {sales_path}"
    )
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Collect domain-sale posts from the official X API v2 (no scrape)."
    )
    p.add_argument("--max-posts", type=int, default=10000, help="Stop after this many NEW posts.")
    p.add_argument("--max-pages", type=int, default=0, help="Optional per-query page cap (0 = no cap).")
    p.add_argument("--sleep", type=float, default=3.0, help="Seconds to sleep after each successful page.")
    p.add_argument(
        "--endpoint",
        choices=("auto", "all", "recent"),
        default="auto",
        help="auto tries search/all then falls back to search/recent on 402/403.",
    )
    p.add_argument("--start-time", default="", help="ISO-8601 start_time (API param, not a query operator).")
    p.add_argument("--end-time", default="", help="ISO-8601 end_time.")
    p.add_argument("--queries", default=str(ROOT / "data" / "queries.json"))
    p.add_argument("--accounts", default=str(ROOT / "data" / "accounts.json"))
    p.add_argument("--sales", default=str(ROOT / "data" / "sales.jsonl"))
    p.add_argument("--premium", default=str(ROOT / "data" / "premium.jsonl"))
    p.add_argument("--summary", default=str(ROOT / "data" / "summary.json"))
    p.add_argument("--env-file", default=str(ROOT / ".env"))
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    return collect(parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())
