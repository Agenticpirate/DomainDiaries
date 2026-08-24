#!/usr/bin/env python3
"""Complementary from:USER date-window search on nitter.poast.org."""
from __future__ import annotations

import fcntl
import json
import re
import sys
import time
import urllib.parse
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

DATA = ROOT / "data"
SALES_PATH = DATA / "sales.jsonl"
PREMIUM_PATH = DATA / "premium.jsonl"
TWEETS_PATH = DATA / "tweets.jsonl"
XCANCEL_PATH = DATA / "xcancel-sales.jsonl"
PROGRESS_PATH = DATA / "collect-progress-continue.json"
LOCK_PATH = DATA / "raw" / "append.lock"

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
}
INDUSTRY_ALL = {x.lower() for x in INDUSTRY} | SALE_ACCOUNTS

USERS = [
    "NameBio", "DomainNews24", "DomainGang", "FinTechNames", "katerleonid",
    "SedoDaveEvanson", "andrewrosener", "ishmilly", "jamesiles", "rundns",
    "DomainNameWire", "swethayenugula", "MediaOptions", "domainretail",
    "DoctorBrandx", "justdropped", "BridgedDomains", "ibuild_io",
    "TonyNames", "DomainLabs", "NameHubs", "DNdomainname",
]


def load_numeric_ids(path: Path) -> set[str]:
    seen: set[str] = set()
    if not path.is_file() or path.stat().st_size == 0:
        return seen
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
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


def is_escrow_sale(text: str, parsed: dict[str, Any]) -> bool:
    domains = [d.lower() for d in (parsed.get("domains") or [])]
    only_escrow = set(domains) <= {"escrow.com"} and bool(domains)
    t = (text or "").lower()
    saleish = bool(re.search(
        r"\b(just\s+sold|sold\s+for|domain\s+sold|sold\s+the\s+domain|"
        r"closed\s+the\s+sale|sale\s+closed)\b", t))
    other_domain = any(d != "escrow.com" for d in domains)
    if only_escrow and not saleish:
        return False
    if other_domain and saleish:
        return True
    if saleish and parsed.get("price_usd") and re.search(r"\bdomain", t):
        return True
    return False


def keep_record(text: str, parsed: dict[str, Any], username: str) -> bool:
    user = (username or "").lower()
    if user == "escrow_com":
        return is_escrow_sale(text, parsed)
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


def windows() -> list[tuple[str, str]]:
    """Recent-first: monthly 2026-07..2024-01, quarterly 2023-2020."""
    out: list[tuple[str, str]] = []
    # monthly 2026-07 down to 2024-01
    y, m = 2026, 7
    while (y, m) >= (2024, 1):
        nm, ny = m + 1, y
        if nm == 13:
            nm, ny = 1, y + 1
        out.append((f"{y}-{m:02d}-01", f"{ny}-{nm:02d}-01"))
        m -= 1
        if m == 0:
            m, y = 12, y - 1
    # quarterly 2023-2020
    for y in range(2023, 2019, -1):
        for m in (10, 7, 4, 1):
            nm = m + 3
            ny = y
            if nm > 12:
                nm, ny = nm - 12, y + 1
            out.append((f"{y}-{m:02d}-01", f"{ny}-{nm:02d}-01"))
    return out


