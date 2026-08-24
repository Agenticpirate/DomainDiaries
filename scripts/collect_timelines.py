#!/usr/bin/env python3
"""Paginate public nitter.poast.org timelines for known sale-poster usernames.

Appends only new unique status-id records. Does not use x.com, X API, or namebio.com.
Does not invent tweets.
"""
from __future__ import annotations

import fcntl
import json
import random
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from http.cookiejar import Cookie, CookieJar, MozillaCookieJar
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from parse_sale import parse_sale  # noqa: E402
from collect_nitter_public import (  # noqa: E402
    BASE,
    UA,
    ITEM_RE,
    STATUS_RE,
    DATE_RE,
    CONTENT_RE,
    FULLNAME_RE,
    STAT_RE,
    MORE_RE,
    strip_tags,
    parse_nitter_date,
    solve_pow,
)

DATA = ROOT / "data"
SALES_PATH = DATA / "sales.jsonl"
PREMIUM_PATH = DATA / "premium.jsonl"
TWEETS_PATH = DATA / "tweets.jsonl"
XCANCEL_PATH = DATA / "xcancel-sales.jsonl"
PROGRESS_PATH = DATA / "collect-progress.json"
RESUME_PATH = DATA / "collect-timelines-progress.json"
COOKIE_PATH = DATA / "raw" / "poast-cookies.txt"
RAW = DATA / "raw" / "timelines"

TWEET_SOURCES = {"x-public", "xcancel", "web-mention"}
HANDLE_RE = re.compile(r"^[A-Za-z0-9_]{1,15}$")
URL_USER_RE = re.compile(
    r"(?:x\.com|twitter\.com|nitter\.[^/]+)/([A-Za-z0-9_]+)/status/(\d+)", re.I
)

SEEDS = [
    "NameBio",
    "DomainNews24",
    "DomainGang",
    "DomainNameWire",
    "andrewrosener",
    "SedoDaveEvanson",
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
    "DomainLabs",
    "NameHubs",
    "DNdomainname",
    "MediaOptions",
    "Afternic",
    "Sedo",
    "GoDaddyAuctions",
    "MorganLinton",
    "DomainShane",
    "DomainInvesting",
    "DNJournal",
    "MichaelCyger",
    "Escrow_com",
]

# Extra known industry handles that pair with seeds / existing files.
EXTRA_INDUSTRY = [
    "AndrewAllemann",
    "DomainSherpa",
    "CygerSays",
    "NameJet",
    "NamePros",
    "DInvesting",
    "Escrowcom",
]

HIGH_VOLUME = {
    u.lower()
    for u in SEEDS
    + EXTRA_INDUSTRY
    + [
        "DropDax",
        "Zakaria_Mouhali",
        "thedraii",
        "unlockeddomains",
        "ContactOwner",
        "domainjobcom",
        "360Domain",
        "domain_raider",
        "iheartdomains",
        "4Ldotcom",
        "MarsDomains_com",
        "MemorableDN",
        "purchasedxyz",
        "Domains90210",
        "StartupNamesDN",
        "iamAzadKhan",
        "DavidSustiel",
        "WEB23domain",
        "UnreportedSales",
        "TLDInvestors",
        "juddeme",
        "TonyNames",
        "atomHQ",
        "lumis_com",
        "AdamatLumis",
        "JeffreyMGabriel",
        "TheDomainAgents",
        "Derick_Sedo",
        "MrPremiumDotCom",
        "cultra",
        "DomainMartCom",
        "goexpired",
    ]
}

