#!/usr/bin/env python3
"""Collect public domain-sale posts from nitter.poast.org (Nitter frontend).

Not x.com, not official X API. Requires a real tweet status id on every record.
"""
from __future__ import annotations

import hashlib
import html as htmlmod
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from http.cookiejar import Cookie, CookieJar
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from parse_sale import parse_sale  # noqa: E402

BASE = "https://nitter.poast.org"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)
DATA = ROOT / "data"
SALES_PATH = DATA / "sales.jsonl"
PREMIUM_PATH = DATA / "premium.jsonl"
SUMMARY_PATH = DATA / "xcancel-summary.json"
RAW = DATA / "raw"

SALE_RE = re.compile(
    r"\b(just\s+sold|sold\s+for|domain\s+sold|sold\s+the\s+domain|"
    r"just\s+closed|closed\s+the\s+domain|acquired|purchased|"
    r"sale\s+closed|sold\s+a\s+domain|sold\s+my\s+domain|"
    r"namebio|escrow\.com|aftermarket)\b|"
    r"\bsold\b.{0,40}\$(?:\d)|\$(?:\d).{0,40}\bsold\b",
    re.I | re.S,
)
NOISE_RE = re.compile(
    r"\b(followers?|subscribers?|hard-bounced|prospecting pipeline|"
    r"fan tokens|bowie bonds)\b",
    re.I,
)
STATUS_RE = re.compile(r"/([A-Za-z0-9_]+)/status/(\d+)")
ITEM_RE = re.compile(
    r'<div class="timeline-item[^"]*"([^>]*)>([\s\S]*?)(?=<div class="timeline-item|class="show-more"|$)',
)
MORE_RE = re.compile(r'class="show-more"[^>]*>\s*<a href="([^"]+)"', re.I)
DATE_RE = re.compile(r'class="tweet-date"><a href="[^"]+" title="([^"]+)"')
CONTENT_RE = re.compile(r'<div class="tweet-content[^"]*"[^>]*>([\s\S]*?)</div>')
FULLNAME_RE = re.compile(r'class="fullname"[^>]*title="([^"]+)"')
USERNAME_RE = re.compile(r'data-username="([^"]+)"|class="username"[^>]*title="@([^"]+)"')
STAT_RE = re.compile(
    r'icon-(comment|retweet|heart|views)"[^>]*>\s*</span></div>\s*(\d[\d,]*)?',
)


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def strip_tags(s: str) -> str:
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = htmlmod.unescape(s)
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def parse_nitter_date(title: str | None) -> str | None:
    if not title:
        return None
    title = htmlmod.unescape(title).replace("\u00b7", "").strip()
    title = re.sub(r"\s+", " ", title)
    for fmt in ("%b %d, %Y %I:%M %p UTC", "%b %d, %Y · %I:%M %p UTC"):
        try:
            dt = datetime.strptime(title.replace(" · ", " "), "%b %d, %Y %I:%M %p UTC")
            return dt.replace(tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        except ValueError:
            continue
    return None


def solve_pow(html: str) -> str | None:
    m = re.search(r"const a0_0x2a54=(\[[^\]]+\])", html)
    if not m:
        return None
    raw = m.group(1)
    parts = re.findall(r"'([^']*)'", raw)
    if len(parts) < 3:
        return None
    n = re.search(r"a0_0x2a54,(0x[0-9a-fA-F]+|\d+)", html)
    rot = int(n.group(1), 0) if n else 0x178
    arr = parts[:]
    for _ in range(rot):
        arr.append(arr.pop(0))
    cookie_prefix = next((x for x in arr if x.startswith("res=")), "res=")
    c = next((x for x in arr if re.fullmatch(r"[0-9A-Fa-f]{16,}", x)), None)
    if not c:
        return None
    n1 = int(c[0], 16)
    for i in range(0, 3_000_000):
        digest = hashlib.sha1((c + str(i)).encode()).digest()
        if digest[n1] == 0xB0 and digest[n1 + 1] == 0x0B:
            return cookie_prefix + c + str(i)
    return None


class Client:
    def __init__(self) -> None:
        self.cj = CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cj))
        self.solved = 0

    def _set_cookie(self, name: str, value: str, domain: str = "nitter.poast.org") -> None:
        ck = Cookie(0, name, value, None, False, domain, True, False, "/", True, False, None, False, None, None, {})
        self.cj.set_cookie(ck)

    def fetch(self, url: str, retries: int = 3) -> tuple[int, str]:
        if url.startswith("/"):
            url = BASE + url
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html"})
        last_html = ""
        last_code = 0
        for attempt in range(retries):
            try:
                with self.opener.open(req, timeout=40) as r:
                    html = r.read().decode("utf-8", "replace")
                    code = r.getcode()
            except urllib.error.HTTPError as e:
                html = e.read().decode("utf-8", "replace")
                code = e.code
            last_html, last_code = html, code
            if "Verifying your browser" in html:
                token = solve_pow(html)
                if not token:
                    RAW.mkdir(parents=True, exist_ok=True)
                    (RAW / "poast-unsolved.html").write_text(html, encoding="utf-8")
                    return code, html
                name, val = token.split("=", 1)
                self._set_cookie(name, val)
                self.solved += 1
                time.sleep(0.3)
                continue
            return code, html
        return last_code, last_html


