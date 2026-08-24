#!/usr/bin/env python3
"""Day-by-day nitter.poast.org search for 2026-01-01 .. 2026-08-15.

Not x.com / not official X API. Every kept record has
https://x.com/{user}/status/{id} and created_at inside the day slice.
"""
from __future__ import annotations

import fcntl
import json
import random
import re
import sys
import time
import urllib.parse
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from collect_nitter_public import (  # noqa: E402
    BASE,
    INDUSTRY,
    Client,
    looks_like_sale,
    now_iso,
    parse_items,
    parse_sale,
)
from solve_poast import solve_pow as solve_pow_script  # noqa: E402

DATA = ROOT / "data"
SALES_PATH = DATA / "sales.jsonl"
PREMIUM_PATH = DATA / "premium.jsonl"
TWEETS_PATH = DATA / "tweets.jsonl"
PROGRESS_PATH = DATA / "collect-progress-daily-2026.json"
RAW = DATA / "raw"
LOCK_PATH = DATA / "raw" / "append.lock"

RANGE_START = date(2026, 1, 1)
RANGE_END = date(2026, 8, 15)  # inclusive

QUERIES = [
    '"just sold" domain',
    '"sold for" .com',
    '"sold for" .ai',
    "sold via Sedo",
    "from:NameBio",
    "from:DomainNews24",
]

SALE_ACCOUNTS = {
    "namebio", "domainnews24", "domaingang", "katerleonid", "fintechnames",
    "domainretail", "doctorbrandx", "justdropped", "bridgeddomains", "ibuild_io",
    "domainlabs", "namehubs", "dndomainname", "andrewrosener", "domainnamewire",
    "sedodaveevanson", "ishmilly", "jamesiles", "rundns", "mediaoptions",
    "swethayenugula", "domaininvesting", "domainshane", "tonynames", "sedo",
    "afternic", "godaddyauctions", "mrpremiumdotcom", "derick_sedo",
    "thedomainagents", "dinvesting", "contactowner", "unlockeddomains",
    "domain_raider", "360domain", "memorabledn", "dropdax", "domainjobcom",
    "atomhq", "lumis_com", "jeffreymgabriel", "escrow_com", "namejet",
    "namepros", "morganlinton", "andrewallemann", "dnjournal", "domainsherpa",
    "dnwatcher", "squadhelp", "undeveloped", "namecheap", "atom", "spaceship",
}
INDUSTRY_ALL = {x.lower() for x in INDUSTRY} | SALE_ACCOUNTS

URL_RE = re.compile(r"^https://x\.com/[A-Za-z0-9_]+/status/\d+$")


def load_numeric_ids(path: Path) -> set[str]:
    seen: set[str] = set()
    if not path.is_file() or path.stat().st_size == 0:
        return seen
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        tid = str(obj.get("id") or "")
        if tid.isdigit():
            seen.add(tid)
    return seen


def load_all_seen() -> set[str]:
    return load_numeric_ids(SALES_PATH) | load_numeric_ids(TWEETS_PATH)


def keep_record(text: str, parsed: dict[str, Any], username: str) -> bool:
    user = (username or "").lower()
    industry = user in INDUSTRY_ALL
    if looks_like_sale(text, parsed, username, industry):
        return True
    if industry and re.search(r"\b(sold|sale|closed|acquired|purchased)\b", text, re.I):
        if parsed.get("domains") or parsed.get("price_usd") is not None:
            return True
        if re.search(r"\b(domain|domains|\.com|\.ai|\.io|#domains)\b", text, re.I):
            return True
    return False


def tweet_row(rec: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": rec["id"],
        "url": rec["url"],
        "username": rec["username"],
        "text": rec["text"],
        "created_at": rec["created_at"],
        "domains": rec.get("domains") or [],
        "price_usd": rec.get("price_usd"),
        "price_raw": rec.get("price_raw"),
        "premium_tier": rec.get("premium_tier"),
        "source": "x-public",
        "collected_at": rec["collected_at"],
        "query": rec.get("query"),
    }