class Col:
    def __init__(self) -> None:
        self.client = Client()
        self.seen = load_all_seen()
        self.start_unique = len(self.seen)
        self.mine: list[dict[str, Any]] = []
        self.premium_new = 0
        self.queries_run: list[str] = []
        self.errors: list[str] = []
        self.pages_ok = 0
        self.pages_429 = 0

    def write_progress(self, extra: dict | None = None) -> None:
        payload = {
            "updated_at": now_iso(),
            "new_count": len(self.mine),
            "total_unique_tweet_ids": len(load_all_seen()),
            "premium_new": self.premium_new,
            "queries_run": self.queries_run[-80:],
            "errors": self.errors[-30:],
            "pages_ok": self.pages_ok,
            "pages_429": self.pages_429,
            "pow_solves": self.client.solved,
            "start_unique": self.start_unique,
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
            disk.add(r["id"])
            self.seen.add(r["id"])
            keep.append(r)
        if keep:
            locked_append(SALES_PATH, keep)
            locked_append(PREMIUM_PATH, [r for r in keep if r.get("premium_tier")])
            locked_append(TWEETS_PATH, [tweet_row(r) for r in keep])
        self.write_progress()

    def fetch_page(self, url: str) -> tuple[int, str]:
        last = (0, "")
        for attempt in range(3):
            code, html = self.client.fetch(url, retries=3)
            last = (code, html)
            if code == 429 or "Too Many Requests" in html:
                self.pages_429 += 1
                wait = 22 + 14 * attempt
                print(f"    429 sleep {wait}s", flush=True)
                time.sleep(wait)
                continue
            if "Verifying your browser" in html:
                time.sleep(0.5)
                continue
            return code, html
        return last

    def collect(self, url: str, query: str, max_pages: int) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        next_url = url
        for pages in range(1, max_pages + 1):
            code, page = self.fetch_page(next_url)
            if code == 429 or "Too Many Requests" in page:
                self.errors.append(f"429 {query} p={pages}")
                break
            if "Verifying your browser" in page or (code >= 400 and "timeline-item" not in page):
                self.errors.append(f"block {code} {query} p={pages}")
                break
            items, more = parse_items(page)
            self.pages_ok += 1
            new_here = 0
            for it in items:
                tid = it["id"]
                if not tid or not str(tid).isdigit() or tid in self.seen:
                    continue
                parsed = parse_sale(it["text"])
                if not keep_record(it["text"], parsed, it["username"]):
                    continue
                self.seen.add(tid)
                rec = {
                    "id": tid,
                    "url": f"https://x.com/{it['username']}/status/{tid}",
                    "tweet_url": f"https://x.com/{it['username']}/status/{tid}",
                    "text": it["text"],
                    "created_at": it["created_at"],
                    "author_id": None,
                    "username": it["username"],
                    "name": it["name"],
                    "domains": parsed["domains"],
                    "price_usd": parsed["price_usd"],
                    "price_raw": parsed["price_raw"],
                    "premium_tier": parsed["premium_tier"],
                    "likes": it["likes"],
                    "reposts": it["reposts"],
                    "quotes": 0,
                    "replies": it["replies"],
                    "query": query,
                    "source": "x-public",
                    "collected_at": now_iso(),
                }
                out.append(rec)
                self.mine.append(rec)
                if rec.get("premium_tier"):
                    self.premium_new += 1
                new_here += 1
            print(
                f"  {query} p={pages} code={code} items={len(items)} new={new_here} "
                f"more={bool(more)} mine={len(self.mine)}",
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
                    path = urllib.parse.urlparse(next_url).path
                    next_url = BASE + path + (more if more.startswith("?") else "?" + more)
                time.sleep(0.95)
            else:
                break
        return out

    def run_search(self, label: str, q: str, max_pages: int) -> None:
        self.queries_run.append(label)
        path = "/search?f=tweets&q=" + urllib.parse.quote(q, safe="")
        print(f"SEARCH {label}", flush=True)
        try:
            rows = self.collect(BASE + path, label, max_pages)
            self.flush(rows)
        except Exception as e:
            self.errors.append(f"exc {label}: {e}")
            print(f"  EXC {label}: {e}", flush=True)
            self.write_progress()
        time.sleep(0.4)


def main() -> int:
    col = Col()
    print(f"start unique={col.start_unique}", flush=True)
    col.write_progress({"phase": "start"})
    wins = windows()
    # NameBio first — daily sale reports, highest yield
    priority = ["NameBio", "DomainNews24", "FinTechNames", "DomainGang", "katerleonid"]
    rest = [u for u in USERS if u not in priority]
    ordered = priority + rest
    for user in ordered:
        for since, until in wins:
            q = f"from:{user} since:{since} until:{until}"
            col.run_search(f"from:{user} {since}", q, 8)
            if len(col.mine) >= 7000:
                break
        if len(col.mine) >= 7000:
            break
    col.write_progress({"phase": "done"})
    print(json.dumps({
        "new_count": len(col.mine),
        "total_unique_tweet_ids": len(load_all_seen()),
        "premium_new": col.premium_new,
        "queries": len(col.queries_run),
        "errors": len(col.errors),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