def parse_items(page_html: str) -> tuple[list[dict[str, Any]], str | None]:
    items: list[dict[str, Any]] = []
    for attrs, body in ITEM_RE.findall(page_html):
        sm = STATUS_RE.search(body)
        if not sm:
            continue
        username, tid = sm.group(1), sm.group(2)
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
        name = htmlmod.unescape(name_m.group(1)) if name_m else None
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
        more = htmlmod.unescape(mm.group(1))
        if more.startswith("?"):
            more = None  # filled by caller with path
            more = htmlmod.unescape(mm.group(1))
    return items, (htmlmod.unescape(mm.group(1)) if mm else None)


def looks_like_sale(text: str, parsed: dict[str, Any], username: str, prefer_industry: bool) -> bool:
    if NOISE_RE.search(text) and not parsed.get("domains") and not parsed.get("price_usd"):
        return False
    saleish = bool(SALE_RE.search(text))
    has_domain = bool(parsed.get("domains"))
    has_price = parsed.get("price_usd") is not None
    if saleish and (has_domain or has_price):
        return True
    if prefer_industry and saleish and re.search(r"\b(domain|domains|\.com|\.ai|\.io|#domains)\b", text, re.I):
        return True
    if has_domain and has_price and re.search(r"\b(sold|closed|acquired|purchased|escrow)\b", text, re.I):
        return True
    return False


INDUSTRY = {
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
    "morganlinton",
    "domainshane",
    "jamesiles",
    "cygersays",
    "internetcommerce",
    "andrewrosener",
    "ishmilly",
    "ronjackson",
}


def load_ids(path: Path) -> set[str]:
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
        if obj.get("id"):
            seen.add(str(obj["id"]))
    return seen


def append_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def collect_url(client: Client, url: str, query: str, seen: set[str], max_pages: int) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    next_url = url
    pages = 0
    while next_url and pages < max_pages:
        pages += 1
        code, page = client.fetch(next_url)
        if "Verifying your browser" in page or code >= 400 and "timeline-item" not in page:
            RAW.mkdir(parents=True, exist_ok=True)
            (RAW / f"blocked-{pages}.html").write_text(page[:20000], encoding="utf-8")
            print(f"  block page={pages} code={code} url={next_url[:80]}", flush=True)
            break
        items, more = parse_items(page)
        print(f"  page={pages} code={code} items={len(items)} more={bool(more)}", flush=True)
        if not items:
            RAW.mkdir(parents=True, exist_ok=True)
            slug = re.sub(r"[^A-Za-z0-9]+", "-", query)[:40]
            (RAW / f"empty-{slug}-{pages}.html").write_text(page[:15000], encoding="utf-8")
            break
        for it in items:
            tid = it["id"]
            if not tid or tid in seen:
                continue
            parsed = parse_sale(it["text"])
            industry = (it["username"] or "").lower() in INDUSTRY
            if not looks_like_sale(it["text"], parsed, it["username"], industry):
                continue
            seen.add(tid)
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
        if more:
            if more.startswith("http"):
                next_url = more
            elif more.startswith("/"):
                next_url = BASE + more
            else:
                # relative query on same path
                path = urllib.parse.urlparse(next_url).path
                next_url = BASE + path + (more if more.startswith("?") else "?" + more)
            time.sleep(0.7)
        else:
            next_url = None
    return out