def append_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOCK_PATH.open("a") as lf:
        fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
        try:
            with path.open("a", encoding="utf-8") as fh:
                for row in rows:
                    fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        finally:
            fcntl.flock(lf.fileno(), fcntl.LOCK_UN)


def day_windows() -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    d = RANGE_START
    while d <= RANGE_END:
        nxt = d + timedelta(days=1)
        out.append((d.isoformat(), nxt.isoformat()))
        d = nxt
    return out


def created_in_slice(created_at: str | None, since: str, until: str) -> bool:
    if not created_at or not isinstance(created_at, str):
        return False
    day = created_at[:10]
    if len(day) != 10:
        return False
    return since <= day < until


class DailyCollector:
    def __init__(self) -> None:
        self.client = Client()
        self.seen = load_all_seen()
        self.start_unique = len(self.seen)
        self.new_rows: list[dict[str, Any]] = []
        self.premium_new = 0
        self.queries_run: list[str] = []
        self.days_done: list[str] = []
        self.days_with_new: list[str] = []
        self.errors: list[str] = []
        self.pages_ok = 0
        self.pages_429 = 0
        self.pages_empty = 0
        self.flushed = 0
        self.jobs_ok = 0
        self.jobs_429 = 0
        self.jobs_empty = 0
        self.skipped_oor = 0
        self.skipped_dup = 0

    def write_progress(self, extra: dict[str, Any] | None = None) -> None:
        examples = []
        for r in self.new_rows:
            if r.get("url") and r.get("id") and URL_RE.match(r["url"] or ""):
                examples.append(
                    {
                        "url": r["url"],
                        "username": r.get("username"),
                        "domains": r.get("domains"),
                        "price_usd": r.get("price_usd"),
                        "created_at": r.get("created_at"),
                        "query": r.get("query"),
                        "text": (r.get("text") or "")[:160],
                    }
                )
            if len(examples) >= 5:
                break
        payload = {
            "updated_at": now_iso(),
            "frontend": "nitter.poast.org",
            "source": "x-public",
            "phase": (extra or {}).get("phase", "running"),
            "range": "2026-01-01..2026-08-15",
            "new_unique": len(self.new_rows),
            "total_unique": self.start_unique + len(self.new_rows),
            "start_unique": self.start_unique,
            "premium_new": self.premium_new,
            "flushed": self.flushed,
            "days_covered": len(self.days_done),
            "days_done": self.days_done,
            "days_with_new": self.days_with_new,
            "queries": QUERIES,
            "queries_run": self.queries_run[-120:],
            "jobs_ok": self.jobs_ok,
            "jobs_429": self.jobs_429,
            "jobs_empty": self.jobs_empty,
            "pages_ok": self.pages_ok,
            "pages_429": self.pages_429,
            "pages_empty": self.pages_empty,
            "skipped_out_of_range": self.skipped_oor,
            "skipped_dup": self.skipped_dup,
            "pow_solves": self.client.solved,
            "errors": self.errors[-50:],
            "examples": examples,
            "note": (
                "Day-sliced nitter.poast.org search 2026-01-01..2026-08-15. "
                "Every url is https://x.com/{user}/status/{id}. "
                "created_at required in day slice. Not invented. Not official X API."
            ),
        }
        if extra:
            payload.update(extra)
        PROGRESS_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def refresh_seen(self) -> None:
        self.seen |= load_all_seen()

    def flush(self) -> None:
        self.refresh_seen()
        pending = []
        disk_sales = load_numeric_ids(SALES_PATH)
        disk_tweets = load_numeric_ids(TWEETS_PATH)
        disk = disk_sales | disk_tweets
        for r in self.new_rows[self.flushed :]:
            if r["id"] in disk:
                continue
            if not URL_RE.match(r.get("url") or ""):
                continue
            if not r.get("created_at"):
                continue
            pending.append(r)
            disk.add(r["id"])
        if pending:
            append_jsonl(SALES_PATH, pending)
            prem = [r for r in pending if r.get("premium_tier")]
            append_jsonl(PREMIUM_PATH, prem)
            append_jsonl(TWEETS_PATH, [tweet_row(r) for r in pending])
        self.flushed = len(self.new_rows)
        self.write_progress()

    def fetch_page(self, url: str) -> tuple[int, str]:
        last_code, last_html = 0, ""
        for _attempt in range(4):
            try:
                code, html = self.client.fetch(url, retries=3)
            except Exception as e:
                self.errors.append(f"fetch exc {e}")
                time.sleep(2)
                continue
            last_code, last_html = code, html
            if "Verifying your browser" in html:
                token = None
                try:
                    token = solve_pow_script(html)
                except Exception as e:
                    self.errors.append(f"pow exc {e}")
                    token = None
                if token:
                    name, val = token.split("=", 1)
                    self.client._set_cookie(name, val)
                    self.client.solved += 1
                    time.sleep(0.4)
                    continue
                print("    POW unsolved, retry", flush=True)
                time.sleep(0.8)
                continue
            if code == 429 or "Too Many Requests" in html:
                return 429, html
            return code, html
        return last_code, last_html

    def collect_job(self, query: str, since: str, until: str, max_pages: int = 4) -> str:
        q = f"{query} since:{since} until:{until}"
        label = f"{query} [{since}..{until})"
        path = "/search?f=tweets&q=" + urllib.parse.quote(q, safe="")
        path += f"&since={since}&until={until}"
        next_url = BASE + path
        pages = 0
        saw_items = False
        while next_url and pages < max_pages:
            pages += 1
            code, page = self.fetch_page(next_url)
            if code == 429 or "Too Many Requests" in page:
                self.pages_429 += 1
                self.errors.append(f"429 {label} page={pages}")
                print(f"  429 {label} page={pages}", flush=True)
                return "429"
            if "Verifying your browser" in page or (
                code >= 400 and "timeline-item" not in page
            ):
                self.errors.append(f"block code={code} {label} page={pages}")
                print(f"  block code={code} {label} page={pages}", flush=True)
                RAW.mkdir(parents=True, exist_ok=True)
                (RAW / "blocked-daily-2026.html").write_text(page[:12000], encoding="utf-8")
                return "block"
            items, more = parse_items(page)
            if items:
                saw_items = True
                self.pages_ok += 1
            else:
                self.pages_empty += 1
            new_here = 0
            in_range_here = 0
            for it in items:
                tid = str(it.get("id") or "")
                user = it.get("username") or ""
                if not tid.isdigit() or not user:
                    continue
                created = it.get("created_at")
                if not created_in_slice(created, since, until):
                    self.skipped_oor += 1
                    continue
                if not created_in_slice(created, "2026-01-01", "2026-08-16"):
                    self.skipped_oor += 1
                    continue
                in_range_here += 1
                if tid in self.seen:
                    self.skipped_dup += 1
                    continue
                text = it.get("text") or ""
                parsed = parse_sale(text)
                if not keep_record(text, parsed, user):
                    continue
                url = f"https://x.com/{user}/status/{tid}"
                if not URL_RE.match(url):
                    continue
                self.seen.add(tid)
                rec = {
                    "id": tid,
                    "url": url,
                    "tweet_url": url,
                    "text": text,
                    "created_at": created,
                    "author_id": None,
                    "username": user,
                    "name": it.get("name"),
                    "domains": parsed["domains"],
                    "price_usd": parsed["price_usd"],
                    "price_raw": parsed["price_raw"],
                    "premium_tier": parsed["premium_tier"],
                    "likes": it.get("likes") or 0,
                    "reposts": it.get("reposts") or 0,
                    "quotes": 0,
                    "replies": it.get("replies") or 0,
                    "query": label,
                    "source": "x-public",
                    "collected_at": now_iso(),
                }
                self.new_rows.append(rec)
                if rec.get("premium_tier"):
                    self.premium_new += 1
                new_here += 1
            print(
                f"  {label} p={pages} code={code} items={len(items)} new={new_here} "
                f"more={bool(more)} total_new={len(self.new_rows)}",
                flush=True,
            )
            if not items or in_range_here == 0:
                break
            if more:
                if more.startswith("http"):
                    next_url = more
                elif more.startswith("/"):
                    next_url = BASE + more
                else:
                    path_only = urllib.parse.urlparse(next_url).path
                    next_url = BASE + path_only + (more if more.startswith("?") else "?" + more)
                time.sleep(0.7)
            else:
                next_url = None
        return "ok" if saw_items else "empty"

    def run(self) -> int:
        DATA.mkdir(parents=True, exist_ok=True)
        RAW.mkdir(parents=True, exist_ok=True)
        windows = day_windows()
        done_days: set[str] = set()
        if PROGRESS_PATH.is_file():
            try:
                prev = json.loads(PROGRESS_PATH.read_text(encoding="utf-8"))
                done_days = set(prev.get("days_done") or [])
            except Exception:
                done_days = set()
        windows = [(s, u) for (s, u) in windows if s not in done_days]
        print(
            f"start unique={self.start_unique} queries={len(QUERIES)} "
            f"days={len(windows)} skipped_done={len(done_days)} "
            f"jobs={len(QUERIES) * len(windows)}",
            flush=True,
        )
        self.days_done = sorted(done_days)
        self.write_progress(
            {
                "phase": "start",
                "day_count": len(windows),
                "resumed_skip": sorted(done_days),
            }
        )

        # Warm POW cookie on a dated search (not the live first page)
        warm = BASE + "/search?f=tweets&q=" + urllib.parse.quote(
            '"just sold" domain since:2026-01-01 until:2026-01-02', safe=""
        ) + "&since=2026-01-01&until=2026-01-02"
        code, html = self.fetch_page(warm)
        print(
            f"warmup code={code} pow={self.client.solved} "
            f"items={html.count('timeline-item')} verify={'Verifying' in html}",
            flush=True,
        )

        for since, until in windows:
            day_new_before = len(self.new_rows)
            print(f"DAY {since} new={len(self.new_rows)}", flush=True)
            for q in QUERIES:
                label = f"{q} [{since}..{until})"
                self.queries_run.append(label)
                status = "block"
                for attempt in range(3):
                    try:
                        status = self.collect_job(q, since, until, max_pages=4)
                    except Exception as e:
                        self.errors.append(f"exc {label}: {e}")
                        print(f"  EXC {label}: {e}", flush=True)
                        status = "block"
                    if status == "429":
                        wait = random.randint(22, 45)
                        print(f"  sleep {wait}s after 429 (attempt {attempt+1})", flush=True)
                        time.sleep(wait)
                        continue
                    break
                if status == "ok":
                    self.jobs_ok += 1
                elif status == "empty":
                    self.jobs_empty += 1
                elif status == "429":
                    self.jobs_429 += 1
                self.flush()
                time.sleep(0.4)
            self.days_done.append(since)
            if len(self.new_rows) > day_new_before:
                self.days_with_new.append(since)
            self.write_progress({"phase": "running", "current_day": since})
            if self.pages_429 and self.pages_429 % 8 == 0:
                time.sleep(random.randint(18, 28))

        self.flush()
        self.write_progress({"phase": "done", "days_covered": len(set(self.days_done))})
        print(
            json.dumps(
                {
                    "new_unique": len(self.new_rows),
                    "total_unique": self.start_unique + len(self.new_rows),
                    "premium_new": self.premium_new,
                    "days_covered": len(set(self.days_done)),
                    "days_with_new": len(self.days_with_new),
                    "jobs_ok": self.jobs_ok,
                    "jobs_429": self.jobs_429,
                    "pages_ok": self.pages_ok,
                    "pages_429": self.pages_429,
                    "pow_solves": self.client.solved,
                },
                indent=2,
            ),
            flush=True,
        )
        print("EXAMPLES", flush=True)
        shown = 0
        for r in self.new_rows:
            print(
                r["url"],
                r.get("created_at"),
                r.get("price_raw"),
                r.get("domains"),
                (r.get("text") or "")[:110].replace("\n", " "),
                flush=True,
            )
            shown += 1
            if shown >= 8:
                break
        return 0


if __name__ == "__main__":
    raise SystemExit(DailyCollector().run())