SALE_RE = re.compile(
    r"\b(just\s+sold|sold\s+for|domain\s+sold|sold\s+the\s+domain|"
    r"just\s+closed|closed\s+(?:on\s+)?(?:the\s+)?domain|closed\s+at|"
    r"sale\s+closed|sold\s+a\s+domain|sold\s+my\s+domain|sold\s+via|"
    r"acquired|purchased|namebio|escrow\.com|aftermarket|"
    r"reported\s+sale|sale\s+reported|weekly\s+sales|daily\s+sales)\b|"
    r"\bsold\b.{0,60}\$|\$.{0,60}\bsold\b|"
    r"\bclosed\b.{0,40}\$|\$.{0,40}\bclosed\b",
    re.I | re.S,
)
NOISE_RE = re.compile(
    r"\b(followers?|subscribers?|hard-bounced|prospecting pipeline|"
    r"fan tokens|bowie bonds|unsubscribe)\b",
    re.I,
)
INDUSTRY = HIGH_VOLUME | {
    "domainnamewire",
    "andrewallemann",
    "dnjournal",
    "domainsherpa",
    "michaelcyger",
    "escrow_com",
    "escrowcom",
    "godaddyauctions",
    "namebio",
    "afternic",
    "sedo",
    "namejet",
    "namepros",
    "domaininvesting",
    "dinvesting",
    "morganlinton",
    "domainshane",
    "jamesiles",
    "cygersays",
    "internetcommerce",
    "andrewrosener",
    "ishmilly",
    "ronjackson",
    "domainnews24",
    "domaingang",
    "sedodaveevanson",
    "rundns",
    "bridgeddomains",
    "ibuild_io",
    "doctorbrandx",
    "justdropped",
    "domainretail",
    "fintechnames",
    "katerleonid",
    "domainlabs",
    "namehubs",
    "dndomainname",
    "mediaoptions",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file() or path.stat().st_size == 0:
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def collect_usernames_and_ids() -> tuple[list[str], set[str]]:
    users: dict[str, int] = {}
    ids: set[str] = set()

    def add_user(u: str | None, weight: int = 1) -> None:
        if not u:
            return
        u = str(u).strip().lstrip("@")
        if not HANDLE_RE.fullmatch(u):
            return
        key = u  # preserve original casing of first seen
        # case-insensitive de-dupe, keep first casing
        existing = next((k for k in users if k.lower() == u.lower()), None)
        if existing:
            users[existing] += weight
        else:
            users[u] = weight

    def add_id(tid: Any) -> None:
        if tid is None:
            return
        s = str(tid).strip()
        if s.isdigit() and 10 <= len(s) <= 22:
            ids.add(s)

    def ingest(rows: list[dict[str, Any]], tweet_only: bool) -> None:
        for r in rows:
            src = r.get("source")
            tid = r.get("id")
            url = str(r.get("url") or r.get("tweet_url") or "")
            is_tweet = (src in TWEET_SOURCES) or (
                isinstance(tid, (str, int)) and str(tid).isdigit()
            )
            if tweet_only and not is_tweet:
                continue
            if is_tweet:
                add_id(tid)
                m = URL_USER_RE.search(url)
                if m:
                    add_user(m.group(1), 1)
                    add_id(m.group(2))
                add_user(r.get("username"), 1)

    ingest(load_jsonl(SALES_PATH), tweet_only=True)
    ingest(load_jsonl(TWEETS_PATH), tweet_only=False)
    ingest(load_jsonl(XCANCEL_PATH), tweet_only=False)
    for s in SEEDS + EXTRA_INDUSTRY:
        add_user(s, 50 if s in SEEDS else 20)

    # Prefer high-volume / seed accounts first, then by observed frequency.
    ordered = sorted(
        users.items(),
        key=lambda kv: (
            0 if kv[0].lower() in HIGH_VOLUME else 1,
            -kv[1],
            kv[0].lower(),
        ),
    )
    return [u for u, _ in ordered], ids


def looks_like_sale(text: str, parsed: dict[str, Any], username: str) -> bool:
    if not text:
        return False
    if NOISE_RE.search(text) and not parsed.get("domains") and parsed.get("price_usd") is None:
        return False
    saleish = bool(SALE_RE.search(text))
    has_domain = bool(parsed.get("domains"))
    has_price = parsed.get("price_usd") is not None
    uname = (username or "").lower()
    # $price + domain-like token
    if has_domain and has_price:
        return True
    if saleish and (has_domain or has_price):
        return True
    if "namebio" in text.lower() and (has_domain or has_price or saleish or "sold" in text.lower()):
        return True
    if uname in INDUSTRY and saleish and re.search(
        r"\b(domain|domains|\.com|\.ai|\.io|\.xyz|#domains|aftermarket|escrow)\b",
        text,
        re.I,
    ):
        return True
    # Escrow_com: sale posts only
    if uname in {"escrow_com", "escrowcom"}:
        return bool(saleish and (has_domain or has_price or re.search(r"\bdomain", text, re.I)))
    return False


def parse_items(page_html: str) -> tuple[list[dict[str, Any]], str | None]:
    items: list[dict[str, Any]] = []
    for attrs, body in ITEM_RE.findall(page_html):
        sm = STATUS_RE.search(body)
        if not sm:
            continue
        username, tid = sm.group(1), sm.group(2)
        if not tid.isdigit():
            continue
        um = re.search(r'data-username="([^"]+)"', attrs)
        if um:
            username = um.group(1)
        else:
            um2 = re.search(r'class="username"[^>]*title="@([^"]+)"', body)
            if um2:
                username = um2.group(1)
        content_m = CONTENT_RE.search(body)
        text = strip_tags(content_m.group(1)) if content_m else ""
        if not text:
            continue
        date_m = DATE_RE.search(body)
        created = parse_nitter_date(date_m.group(1) if date_m else None)
        name_m = FULLNAME_RE.search(body)
        name = None
        if name_m:
            import html as htmlmod

            name = htmlmod.unescape(name_m.group(1))
        stats = {"replies": 0, "reposts": 0, "likes": 0}
        for kind, num in STAT_RE.findall(body):
            n = int(num.replace(",", "")) if num else 0
            if kind == "comment":
                stats["replies"] = n
            elif kind == "retweet":
                stats["reposts"] = n
            elif kind == "heart":
                stats["likes"] = n
        items.append(
            {
                "id": tid,
                "username": username,
                "name": name,
                "text": text,
                "created_at": created,
                "likes": stats["likes"],
                "reposts": stats["reposts"],
                "quotes": 0,
                "replies": stats["replies"],
            }
        )
    more = None
    mm = MORE_RE.search(page_html)
    if mm:
        import html as htmlmod

        more = htmlmod.unescape(mm.group(1))
    return items, more


class Client:
    def __init__(self) -> None:
        self.cj = CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cj))
        self.solved = 0
        self._load_cookies()

    def _load_cookies(self) -> None:
        if not COOKIE_PATH.is_file():
            return
        try:
            jar = MozillaCookieJar(str(COOKIE_PATH))
            jar.load(ignore_discard=True, ignore_expires=True)
            for ck in jar:
                self.cj.set_cookie(ck)
        except Exception:
            pass

    def _save_cookies(self) -> None:
        COOKIE_PATH.parent.mkdir(parents=True, exist_ok=True)
        jar = MozillaCookieJar(str(COOKIE_PATH))
        for ck in self.cj:
            jar.set_cookie(ck)
        try:
            jar.save(ignore_discard=True, ignore_expires=True)
        except Exception:
            pass

    def _set_cookie(self, name: str, value: str, domain: str = "nitter.poast.org") -> None:
        ck = Cookie(
            0, name, value, None, False, domain, True, False, "/", True, False, None, False, None, None, {}
        )
        self.cj.set_cookie(ck)

    def fetch(self, url: str, retries: int = 6) -> tuple[int, str]:
        if url.startswith("/"):
            url = BASE + url
        last_html = ""
        last_code = 0
        backoff = 8.0
        for attempt in range(retries):
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": UA,
                    "Accept": "text/html,application/xhtml+xml",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Referer": BASE + "/",
                },
            )
            try:
                with self.opener.open(req, timeout=45) as r:
                    html = r.read().decode("utf-8", "replace")
                    code = r.getcode()
            except urllib.error.HTTPError as e:
                html = e.read().decode("utf-8", "replace")
                code = e.code
            except Exception as e:
                last_code, last_html = 0, str(e)
                time.sleep(backoff + random.uniform(0, 2))
                backoff = min(backoff * 1.6, 90)
                continue
            last_html, last_code = html, code
            if "Verifying your browser" in html:
                token = solve_pow(html)
                if not token:
                    # fallback to standalone solver pieces
                    try:
                        from solve_poast import solve_pow as solve_pow2

                        token = solve_pow2(html)
                    except Exception:
                        token = None
                if not token:
                    RAW.mkdir(parents=True, exist_ok=True)
                    (RAW / "poast-unsolved.html").write_text(html, encoding="utf-8")
                    return code, html
                name, val = token.split("=", 1)
                self._set_cookie(name, val)
                self.solved += 1
                self._save_cookies()
                time.sleep(0.35)
                continue
            rate_limited = (
                code == 429
                or "Instance has been rate limited" in html
                or "rate limited" in html.lower() and "error-panel" in html
            )
            if rate_limited:
                wait = backoff + random.uniform(4, 12)
                print(f"    429/rate-limit sleep {wait:.0f}s attempt={attempt+1} url={url[:90]}", flush=True)
                time.sleep(wait)
                backoff = min(backoff * 1.8, 120)
                continue
            return code, html
        return last_code, last_html


