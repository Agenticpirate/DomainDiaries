#!/usr/bin/env python3
"""Date-sliced nitter.poast.org search for domain-sale tweets.

Uses since:/until: operators (and since/until form params) so results are
older posts, not the same recent first page. Not x.com / not official X API.
Every kept record has https://x.com/{user}/status/{id} from real HTML.
"""
from __future__ import annotations

import json
import random
import re
import sys
import time
import urllib.parse
from datetime import datetime, timezone
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
XCANCEL_PATH = DATA / "xcancel-sales.jsonl"
PROGRESS_PATH = DATA / "collect-progress-search.json"
RAW = DATA / "raw"

QUERIES = [
    "just sold domain",
    "sold for .com",
    "sold for .ai",
    "just sold .io",
    "sold via Sedo",
    "sold via Afternic",
    "sold via Atom",
    "sold via Spaceship",
    '"just sold" #domains',
    "NameBio sold",
    "closed a domain",
    "sold my domain",
    "BIN sold .com",
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
    seen: set[str] = set()
    for p in (SALES_PATH, TWEETS_PATH, XCANCEL_PATH):
        seen |= load_numeric_ids(p)
    return seen


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
    with path.open("a", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def month_windows(y0: int, m0: int, y1: int, m1: int) -> list[tuple[str, str]]:
    """Inclusive start month through inclusive end month → (since, until) pairs.
    until is the first day of the following month (Twitter until is exclusive).
    """
    out: list[tuple[str, str]] = []
    y, m = y0, m0
    while (y, m) <= (y1, m1):
        since = f"{y}-{m:02d}-01"
        nm, ny = m + 1, y
        if nm == 13:
            nm, ny = 1, y + 1
        until = f"{ny}-{nm:02d}-01"
        out.append((since, until))
        m += 1
        if m == 13:
            m, y = 1, y + 1
    return out


def build_windows() -> list[tuple[str, str]]:
    """Older-first mix: skip the current month (same recent page)."""
    # 2018–2022 half-year, 2023 quarterly, 2024–2026-07 monthly
    wins: list[tuple[str, str]] = []
    # half-year 2018-2022
    for y in range(2018, 2023):
        wins.append((f"{y}-01-01", f"{y}-07-01"))
        wins.append((f"{y}-07-01", f"{y + 1}-01-01"))
    # quarterly 2023
    for m in (1, 4, 7, 10):
        nm = m + 3
        ny = 2023
        if nm > 12:
            nm, ny = nm - 12, 2024
        wins.append((f"2023-{m:02d}-01", f"{ny}-{nm:02d}-01"))
    # monthly 2024-01 .. 2026-07 (skip 2026-08 = current recent page)
    wins.extend(month_windows(2024, 1, 2026, 7))
    return wins


class SearchCollector:
    def __init__(self) -> None:
        self.client = Client()
        self.seen = load_all_seen()
        self.start_unique = len(self.seen)
        self.new_rows: list[dict[str, Any]] = []
        self.premium_new = 0
        self.queries_run: list[str] = []
        self.windows_done: list[str] = []
        self.errors: list[str] = []
        self.pages_ok = 0
        self.pages_429 = 0
        self.pages_empty = 0
        self.flushed = 0
        self.jobs_ok = 0
        self.jobs_429 = 0
        self.jobs_empty = 0

    def write_progress(self, extra: dict[str, Any] | None = None) -> None:
        examples = []
        for r in self.new_rows:
            if r.get("url") and r.get("id"):
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
            "new_unique": len(self.new_rows),
            "total_unique": self.start_unique + len(self.new_rows),
            "start_unique": self.start_unique,
            "premium_new": self.premium_new,
            "flushed": self.flushed,
            "queries": QUERIES,
            "queries_run": self.queries_run[-80:],
            "windows_done": self.windows_done[-80:],
            "jobs_ok": self.jobs_ok,
            "jobs_429": self.jobs_429,
            "jobs_empty": self.jobs_empty,
            "pages_ok": self.pages_ok,
            "pages_429": self.pages_429,
            "pages_empty": self.pages_empty,
            "pow_solves": self.client.solved,
            "errors": self.errors[-50:],
            "examples": examples,
            "note": "Date-sliced nitter search. Every url is https://x.com/{user}/status/{id}. Not invented. Not official X API.",
        }
        if extra:
            payload.update(extra)
        PROGRESS_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def refresh_seen(self) -> None:
        """Pick up IDs written by any parallel collector."""
        disk = load_all_seen()
        self.seen |= disk

    def flush(self) -> None:
        self.refresh_seen()
        pending = []
        for r in self.new_rows[self.flushed :]:
            if r["id"] in load_numeric_ids(SALES_PATH) or r["id"] in load_numeric_ids(TWEETS_PATH):
                continue
            pending.append(r)
        if pending:
            append_jsonl(SALES_PATH, pending)
            prem = [r for r in pending if r.get("premium_tier")]
            append_jsonl(PREMIUM_PATH, prem)
            append_jsonl(TWEETS_PATH, [tweet_row(r) for r in pending])
        self.flushed = len(self.new_rows)
        self.write_progress()

    def fetch_page(self, url: str) -> tuple[int, str]:
        last_code, last_html = 0, ""
        for attempt in range(3):
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
                except Exception:
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

    def collect_job(self, query: str, since: str, until: str, max_pages: int = 30) -> str:
        """Return 'ok' | 'empty' | '429' | 'block'."""
        q = f"{query} since:{since} until:{until}"
        label = f"{query} [{since}..{until})"
        path = "/search?f=tweets&q=" + urllib.parse.quote(q, safe="")
        # also pass form params (nitter search panel)
        path += f"&since={since}&until={until}"
        next_url = BASE + path
        pages = 0
        kept = 0
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
                (RAW / "blocked-search.html").write_text(page[:12000], encoding="utf-8")
                return "block"
            items, more = parse_items(page)
            if items:
                saw_items = True
                self.pages_ok += 1
            else:
                self.pages_empty += 1
            new_here = 0
            for it in items:
                tid = str(it.get("id") or "")
                if not tid.isdigit() or tid in self.seen:
                    continue
                user = it.get("username") or ""
                if not user:
                    continue
                text = it.get("text") or ""
                parsed = parse_sale(text)
                if not keep_record(text, parsed, user):
                    continue
                self.seen.add(tid)
                rec = {
                    "id": tid,
                    "url": f"https://x.com/{user}/status/{tid}",
                    "tweet_url": f"https://x.com/{user}/status/{tid}",
                    "text": text,
                    "created_at": it.get("created_at"),
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
                kept += 1
                new_here += 1
            print(
                f"  {label} p={pages} code={code} items={len(items)} new={new_here} "
                f"more={bool(more)} total_new={len(self.new_rows)}",
                flush=True,
            )
            if not items:
                break
            if more:
                if more.startswith("http"):
                    next_url = more
                elif more.startswith("/"):
                    next_url = BASE + more
                else:
                    path_only = urllib.parse.urlparse(next_url).path
                    next_url = BASE + path_only + (more if more.startswith("?") else "?" + more)
                time.sleep(0.75)
            else:
                next_url = None
        return "ok" if saw_items else "empty"

    def run(self) -> int:
        DATA.mkdir(parents=True, exist_ok=True)
        RAW.mkdir(parents=True, exist_ok=True)
        windows = build_windows()
        done = set()
        if PROGRESS_PATH.is_file():
            try:
                prev = json.loads(PROGRESS_PATH.read_text(encoding="utf-8"))
                done = set(prev.get("windows_done") or [])
                # keep prior run's new_unique in progress extras
                self.prior_new = int(prev.get("new_unique") or 0)
            except Exception:
                self.prior_new = 0
        else:
            self.prior_new = 0
        windows = [(s, u) for (s, u) in windows if f"{s}..{u}" not in done]
        print(
            f"start unique={self.start_unique} queries={len(QUERIES)} "
            f"windows={len(windows)} skipped_done={len(done)} "
            f"jobs={len(QUERIES) * len(windows)}",
            flush=True,
        )
        self.windows_done = list(done)
        self.write_progress({"phase": "start", "window_count": len(windows), "resumed_skip": sorted(done)})

        # Warm POW cookie
        code, html = self.fetch_page(BASE + "/search?f=tweets&q=just+sold+domain+since%3A2024-01-01+until%3A2024-02-01")
        print(f"warmup code={code} pow={self.client.solved} items={html.count('timeline-item')}", flush=True)

        # Interleave: for each window (older first), run all queries.
        # On 429, sleep 20-40s and continue the NEXT query (not retry same).
        for since, until in windows:
            win_label = f"{since}..{until}"
            print(f"WINDOW {win_label} new={len(self.new_rows)}", flush=True)
            for q in QUERIES:
                label = f"{q} [{since}..{until})"
                self.queries_run.append(label)
                try:
                    status = self.collect_job(q, since, until, max_pages=30)
                except Exception as e:
                    self.errors.append(f"exc {label}: {e}")
                    print(f"  EXC {label}: {e}", flush=True)
                    status = "block"
                if status == "ok":
                    self.jobs_ok += 1
                elif status == "empty":
                    self.jobs_empty += 1
                elif status == "429":
                    self.jobs_429 += 1
                    wait = random.randint(20, 40)
                    print(f"  sleep {wait}s after 429, next query", flush=True)
                    time.sleep(wait)
                self.flush()
                time.sleep(0.35)
            self.windows_done.append(win_label)
            self.write_progress({"phase": "running", "current_window": win_label})
            # extra cool-down if this window was spicy
            if self.pages_429 and self.pages_429 % 6 == 0:
                time.sleep(random.randint(20, 30))

        self.flush()
        self.write_progress({"phase": "done"})
        print(
            json.dumps(
                {
                    "new_unique": len(self.new_rows),
                    "total_unique": self.start_unique + len(self.new_rows),
                    "premium_new": self.premium_new,
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
    raise SystemExit(SearchCollector().run())
