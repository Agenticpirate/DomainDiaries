#!/usr/bin/env python3
"""Parse saved Nitter HTML into sales.jsonl. Skip posts without a status id."""
from __future__ import annotations

import html as htmlmod
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
from parse_sale import parse_sale  # noqa: E402

PAGES = ROOT / "data" / "raw" / "pages"
SALES = ROOT / "data" / "sales.jsonl"
PREMIUM = ROOT / "data" / "premium.jsonl"
SUMMARY = ROOT / "data" / "xcancel-summary.json"
EXTRA_HTML = [
    ROOT / "data" / "raw" / "poast-ok.html",
]

SALE_RE = re.compile(
    r"\b(just\s+sold|sold\s+for|domain\s+sold|sold\s+the\s+domain|"
    r"just\s+closed|closed\s+(?:on\s+)?(?:the\s+)?domain|acquired|purchased|"
    r"sale\s+closed|sold\s+a\s+domain|sold\s+my\s+domain|namebio|"
    r"escrow\.com|aftermarket|sold\s+via|closed\s+at)\b|"
    r"\bsold\b.{0,50}\$|\$.{0,50}\bsold\b",
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
DATE_RE = re.compile(r'class="tweet-date"><a href="[^"]+" title="([^"]+)"')
CONTENT_RE = re.compile(r'<div class="tweet-content[^"]*"[^>]*>([\s\S]*?)</div>')
FULLNAME_RE = re.compile(r'class="fullname"[^>]*title="([^"]+)"')
STAT_RE = re.compile(
    r'icon-(comment|retweet|heart|views)"[^>]*>\s*</span></div>\s*(\d[\d,]*)?',
)
INDUSTRY = {
    "domainnamewire", "andrewallemann", "dnjournal", "domainsherpa",
    "michaelcyger", "escrow_com", "escrowcom", "godaddyauctions", "namebio",
    "afternic", "sedo", "namejet", "namepros", "domaininvesting", "morganlinton",
    "domainshane", "jamesiles", "cygersays", "internetcommerce", "andrewrosener",
    "ishmilly",
}
SLUG_QUERY = {
    "justsold": "just sold domain",
    "soldfor": '"sold for" domain',
    "domainsold": "domain sold $",
    "justsoldcom": '"just sold" .com',
    "soldforcom": '"sold for" .com',
    "justclosed": '"just closed" domain',
    "namebio": "namebio sold",
    "escrow": "escrow.com sold domain",
    "hashdomains": "#domains sold",
    "fromdnw": "from:DomainNameWire sold",
    "fromrosener": "from:andrewrosener sold",
    "fromdi": "from:DomainInvesting sold",
    "fromshane": "from:DomainShane sold",
    "fromnamebio": "from:NameBio sold",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def strip_tags(s: str) -> str:
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = htmlmod.unescape(s)
    s = re.sub(r"[ \t]+", " ", s)
    return s.strip()


def parse_date(title: str | None) -> str | None:
    if not title:
        return None
    t = htmlmod.unescape(title).replace("\u00b7", " ").replace("·", " ")
    t = re.sub(r"\s+", " ", t).strip()
    t = t.replace(" UTC", "").strip()
    for fmt in ("%b %d, %Y %I:%M %p",):
        try:
            dt = datetime.strptime(t, fmt).replace(tzinfo=timezone.utc)
            return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        except ValueError:
            continue
    return None


def looks_like_sale(text: str, parsed: dict, username: str) -> bool:
    if NOISE_RE.search(text) and not parsed.get("domains") and parsed.get("price_usd") is None:
        return False
    saleish = bool(SALE_RE.search(text))
    has_domain = bool(parsed.get("domains"))
    has_price = parsed.get("price_usd") is not None
    if saleish and (has_domain or has_price):
        return True
    if has_domain and has_price and re.search(r"\b(sold|closed|acquired|purchased|escrow)\b", text, re.I):
        return True
    if (username or "").lower() in INDUSTRY and saleish and re.search(
        r"\b(domain|domains|\.com|\.ai|\.io|#domains)\b", text, re.I
    ):
        return True
    return False


def parse_file(path: Path, query: str) -> list[dict]:
    html = path.read_text(encoding="utf-8", errors="replace")
    if "Verifying your browser" in html or "timeline-item" not in html:
        return []
    rows = []
    for attrs, body in ITEM_RE.findall(html):
        sm = STATUS_RE.search(body)
        if not sm:
            continue
        username, tid = sm.group(1), sm.group(2)
        um = re.search(r'data-username="([^"]+)"', attrs)
        if um:
            username = um.group(1)
        cm = CONTENT_RE.search(body)
        text = strip_tags(cm.group(1)) if cm else ""
        if not text:
            continue
        dm = DATE_RE.search(body)
        created = parse_date(dm.group(1) if dm else None)
        nm = FULLNAME_RE.search(body)
        name = htmlmod.unescape(nm.group(1)) if nm else None
        likes = reposts = replies = 0
        for kind, num in STAT_RE.findall(body):
            n = int(num.replace(",", "")) if num else 0
            if kind == "comment":
                replies = n
            elif kind == "retweet":
                reposts = n
            elif kind == "heart":
                likes = n
        parsed = parse_sale(text)
        if not looks_like_sale(text, parsed, username):
            continue
        url = f"https://x.com/{username}/status/{tid}"
        rows.append(
            {
                "id": tid,
                "url": url,
                "tweet_url": url,
                "text": text,
                "created_at": created,
                "author_id": None,
                "username": username,
                "name": name,
                "domains": parsed["domains"],
                "price_usd": parsed["price_usd"],
                "price_raw": parsed["price_raw"],
                "premium_tier": parsed["premium_tier"],
                "likes": likes,
                "reposts": reposts,
                "quotes": 0,
                "replies": replies,
                "query": query,
                "source": "x-public",
                "collected_at": now_iso(),
            }
        )
    return rows


def load_ids(path: Path) -> set[str]:
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
        if obj.get("id"):
            seen.add(str(obj["id"]))
    return seen


def slug_query(name: str) -> str:
    base = name.rsplit("-", 1)[0]
    if base.startswith("p_"):
        return "profile:" + base[2:]
    return SLUG_QUERY.get(base, base)


def main() -> int:
    seen = load_ids(SALES)
    new_rows: list[dict] = []
    files = []
    if PAGES.is_dir():
        files.extend(sorted(PAGES.glob("*.html")))
    files.extend(p for p in EXTRA_HTML if p.is_file())
    scanned = 0
    for path in files:
        q = slug_query(path.stem) if path.parent == PAGES else "just sold domain"
        rows = parse_file(path, q)
        scanned += 1
        for rec in rows:
            if rec["id"] in seen:
                continue
            seen.add(rec["id"])
            new_rows.append(rec)
    if new_rows:
        SALES.parent.mkdir(parents=True, exist_ok=True)
        with SALES.open("a", encoding="utf-8") as fh:
            for rec in new_rows:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        prem = [r for r in new_rows if r.get("premium_tier")]
        if prem:
            with PREMIUM.open("a", encoding="utf-8") as fh:
                for rec in prem:
                    fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    else:
        prem = []
    summary = {
        "collected_at": now_iso(),
        "frontend_worked": "nitter.poast.org",
        "html_files_scanned": scanned,
        "new_sales": len(new_rows),
        "new_premium": len(prem),
        "sales_total": len(seen),
        "premium_total": len(load_ids(PREMIUM)),
        "source": "x-public",
        "note": "url/tweet_url is https://x.com/{user}/status/{id}; posts without status id skipped",
    }
    SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print("EXAMPLES")
    for r in new_rows[:8]:
        print(r["url"], r.get("price_raw"), r.get("domains"), r["text"][:140].replace("\n", " "))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