def next_url(current: str, more: str | None) -> str | None:
    if not more:
        return None
    if more.startswith("http"):
        return more
    if more.startswith("/"):
        return BASE + more
    path = urllib.parse.urlparse(current).path
    return BASE + path + (more if more.startswith("?") else "?" + more)


def make_record(it: dict[str, Any], parsed: dict[str, Any], query: str) -> dict[str, Any]:
    tid = it["id"]
    user = it["username"]
    url = f"https://x.com/{user}/status/{tid}"
    return {
        "id": tid,
        "url": url,
        "tweet_url": url,
        "text": it["text"],
        "created_at": it["created_at"],
        "author_id": None,
        "username": user,
        "name": it.get("name"),
        "domains": parsed["domains"],
        "price_usd": parsed["price_usd"],
        "price_raw": parsed["price_raw"],
        "premium_tier": parsed["premium_tier"],
        "likes": it.get("likes", 0),
        "reposts": it.get("reposts", 0),
        "quotes": 0,
        "replies": it.get("replies", 0),
        "query": query,
        "source": "x-public",
        "collected_at": now_iso(),
    }


def tweet_fields(rec: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": rec["id"],
        "url": rec["url"],
        "tweet_url": rec.get("tweet_url", rec["url"]),
        "username": rec.get("username"),
        "name": rec.get("name"),
        "text": rec.get("text"),
        "created_at": rec.get("created_at"),
        "domains": rec.get("domains"),
        "price_usd": rec.get("price_usd"),
        "price_raw": rec.get("price_raw"),
        "premium_tier": rec.get("premium_tier"),
        "likes": rec.get("likes", 0),
        "reposts": rec.get("reposts", 0),
        "quotes": rec.get("quotes", 0),
        "replies": rec.get("replies", 0),
        "query": rec.get("query"),
        "source": rec.get("source", "x-public"),
        "collected_at": rec.get("collected_at"),
    }


