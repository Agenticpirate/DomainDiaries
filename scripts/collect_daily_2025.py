#!/usr/bin/env python3
"""Day-by-day nitter.poast.org search for 2025 domain-sale tweets.

Not x.com / not official X API. Every kept record has
https://x.com/{user}/status/{id} and a created_at in
[2025-01-01, 2026-08-15]. Nothing is invented.
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
XCANCEL_PATH = DATA / "xcancel-sales.jsonl"
WALL_PATH = DATA / "tweets-2025-2026.jsonl"
PROGRESS_PATH = DATA / "collect-progress-daily.json"
LOCK_PATH = DATA / "raw" / "append.lock"
RAW = DATA / "raw"

WIN0 = date(2025, 1, 1)
WIN1 = date(2026, 8, 15)
WALK_START = date(2025, 1, 1)
WALK_END = date(2025, 12, 31)
MUST_COVER_THROUGH = date(2025, 6, 30)
TARGET_IN_WINDOW = 6000

PRIMARY = [
    '"just sold" domain',
    '"sold for" .com',
    '"sold for" .ai',
    "NameBio sold",
    "sold via Sedo",
    "sold via Afternic",
]
THIN_EXTRA = [
    "from:NameBio",
    "from:DomainNews24",
    "from:FinTechNames",
    "from:DomainGang",
    '"just sold" .com',
    '"just sold" .ai',
    '"sold for" .io',
    "sold via Atom",
    "sold my domain",
    '"just closed" domain',
    "#domains sold",
    "closed a domain",
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


def parse_day(ca: str | None) -> date | None:
    if not ca:
        return None
    try:
        return date.fromisoformat(ca[:10])
    except ValueError:
        return None


def in_window(ca: str | None) -> bool:
    d = parse_day(ca)
    return bool(d and WIN0 <= d <= WIN1)


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
        "username": rec.get("username"),
        "text": rec.get("text"),
        "created_at": rec.get("created_at"),
        "domains": rec.get("domains") or [],
        "price_usd": rec.get("price_usd"),
        "price_raw": rec.get("price_raw"),
        "premium_tier": rec.get("premium_tier"),
        "source": rec.get("source") or "x-public",
        "collected_at": rec.get("collected_at"),
        "query": rec.get("query"),
    }


def locked_append(path: Path, rows: list[dict[str, Any]]) -> None:
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


def iter_jsonl(path: Path):
    if not path.is_file():
        return
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def count_in_window() -> tuple[int, dict[str, int]]:
    """Unique numeric tweet ids with created_at in wall window."""
    by_month: dict[str, int] = {}
    seen: set[str] = set()
    for path in (SALES_PATH, TWEETS_PATH):
        for obj in iter_jsonl(path):
            tid = str(obj.get("id") or "")
            if not tid.isdigit() or tid in seen:
                continue
            ca = obj.get("created_at") or ""
            if not in_window(ca):
                continue
            seen.add(tid)
            m = ca[:7]
            by_month[m] = by_month.get(m, 0) + 1
    return len(seen), by_month


def rebuild_wall() -> int:
    """Write ALL unique in-window tweets (old+new) to tweets-2025-2026.jsonl."""
    best: dict[str, dict[str, Any]] = {}
    for path in (SALES_PATH, TWEETS_PATH):
        for obj in iter_jsonl(path):
            tid = str(obj.get("id") or "")
            if not tid.isdigit():
                continue
            ca = obj.get("created_at") or ""
            if not in_window(ca):
                continue
            url = obj.get("url") or obj.get("tweet_url") or ""
            user = obj.get("username") or ""
            if not url.startswith("https://x.com/") or "/status/" not in url:
                if user:
                    url = f"https://x.com/{user}/status/{tid}"
                else:
                    continue
            row = tweet_row({
                "id": tid,
                "url": url,
                "username": user,
                "text": obj.get("text"),
                "created_at": ca,
                "domains": obj.get("domains") or [],
                "price_usd": obj.get("price_usd"),
                "price_raw": obj.get("price_raw"),
                "premium_tier": obj.get("premium_tier"),
                "source": obj.get("source") or "x-public",
                "collected_at": obj.get("collected_at"),
                "query": obj.get("query"),
            })
            prev = best.get(tid)
            if prev is None:
                best[tid] = row
            else:
                # prefer row that already lives in tweets.jsonl shape / has text
                if (row.get("text") and not prev.get("text")) or (
                    path == TWEETS_PATH
                ):
                    best[tid] = row
    rows = sorted(best.values(), key=lambda r: (r.get("created_at") or "", r["id"]))
    tmp = WALL_PATH.with_suffix(".jsonl.tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    tmp.replace(WALL_PATH)
    return len(rows)


class DailyCollector:
    def __init__(self) -> None:
        self.client = Client()
        self.seen = load_all_seen()
        self.start_unique = len(self.seen)
        self.start_in_window, self.by_month = count_in_window()
        self.new_rows: list[dict[str, Any]] = []
        self.premium_new = 0
        self.days_done: list[str] = []
        self.jobs_done: set[str] = set()
        self.queries_run: list[str] = []
        self.errors: list[str] = []
        self.pages_ok = 0
        self.pages_429 = 0
        self.pages_empty = 0
        self.jobs_ok = 0
        self.jobs_429 = 0
        self.jobs_empty = 0
        self.jobs_block = 0
        self.consecutive_hard = 0
        self.examples: list[dict[str, Any]] = []
        self._load_progress()

    def _load_progress(self) -> None:
        if not PROGRESS_PATH.is_file():
            return
        try:
            prev = json.loads(PROGRESS_PATH.read_text(encoding="utf-8"))
        except Exception:
            return
        self.days_done = list(prev.get("days_done") or [])
        self.jobs_done = set(prev.get("jobs_done") or [])
        self.queries_run = list(prev.get("queries_run") or [])[-80:]

    def write_progress(self, extra: dict[str, Any] | None = None) -> None:
        inw, by_month = count_in_window()
        self.by_month = by_month
        payload = {
            "updated_at": now_iso(),
            "frontend": "nitter.poast.org",
            "source": "x-public",
            "phase": (extra or {}).get("phase", "running"),
            "days_done": self.days_done,
            "days_done_count": len(self.days_done),
            "new_count": len(self.new_rows),
            "in_window_total": inw,
            "start_in_window": self.start_in_window,
            "start_unique": self.start_unique,
            "premium_new": self.premium_new,
            "by_month": dict(sorted(by_month.items())),
            "queries": PRIMARY,
            "queries_run": self.queries_run[-80:],
            "jobs_done": sorted(self.jobs_done)[-200:],
            "jobs_ok": self.jobs_ok,
            "jobs_429": self.jobs_429,
            "jobs_empty": self.jobs_empty,
            "jobs_block": self.jobs_block,
            "pages_ok": self.pages_ok,
            "pages_429": self.pages_429,
            "pages_empty": self.pages_empty,
            "pow_solves": self.client.solved,
            "errors": self.errors[-40:],
            "examples": self.examples[:8],
            "note": (
                "Day-by-day nitter.poast.org search. Every url is "
                "https://x.com/{user}/status/{id}. Not invented. Not official X API."
            ),
        }
        if extra:
            payload.update(extra)
        PROGRESS_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def flush(self, rows: list[dict[str, Any]]) -> None:
        if not rows:
            self.write_progress()
            return
        disk = load_all_seen()
        self.seen |= disk
        keep = []
        for r in rows:
            if r["id"] in disk:
                continue
            if not in_window(r.get("created_at")):
                continue
            if not r.get("url") or "/status/" not in r["url"]:
                continue
            disk.add(r["id"])
            self.seen.add(r["id"])
            keep.append(r)
        if keep:
            locked_append(SALES_PATH, keep)
            locked_append(PREMIUM_PATH, [r for r in keep if r.get("premium_tier")])
            locked_append(TWEETS_PATH, [tweet_row(r) for r in keep])
        self.write_progress()

    def fetch_page(self, url: str) -> tuple[int, str]:
        last_code, last_html = 0, ""
        for attempt in range(4):
            try:
                code, html = self.client.fetch(url, retries=3)
            except Exception as e:
                self.errors.append(f"fetch exc {e}")
                time.sleep(2 + attempt)
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
                wait = 20 + 10 * attempt + random.randint(0, 12)
                print(f"    429 sleep {wait}s", flush=True)
                self.pages_429 += 1
                time.sleep(wait)
                continue
            return code, html
        return last_code, last_html

    def collect_job(self, query: str, since: str, until: str, max_pages: int = 6) -> str:
        """Return 'ok' | 'empty' | '429' | 'block'."""
        job_key = f"{query}|{since}|{until}"
        if job_key in self.jobs_done:
            return "ok"
        q = f"{query} since:{since} until:{until}"
        label = f"{query} [{since}..{until})"
        path = "/search?f=tweets&q=" + urllib.parse.quote(q, safe="")
        path += f"&since={since}&until={until}"
        next_url = BASE + path
        pages = 0
        kept = 0
        saw_items = False
        pending: list[dict[str, Any]] = []
        while next_url and pages < max_pages:
            pages += 1
            code, page = self.fetch_page(next_url)
            if code == 429 or "Too Many Requests" in page:
                self.errors.append(f"429 {label} page={pages}")
                print(f"  429 {label} page={pages}", flush=True)
                if pending:
                    self.flush(pending)
                return "429"
            if "Verifying your browser" in page or (
                code >= 400 and "timeline-item" not in page
            ):
                self.errors.append(f"block code={code} {label} page={pages}")
                print(f"  block code={code} {label} page={pages}", flush=True)
                RAW.mkdir(parents=True, exist_ok=True)
                (RAW / "blocked-daily.html").write_text(page[:12000], encoding="utf-8")
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
                created = it.get("created_at")
                if not in_window(created):
                    continue
                parsed = parse_sale(text)
                if not keep_record(text, parsed, user):
                    continue
                self.seen.add(tid)
                rec = {
                    "id": tid,
                    "url": f"https://x.com/{user}/status/{tid}",
                    "tweet_url": f"https://x.com/{user}/status/{tid}",
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
                pending.append(rec)
                self.new_rows.append(rec)
                if rec.get("premium_tier"):
                    self.premium_new += 1
                if len(self.examples) < 8:
                    self.examples.append(
                        {
                            "url": rec["url"],
                            "username": user,
                            "domains": rec["domains"],
                            "price_usd": rec["price_usd"],
                            "created_at": created,
                            "query": label,
                            "text": (text or "")[:160],
                        }
                    )
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
                time.sleep(0.7)
            else:
                next_url = None
        if pending:
            self.flush(pending)
        self.jobs_done.add(job_key)
        self.queries_run.append(label)
        return "ok" if saw_items else "empty"

    def run_job(self, query: str, since: str, until: str, max_pages: int = 6) -> str:
        try:
            status = self.collect_job(query, since, until, max_pages=max_pages)
        except Exception as e:
            self.errors.append(f"exc {query} [{since}..{until}): {e}")
            print(f"  EXC {query} [{since}..{until}): {e}", flush=True)
            status = "block"
        if status == "ok":
            self.jobs_ok += 1
            self.consecutive_hard = 0
        elif status == "empty":
            self.jobs_empty += 1
            self.consecutive_hard = 0
        elif status == "429":
            self.jobs_429 += 1
            self.consecutive_hard += 1
            wait = random.randint(22, 40)
            print(f"  sleep {wait}s after 429, next query", flush=True)
            time.sleep(wait)
        else:
            self.jobs_block += 1
            self.consecutive_hard += 1
            time.sleep(2)
        time.sleep(0.35)
        return status

    def exhausted(self) -> bool:
        return self.consecutive_hard >= 12

    def should_stop(self, day: date) -> bool:
        inw, _ = count_in_window()
        covered_june = any(d >= "2025-06-30" for d in self.days_done) or day >= MUST_COVER_THROUGH
        if inw >= TARGET_IN_WINDOW and covered_june and day >= MUST_COVER_THROUGH:
            return True
        return False

    def queries_for(self, day: date) -> list[str]:
        # Primary rotation every day. Extras only when the day is empty.
        return list(PRIMARY)

    def run(self) -> int:
        DATA.mkdir(parents=True, exist_ok=True)
        RAW.mkdir(parents=True, exist_ok=True)
        print(
            f"start unique={self.start_unique} in_window={self.start_in_window} "
            f"days_already={len(self.days_done)}",
            flush=True,
        )
        n = rebuild_wall()
        print(f"wall baseline {n} -> {WALL_PATH}", flush=True)
        self.write_progress({"phase": "start", "wall_count": n})

        code, html = self.fetch_page(
            BASE + "/search?f=tweets&q="
            + urllib.parse.quote('"just sold" domain since:2025-01-01 until:2025-01-02', safe="")
            + "&since=2025-01-01&until=2025-01-02"
        )
        print(
            f"warmup code={code} pow={self.client.solved} items={html.count('timeline-item')}",
            flush=True,
        )

        day = WALK_START
        done_set = set(self.days_done)
        # After the first week of true day-by-day, walk 3-day slices so we
        # can cover through June (and the rest of 2025) before poast dies.
        slice_days = 3
        while day <= WALK_END:
            day_s = day.isoformat()
            if day_s in done_set:
                day = day + timedelta(days=1)
                continue
            # 3-day window; until is exclusive
            until_d = min(day + timedelta(days=slice_days), WALK_END + timedelta(days=1))
            nxt = day + timedelta(days=1)
            until_s = until_d.isoformat()
            print(
                f"SLICE {day_s}..{until_s} new={len(self.new_rows)} inw~{self.start_in_window + len(self.new_rows)}",
                flush=True,
            )
            empty_qs: list[str] = []
            day_new_before = len(self.new_rows)
            for q in self.queries_for(day):
                status = self.run_job(q, day_s, until_s, max_pages=4)
                if status == "empty":
                    empty_qs.append(q)
                if self.exhausted():
                    print("poast exhausted (consecutive hard failures)", flush=True)
                    self._finish("exhausted")
                    return 0
            gained = len(self.new_rows) - day_new_before
            # Thin-month extras only when the primary rotation found nothing.
            if gained == 0 and day <= date(2025, 6, 30):
                print(f"  thin-day extras {day_s}", flush=True)
                for q in THIN_EXTRA:
                    status = self.run_job(q, day_s, until_s, max_pages=3)
                    if status == "empty":
                        empty_qs.append(q)
                    if self.exhausted():
                        print("poast exhausted (consecutive hard failures)", flush=True)
                        self._finish("exhausted")
                        return 0
                gained = len(self.new_rows) - day_new_before
            mark = day
            while mark < until_d:
                ms = mark.isoformat()
                if ms not in done_set:
                    self.days_done.append(ms)
                    done_set.add(ms)
                mark += timedelta(days=1)
            if day.day == 1 or day.month != until_d.month:
                rebuild_wall()
            self.write_progress({"phase": "running", "current_day": day_s, "day_new": gained, "slice_until": until_s})
            # Continue through all of 2025; stop only if exhausted.
            day = until_d

        self._finish("done")
        return 0

    def _finish(self, phase: str) -> None:
        wall_n = rebuild_wall()
        inw, by_month = count_in_window()
        self.write_progress(
            {
                "phase": phase,
                "wall_count": wall_n,
                "in_window_total": inw,
                "by_month": dict(sorted(by_month.items())),
            }
        )
        print(
            json.dumps(
                {
                    "phase": phase,
                    "new_unique": len(self.new_rows),
                    "in_window_total": inw,
                    "days_covered": len(self.days_done),
                    "premium_new": self.premium_new,
                    "jobs_ok": self.jobs_ok,
                    "jobs_429": self.jobs_429,
                    "pages_ok": self.pages_ok,
                    "pow_solves": self.client.solved,
                    "wall_count": wall_n,
                },
                indent=2,
            ),
            flush=True,
        )
        print("EXAMPLES", flush=True)
        for r in self.new_rows[:8]:
            print(
                r["url"],
                r.get("price_raw"),
                r.get("domains"),
                (r.get("text") or "")[:110].replace("\n", " "),
                flush=True,
            )


if __name__ == "__main__":
    raise SystemExit(DailyCollector().run())
