#!/usr/bin/env python3
"""Continue public Nitter collection from nitter.poast.org. Append-only."""
from __future__ import annotations

import json
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
from parse_sale import parse_sale as _ps  # noqa: E402

DATA = ROOT / "data"
SALES_PATH = DATA / "sales.jsonl"
PREMIUM_PATH = DATA / "premium.jsonl"
TWEETS_PATH = DATA / "tweets.jsonl"
XCANCEL_PATH = DATA / "xcancel-sales.jsonl"
PROGRESS_PATH = DATA / "collect-progress.json"
RAW = DATA / "raw"

SALE_ACCOUNTS = {
    "namebio",
    "domainnews24",
    "domaingang",
    "katerleonid",
    "fintechnames",
    "domainretail",
    "doctorbrandx",
    "justdropped",
    "bridgeddomains",
    "ibuild_io",
    "domainlabs",
    "namehubs",
    "dndomainname",
    "andrewrosener",
    "domainnamewire",
    "sedodaveevanson",
    "ishmilly",
    "jamesiles",
    "rundns",
    "mediaoptions",
    "swethayenugula",
    "domaininvesting",
    "domainshane",
    "tonynames",
    "sedo",
    "afternic",
    "godaddyauctions",
    "mrpremiumdotcom",
    "derick_sedo",
    "thedomainagents",
    "dinvesting",
    "contactowner",
    "unlockeddomains",
    "domain_raider",
    "360domain",
    "memorabledn",
    "dropdax",
    "domainjobcom",
    "atomhq",
    "lumis_com",
    "jeffreymgabriel",
    "dinvesting",
    "escrow_com",
    "namejet",
    "namepros",
    "morganlinton",
    "andrewallemann",
    "dnjournal",
    "domainsherpa",
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


def is_escrow_sale(text: str, parsed: dict[str, Any]) -> bool:
    domains = [d.lower() for d in (parsed.get("domains") or [])]
    only_escrow = set(domains) <= {"escrow.com"} and bool(domains)
    t = (text or "").lower()
    saleish = bool(
        re.search(
            r"\b(just\s+sold|sold\s+for|domain\s+sold|sold\s+the\s+domain|"
            r"closed\s+the\s+sale|sale\s+closed)\b",
            t,
        )
    )
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


def append_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


class Collector:
    def __init__(self) -> None:
        self.client = Client()
        self.seen = set()
        for p in (SALES_PATH, TWEETS_PATH, XCANCEL_PATH):
            self.seen |= load_numeric_ids(p)
        self.start_unique = len(self.seen)
        self.new_rows: list[dict[str, Any]] = []
        self.premium_new = 0
        self.queries_run: list[str] = []
        self.errors: list[str] = []
        self.pages_ok = 0
        self.pages_429 = 0
        self.flushed = 0

    def write_progress(self, extra: dict[str, Any] | None = None) -> None:
        payload = {
            "updated_at": now_iso(),
            "new_count": len(self.new_rows),
            "total_unique_tweet_ids": self.start_unique + len(self.new_rows),
            "premium_new": self.premium_new,
            "queries_run": self.queries_run,
            "errors": self.errors[-40:],
            "pages_ok": self.pages_ok,
            "pages_429": self.pages_429,
            "pow_solves": self.client.solved,
            "start_unique": self.start_unique,
        }
        if extra:
            payload.update(extra)
        PROGRESS_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def flush(self) -> None:
        pending = self.new_rows[self.flushed :]
        if not pending:
            self.write_progress()
            return
        append_jsonl(SALES_PATH, pending)
        prem = [r for r in pending if r.get("premium_tier")]
        append_jsonl(PREMIUM_PATH, prem)
        append_jsonl(TWEETS_PATH, [tweet_row(r) for r in pending])
        self.flushed += len(pending)
        self.write_progress({"flushed": self.flushed})

    def fetch_page(self, url: str) -> tuple[int, str]:
        last_code, last_html = 0, ""
        for attempt in range(4):
            code, html = self.client.fetch(url, retries=3)
            last_code, last_html = code, html
            if code == 429 or "Too Many Requests" in html:
                self.pages_429 += 1
                wait = 18 + 12 * attempt
                print(f"    429 sleep {wait}s attempt={attempt+1}", flush=True)
                time.sleep(wait)
                continue
            if "Verifying your browser" in html:
                print("    POW still present, retry", flush=True)
                time.sleep(0.6)
                continue
            return code, html
        return last_code, last_html

    def collect_url(self, url: str, query: str, max_pages: int) -> int:
        next_url = url
        pages = 0
        kept = 0
        empty_streak = 0
        while next_url and pages < max_pages:
            pages += 1
            code, page = self.fetch_page(next_url)
            if code == 429 or "Too Many Requests" in page:
                self.errors.append(f"429 {query} page={pages}")
                print(f"  give-up 429 q={query!r} page={pages}", flush=True)
                break
            if "Verifying your browser" in page or (
                code >= 400 and "timeline-item" not in page
            ):
                self.errors.append(f"block code={code} {query} page={pages}")
                print(f"  block code={code} q={query!r} page={pages}", flush=True)
                RAW.mkdir(parents=True, exist_ok=True)
                (RAW / "blocked-continue.html").write_text(page[:12000], encoding="utf-8")
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
                self.new_rows.append(rec)
                if rec.get("premium_tier"):
                    self.premium_new += 1
                kept += 1
                new_here += 1
            print(
                f"  page={pages} code={code} items={len(items)} new={new_here} "
                f"more={bool(more)} total_new={len(self.new_rows)}",
                flush=True,
            )
            if not items:
                empty_streak += 1
                if empty_streak >= 1:
                    break
            else:
                empty_streak = 0
            if more:
                if more.startswith("http"):
                    next_url = more
                elif more.startswith("/"):
                    next_url = BASE + more
                else:
                    path = urllib.parse.urlparse(next_url).path
                    next_url = BASE + path + (more if more.startswith("?") else "?" + more)
                time.sleep(0.85)
            else:
                next_url = None
        return kept

    def run_search(self, label: str, q: str, max_pages: int) -> None:
        path = "/search?f=tweets&q=" + urllib.parse.quote(q, safe="")
        print(f"SEARCH {label} q={q!r}", flush=True)
        self.queries_run.append(label)
        try:
            kept = self.collect_url(BASE + path, label, max_pages)
            print(f"  kept {kept} running_new={len(self.new_rows)}", flush=True)
        except Exception as e:
            self.errors.append(f"exc {label}: {e}")
            print(f"  EXC {label}: {e}", flush=True)
        self.flush()
        time.sleep(0.45)

    def run_profile(self, user: str, max_pages: int) -> None:
        label = f"profile:{user}"
        print(f"PROFILE {user}", flush=True)
        self.queries_run.append(label)
        try:
            kept = self.collect_url(f"{BASE}/{user}", label, max_pages)
            print(f"  kept {kept} running_new={len(self.new_rows)}", flush=True)
        except Exception as e:
            self.errors.append(f"exc {label}: {e}")
            print(f"  EXC {label}: {e}", flush=True)
        self.flush()
        time.sleep(0.45)


def date_windows() -> list[tuple[str, str]]:
    """Quarterly windows 2020-01 through 2026-08."""
    out: list[tuple[str, str]] = []
    bounds = []
    for y in range(2020, 2027):
        for m in (1, 4, 7, 10):
            if y == 2026 and m > 8:
                break
            bounds.append((y, m))
    bounds.append((2026, 8))
    for i, (y, m) in enumerate(bounds[:-1]):
        ny, nm = bounds[i + 1]
        out.append((f"{y}-{m:02d}-01", f"{ny}-{nm:02d}-01"))
    return out


def main() -> int:
    DATA.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)
    col = Collector()
    print(
        f"start unique tweet ids={col.start_unique} pow_ready",
        flush=True,
    )
    col.write_progress({"phase": "start"})

    # --- leftover nitter-raw that passed filter ---
    raw_path = RAW / "nitter-raw.jsonl"
    if raw_path.is_file():
        n_raw = 0
        for line in raw_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                o = json.loads(line)
            except json.JSONDecodeError:
                continue
            tid = str(o.get("id") or "")
            if not tid.isdigit() or tid in col.seen:
                continue
            text = o.get("text") or ""
            user = o.get("user") or ""
            parsed = parse_sale(text)
            if not keep_record(text, parsed, user):
                continue
            created = None
            date = o.get("date") or ""
            # "Aug 15, 2026 · 3:15 PM UTC"
            date = date.replace("·", " ").replace("\u00b7", " ")
            date = re.sub(r"\s+", " ", date).replace(" UTC", "").strip()
            for fmt in ("%b %d, %Y %I:%M %p",):
                try:
                    created = (
                        datetime.strptime(date, fmt)
                        .replace(tzinfo=timezone.utc)
                        .strftime("%Y-%m-%dT%H:%M:%S.000Z")
                    )
                    break
                except ValueError:
                    continue
            col.seen.add(tid)
            rec = {
                "id": tid,
                "url": f"https://x.com/{user}/status/{tid}",
                "tweet_url": f"https://x.com/{user}/status/{tid}",
                "text": text,
                "created_at": created,
                "author_id": None,
                "username": user,
                "name": None,
                "domains": parsed["domains"],
                "price_usd": parsed["price_usd"],
                "price_raw": parsed["price_raw"],
                "premium_tier": parsed["premium_tier"],
                "likes": 0,
                "reposts": 0,
                "quotes": 0,
                "replies": 0,
                "query": "nitter-raw",
                "source": "x-public",
                "collected_at": now_iso(),
            }
            col.new_rows.append(rec)
            if rec.get("premium_tier"):
                col.premium_new += 1
            n_raw += 1
        if n_raw:
            col.queries_run.append("nitter-raw")
            print(f"nitter-raw kept {n_raw}", flush=True)
            col.flush()

    # User-requested NEW keyword searches (not previously exhausted)
    searches = [
        ('"sold for" .ai', 28),
        ('"just sold" .io', 24),
        ('"just sold" .ai', 20),
        ('"sold for" .io', 24),
        ("closed domain $k", 16),
        ('"closed" domain $k', 12),
        ("sold via Sedo", 22),
        ("sold via Afternic", 22),
        ("sold via Atom", 20),
        ("sold via Spaceship", 16),
        ('"BIN" sold domain', 18),
        ("BIN sold domain", 12),
        ("sold via GoDaddy", 12),
        ("sold at Sedo", 16),
        ("sold at Afternic", 16),
        ("sold at Atom", 14),
        ("sold at Spaceship", 12),
        ("#domaininvesting sold", 16),
        ("#domaining sold", 14),
        ('"just sold" .net', 16),
        ('"sold for" .org', 14),
        ('"sold for" .co', 12),
        ("end user sold domain", 12),
        ("aftermarket sold domain", 12),
        ('"sale closed" domain', 10),
        ("NameBio sold", 8),  # already run; short extra
        ('"just sold" .com', 8),
    ]

    from_users = [
        "NameBio",
        "DomainNews24",
        "DomainGang",
        "andrewrosener",
        "SedoDaveEvanson",
        "ishmilly",
        "jamesiles",
        "rundns",
        "DomainNameWire",
        "swethayenugula",
        "MediaOptions",
        "Escrow_com",
        "katerleonid",
        "FinTechNames",
        "domainretail",
        "DoctorBrandx",
        "justdropped",
        "BridgedDomains",
        "ibuild_io",
        "TonyNames",
        "MrPremiumDotCom",
        "Derick_Sedo",
        "TheDomainAgents",
        "DInvesting",
        "atomHQ",
        "DomainLabs",
        "NameHubs",
        "DNdomainname",
        "DomainInvesting",
        "DomainShane",
        "ContactOwner",
        "unlockeddomains",
        "domain_raider",
        "DropDax",
        "MemorableDN",
        "360Domain",
    ]

    profiles = [
        "NameBio",
        "DomainNews24",
        "DomainGang",
        "andrewrosener",
        "Sedo",
        "Afternic",
        "GoDaddyAuctions",
        "ishmilly",
        "jamesiles",
        "rundns",
        "BridgedDomains",
        "ibuild_io",
        "DoctorBrandx",
        "justdropped",
        "domainretail",
        "FinTechNames",
        "katerleonid",
        "SedoDaveEvanson",
        "MediaOptions",
        "swethayenugula",
        "TonyNames",
        "DomainLabs",
        "NameHubs",
        "DNdomainname",
        "atomHQ",
        "NameJet",
        "MorganLinton",
        "AndrewAllemann",
        "DNJournal",
        "DomainShane",
        "DomainInvesting",
    ]

    for q, pages in searches:
        col.run_search(q, q, pages)
        if col.pages_429 >= 8 and col.pages_429 % 8 == 0:
            print("cooling after 429s", flush=True)
            time.sleep(25)

    for user in from_users:
        col.run_search(f"from:{user}", f"from:{user}", 18)
        if col.pages_429 >= 12:
            time.sleep(20)

    for user in profiles:
        col.run_profile(user, 12)

    # Date-windowed from: for high-volume sale posters
    windows = date_windows()
    window_users = [
        "NameBio",
        "DomainNews24",
        "DomainGang",
        "katerleonid",
        "FinTechNames",
        "domainretail",
        "SedoDaveEvanson",
        "andrewrosener",
        "DoctorBrandx",
        "justdropped",
        "BridgedDomains",
        "ibuild_io",
        "rundns",
        "DomainNameWire",
        "ishmilly",
        "jamesiles",
        "TonyNames",
        "DomainLabs",
        "NameHubs",
        "DNdomainname",
        "MediaOptions",
        "swethayenugula",
    ]
    window_keywords = [
        '"sold for" .com',
        '"just sold" .com',
        '"sold for" .ai',
        "sold via Sedo",
        "sold via Afternic",
        "NameBio sold",
    ]

    # Newer windows first (more likely still indexed)
    windows_rev = list(reversed(windows))
    for user in window_users:
        for since, until in windows_rev:
            q = f"from:{user} since:{since} until:{until}"
            col.run_search(f"from:{user} {since}", q, 4)
            if len(col.new_rows) >= 9000:
                break
        if len(col.new_rows) >= 9000:
            break

    if len(col.new_rows) < 8500:
        for kw in window_keywords:
            for since, until in windows_rev[:16]:
                q = f"{kw} since:{since} until:{until}"
                col.run_search(f"{kw} {since}", q, 5)
                if len(col.new_rows) >= 9000:
                    break
            if len(col.new_rows) >= 9000:
                break

    col.flush()
    col.write_progress({"phase": "done"})
    print(
        json.dumps(
            {
                "new_count": len(col.new_rows),
                "total_unique_tweet_ids": col.start_unique + len(col.new_rows),
                "premium_new": col.premium_new,
                "queries": len(col.queries_run),
                "errors": len(col.errors),
                "pages_ok": col.pages_ok,
                "pages_429": col.pages_429,
            },
            indent=2,
        )
    )
    print("EXAMPLES")
    shown = 0
    for r in col.new_rows:
        if r.get("price_usd"):
            print(r["url"], r.get("price_raw"), r.get("domains"), r["text"][:100].replace("\n", " "))
            shown += 1
            if shown >= 8:
                break
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