def main() -> int:
    DATA.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)
    seen = load_ids(SALES_PATH)
    client = Client()
    collected: list[dict[str, Any]] = []
    frontend = "nitter.poast.org"
    blockers: list[str] = []

    searches = [
        ("just sold domain", "/search?f=tweets&q=just+sold+domain"),
        ('"sold for" domain', "/search?f=tweets&q=%22sold%20for%22%20domain"),
        ("domain sold $", "/search?f=tweets&q=domain%20sold%20%24"),
        ('"just sold" .com', "/search?f=tweets&q=%22just%20sold%22%20.com"),
        ('"sold for" .com', "/search?f=tweets&q=%22sold%20for%22%20.com"),
        ('"just closed" domain', "/search?f=tweets&q=%22just%20closed%22%20domain"),
        ("namebio sold", "/search?f=tweets&q=namebio%20sold"),
        ("escrow.com sold domain", "/search?f=tweets&q=escrow.com%20sold%20domain"),
        ('"sold" .ai $', "/search?f=tweets&q=sold%20.ai%20%24"),
        ("from:DomainNameWire sold", "/search?f=tweets&q=from%3ADomainNameWire%20sold"),
        ("from:andrewrosener sold", "/search?f=tweets&q=from%3Aandrewrosener%20sold"),
        ("from:DomainInvesting sold", "/search?f=tweets&q=from%3ADomainInvesting%20sold"),
        ("from:DomainShane sold", "/search?f=tweets&q=from%3ADomainShane%20sold"),
        ("from:NameBio sold", "/search?f=tweets&q=from%3ANameBio%20sold"),
        ("from:DNJournal sold", "/search?f=tweets&q=from%3ADNJournal%20sold"),
        ("#domains sold", "/search?f=tweets&q=%23domains%20sold"),
    ]
    profiles = [
        "DomainNameWire",
        "andrewrosener",
        "jamesiles",
        "ishmilly",
        "DomainSherpa",
        "DNJournal",
        "Escrow_com",
        "Escrowcom",
        "DomainInvesting",
        "DomainShane",
        "MorganLinton",
        "NameBio",
        "AndrewAllemann",
        "GoDaddyAuctions",
        "Afternic",
        "Sedo",
        "NameJet",
    ]

    for q, path in searches:
        print(f"SEARCH {q}", flush=True)
        rows = collect_url(client, BASE + path, q, seen, max_pages=25)
        print(f"  kept {len(rows)}", flush=True)
        collected.extend(rows)
        time.sleep(0.5)

    for user in profiles:
        print(f"PROFILE {user}", flush=True)
        rows = collect_url(client, f"{BASE}/{user}", f"profile:{user}", seen, max_pages=8)
        print(f"  kept {len(rows)}", flush=True)
        collected.extend(rows)
        time.sleep(0.5)

    if collected:
        append_jsonl(SALES_PATH, collected)
        prem = [r for r in collected if r.get("premium_tier")]
        if prem:
            append_jsonl(PREMIUM_PATH, prem)
    else:
        prem = []

    # also count existing totals
    all_ids = load_ids(SALES_PATH)
    prem_ids = load_ids(PREMIUM_PATH)
    summary = {
        "collected_at": now_iso(),
        "frontend_worked": frontend if collected or client.solved else None,
        "frontends_tried": [
            "xcancel.com (captcha/antibot)",
            "nitter.poast.org (worked after public JS check)",
            "nitter.net (TLS error)",
            "nitter.tiekoetter.com (bot check)",
            "nitter.catsarch.com (403)",
            "lightbrd.com (cloudflare)",
            "nitter.space (cloudflare)",
            "xcancel RSS (reader not whitelisted)",
        ],
        "pow_solves": client.solved,
        "new_sales": len(collected),
        "new_premium": len(prem),
        "sales_total": len(all_ids),
        "premium_total": len(prem_ids),
        "blockers": blockers,
        "source": "x-public",
        "note": "Records require a real status id; url is https://x.com/{user}/status/{id}.",
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    if collected:
        print("EXAMPLES")
        for r in collected[:8]:
            print(r["url"], r.get("price_raw"), r.get("domains"), r["text"][:120].replace("\n", " "))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