def append_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)
    with path.open("a", encoding="utf-8") as fh:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        try:
            fh.write(payload)
            fh.flush()
        finally:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)


def write_progress(payload: dict[str, Any]) -> None:
    text = json.dumps(payload, indent=2) + "\n"
    for dest in (PROGRESS_PATH, RESUME_PATH):
        dest.write_text(text, encoding="utf-8")


def pages_for(username: str) -> int:
    if username.lower() in HIGH_VOLUME:
        return 28
    return 12


def paginate_user(
    client: Client,
    username: str,
    seen: set[str],
    max_pages: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    collected: list[dict[str, Any]] = []
    start = f"{BASE}/{username}"
    url: str | None = start
    pages = 0
    empty_streak = 0
    rate_hits = 0
    items_seen = 0
    query = f"timeline:{username}"
    info: dict[str, Any] = {
        "username": username,
        "pages": 0,
        "items": 0,
        "kept": 0,
        "error": None,
    }
    while url and pages < max_pages:
        pages += 1
        code, page = client.fetch(url)
        rate_limited = code == 429 or "Instance has been rate limited" in page
        if rate_limited:
            rate_hits += 1
            info["error"] = f"rate-limited page={pages} code={code}"
            if rate_hits >= 3:
                break
            time.sleep(25 + random.uniform(5, 15))
            continue
        if "Verifying your browser" in page:
            info["error"] = f"pow-unsolved page={pages}"
            RAW.mkdir(parents=True, exist_ok=True)
            (RAW / f"pow-{username}-{pages}.html").write_text(page[:12000], encoding="utf-8")
            break
        if (code == 404 or "User not found" in page or "This account doesn’t exist" in page) and items_seen == 0 and pages <= 2:
            info["error"] = f"not-found code={code}"
            break
        if code == 404 and items_seen > 0:
            print(f"    transient 404 on {username} p{pages}, retry", flush=True)
            time.sleep(8 + random.uniform(2, 6))
            pages -= 1
            continue
        if code >= 400 and "timeline-item" not in page:
            info["error"] = f"http-{code} page={pages}"
            RAW.mkdir(parents=True, exist_ok=True)
            (RAW / f"err-{username}-{pages}.html").write_text(page[:12000], encoding="utf-8")
            break
        items, more = parse_items(page)
        items_seen += len(items)
        print(
            f"  {username} p{pages} code={code} items={len(items)} more={bool(more)} kept_so_far={len(collected)}",
            flush=True,
        )
        if not items:
            empty_streak += 1
            if empty_streak >= 2:
                break
        else:
            empty_streak = 0
        for it in items:
            tid = it["id"]
            if not tid or tid in seen:
                continue
            parsed = parse_sale(it["text"])
            if not looks_like_sale(it["text"], parsed, it["username"]):
                continue
            seen.add(tid)
            rec = make_record(it, parsed, query)
            collected.append(rec)
        url = next_url(url, more)
        if url:
            time.sleep(1.15 + random.uniform(0.15, 0.55))
    info["pages"] = pages
    info["items"] = items_seen
    info["kept"] = len(collected)
    return collected, info


def main() -> int:
    DATA.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)
    usernames, seen = collect_usernames_and_ids()
    start_unique = len(seen)
    print(f"usernames={len(usernames)} existing_ids={start_unique}", flush=True)

    progress: dict[str, Any] = {}
    for cand in (RESUME_PATH, PROGRESS_PATH):
        if cand.is_file():
            try:
                obj = json.loads(cand.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            if obj.get("usernames_done"):
                progress = obj
                break
            if not progress:
                progress = obj
    done_set = {u.lower() for u in progress.get("usernames_done", [])}
    errors: list[dict[str, Any]] = list(progress.get("errors", []))
    new_rows_total = int(progress.get("new_count", 0) or 0)
    examples: list[str] = list(progress.get("examples", []))
    usernames_done: list[str] = list(progress.get("usernames_done", []))
    per_user: list[dict[str, Any]] = list(progress.get("per_user", []))

    limit = None
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        limit = int(sys.argv[1])

    client = Client()
    processed = 0
    consecutive_rate = 0

    for username in usernames:
        if username.lower() in done_set:
            continue
        if limit is not None and processed >= limit:
            break
        processed += 1
        max_pages = pages_for(username)
        print(f"PROFILE {username} max_pages={max_pages} ({processed}/{len(usernames)})", flush=True)
        try:
            rows, info = paginate_user(client, username, seen, max_pages)
        except Exception as e:
            info = {"username": username, "pages": 0, "items": 0, "kept": 0, "error": repr(e)}
            rows = []
            errors.append({"username": username, "error": repr(e)})
        if info.get("error"):
            errors.append({"username": username, "error": info["error"]})
            if "rate-limited" in str(info.get("error")):
                consecutive_rate += 1
            else:
                consecutive_rate = 0
        else:
            consecutive_rate = 0
        if rows:
            append_jsonl(SALES_PATH, rows)
            prem = [r for r in rows if r.get("premium_tier")]
            if prem:
                append_jsonl(PREMIUM_PATH, prem)
            append_jsonl(TWEETS_PATH, [tweet_fields(r) for r in rows])
            new_rows_total += len(rows)
            for r in rows:
                if len(examples) < 12:
                    examples.append(r["url"])
        usernames_done.append(username)
        done_set.add(username.lower())
        per_user.append(info)
        write_progress(
            {
                "collected_at": now_iso(),
                "new_count": new_rows_total,
                "total_unique": len(seen),
                "start_unique": start_unique,
                "usernames_done": usernames_done,
                "usernames_total": len(usernames),
                "errors": errors[-80:],
                "examples": examples,
                "pow_solves": client.solved,
                "per_user": per_user,
                "source": "x-public",
                "frontend": "nitter.poast.org",
                "note": "Timeline pagination only; records require a real /status/ id.",
            }
        )
        print(f"  kept {len(rows)} new_total={new_rows_total} unique={len(seen)}", flush=True)
        if consecutive_rate >= 4:
            wait = 90 + random.uniform(10, 30)
            print(f"  cooling off {wait:.0f}s after repeated rate limits", flush=True)
            time.sleep(wait)
            consecutive_rate = 0
        else:
            time.sleep(1.6 + random.uniform(0.2, 0.8))

    write_progress(
        {
            "collected_at": now_iso(),
            "new_count": new_rows_total,
            "total_unique": len(seen),
            "start_unique": start_unique,
            "usernames_done": usernames_done,
            "usernames_total": len(usernames),
            "usernames_paginated": len(usernames_done),
            "errors": errors,
            "examples": examples,
            "pow_solves": client.solved,
            "per_user": per_user,
            "source": "x-public",
            "frontend": "nitter.poast.org",
            "finished": limit is None or len(usernames_done) >= len(usernames),
            "note": "Timeline pagination only; records require a real /status/ id.",
        }
    )
    print(
        json.dumps(
            {
                "new_count": new_rows_total,
                "total_unique": len(seen),
                "usernames_paginated": len(usernames_done),
                "errors": len(errors),
                "examples": examples[:5],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
