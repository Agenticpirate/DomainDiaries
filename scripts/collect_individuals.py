#!/usr/bin/env python3
"""Collect INDIVIDUAL domain-sale tweets from blog embeds (real /status/ IDs only)."""
from __future__ import annotations

import html as htmlmod
import json
import re
import subprocess
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))
from parse_sale import parse_sale  # noqa: E402
from collect_nitter_public import looks_like_sale  # noqa: E402

DATA = ROOT / "data"
TWEETS = DATA / "tweets.jsonl"
TWEETS_IND = DATA / "tweets-individuals.jsonl"
TWEETS_2526 = DATA / "tweets-2025-2026.jsonl"
SALES = DATA / "sales.jsonl"
PREMIUM = DATA / "premium.jsonl"
COMPANY_FILE = DATA / "company-accounts.json"
PROGRESS = DATA / "collect-progress-individuals.json"
HTML_DIR = Path("/tmp/dd-hunt/html-ind")
HTML_DIR.mkdir(parents=True, exist_ok=True)

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)

STATUS_RE = re.compile(
    r"(?:https?:)?//(?:www\.|mobile\.)?(?:twitter|x)\.com/([A-Za-z0-9_]+)/status(?:es)?/(\d{10,20})",
    re.I,
)
BLOCKQUOTE_RE = re.compile(
    r'<blockquote[^>]*class="[^"]*twitter-tweet[^"]*"[\s\S]{0,8000}?</blockquote>',
    re.I,
)
P_RE = re.compile(r"<p[^>]*>([\s\S]*?)</p>", re.I)
MDASH_RE = re.compile(
    r"""(?:&mdash;|—)\s*([^<]*?)\s*\(@([A-Za-z0-9_]+)\)\s*<a href="[^"]+/status(?:es)?/(\d{10,20})[^"]*"[^>]*>([^<]*)</a>""",
    re.I,
)
CANON = re.compile(r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)', re.I)
CANON2 = re.compile(r'<link[^>]+href=["\']([^"\']+)["\'][^>]+rel=["\']canonical["\']', re.I)
OG_TITLE = re.compile(r'<meta[^>]+property="og:title"[^>]+content="([^"]+)"', re.I)
TITLE_RE = re.compile(r"<title>([^<]+)</title>", re.I)
PUBLISHED = re.compile(
    r'<meta[^>]+property="article:published_time"[^>]+content="([^"]+)"', re.I
)
SKIP_USER = {
    "intent", "share", "home", "search", "hashtag", "i", "twitter", "privacy",
    "tos", "x", "settings", "explore", "messages", "notifications", "compose",
}

# Extra marketplace/news brands even if missing from company-accounts.json
EXTRA_COMPANY = {
    "namebio", "domainnews24", "fintechnames", "domaingang", "namehubs",
    "domainlabs", "sedo", "sedoofficial", "afternic", "atomhq", "atomcom",
    "escrow_com", "escrowcom", "godaddyauctions", "godaddy", "domainnamewire",
    "dnjournal", "namepros", "domaininvesting", "dinvesting", "arabicdomainadc",
    "namemaxicom", "360domain", "appraise_net", "unreportedsales",
    "aidomainmarket", "thedomainagents", "thedomains", "dnw", "dndomainname",
    "contactowner", "domainize", "domainjobcom", "domainsherpa", "dynadot",
    "lumis_com", "mediaoptions", "memorabledn", "namecheap", "namejet",
    "qualitynames", "spaceship", "unlockeddomains", "xtopdomains",
}

SALE_HINT = re.compile(
    r"\b(just\s+sold|sold\s+for|sold\s+via|domain\s+sold|sold\s+the\s+domain|"
    r"just\s+closed|closed\s+the\s+domain|acquired|purchased|sale\s+closed|"
    r"sold\s+a\s+domain|sold\s+my\s+domain|bin\b|escrow|brokered|"
    r"sells?\s+for|gross|netted|payout)\b",
    re.I,
)
MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
}

def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def strip_tags(s: str) -> str:
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = htmlmod.unescape(s)
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def parse_date(s: str) -> str | None:
    if not s:
        return None
    s = htmlmod.unescape(s).strip()
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}T00:00:00.000Z"
    m = re.search(r"([A-Za-z]+)\s+(\d{1,2}),\s*(\d{4})", s)
    if m:
        mon = MONTHS.get(m.group(1).lower())
        if mon:
            return f"{int(m.group(3)):04d}-{mon:02d}-{int(m.group(2)):02d}T00:00:00.000Z"
    return None


def load_company() -> set[str]:
    users = set(EXTRA_COMPANY)
    if COMPANY_FILE.is_file():
        obj = json.loads(COMPANY_FILE.read_text())
        for u in obj.get("usernames") or []:
            users.add(str(u).lower())
    return users


def load_known_ids() -> set[str]:
    ids: set[str] = set()
    url_re = re.compile(r"/status(?:es)?/(\d{10,20})")
    for path in (TWEETS, TWEETS_IND, SALES, TWEETS_2526, PREMIUM, DATA / "tweets-company.jsonl"):
        if not path.is_file():
            continue
        with path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                tid = str(r.get("id") or "")
                if re.fullmatch(r"\d{10,20}", tid):
                    ids.add(tid)
                for key in ("url", "tweet_url"):
                    m = url_re.search(str(r.get(key) or ""))
                    if m:
                        ids.add(m.group(1))
    return ids


def is_company(username: str, company: set[str]) -> bool:
    return (username or "").lower() in company


def in_2526(created: str | None) -> bool:
    if not created:
        return False
    d = created[:10]
    return "2025-01-01" <= d <= "2026-08-15"


def keep_sale(text: str, parsed: dict[str, Any], username: str) -> bool:
    if not text or len(text) < 8:
        return False
    if looks_like_sale(text, parsed, username, True):
        return True
    if SALE_HINT.search(text) and (parsed.get("domains") or parsed.get("price_usd") is not None):
        return True
    return False


def extract_blockquotes(html: str) -> list[dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    for bq in BLOCKQUOTE_RE.findall(html):
        text = ""
        pm = P_RE.search(bq)
        if pm:
            text = strip_tags(pm.group(1))
        text = re.sub(r"\s*—\s*.*?\(@[A-Za-z0-9_]+\)\s*.*$", "", text).strip()
        username = None
        tid = None
        tdate = None
        mm = MDASH_RE.search(bq)
        if mm:
            username = mm.group(2)
            tid = mm.group(3)
            tdate = parse_date(strip_tags(mm.group(4)))
        if not tid:
            sm = STATUS_RE.search(bq)
            if sm:
                username = sm.group(1)
                tid = sm.group(2)
        if not tid or not username:
            continue
        if username.lower() in SKIP_USER:
            continue
        if not text or len(text) < 8:
            continue
        found[tid] = {
            "id": tid,
            "username": username,
            "text": text,
            "created_at": tdate,
            "url": f"https://x.com/{username}/status/{tid}",
        }
    return list(found.values())


def curl_fetch(url: str, timeout: int = 18) -> tuple[str, int, int, Path | None]:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", url)[:180]
    out = HTML_DIR / f"{slug}.html"
    cmd = [
        "curl", "-sL", "-A", UA,
        "--max-time", str(timeout),
        "-o", str(out),
        "-w", "%{http_code} %{size_download}",
        url,
    ]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 6)
        parts = (p.stdout or "").strip().split()
        code = int(parts[0]) if parts and parts[0].isdigit() else 0
        size = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else (
            out.stat().st_size if out.exists() else 0
        )
        return url, code, size, out
    except Exception:
        return url, 0, 0, None


def host_of(url: str) -> str:
    h = urlparse(url).netloc.lower()
    if h.startswith("www."):
        h = h[4:]
    return h


def append_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("a", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def tweet_row(rec: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": rec["id"],
        "url": rec["url"],
        "username": rec["username"],
        "text": rec["text"],
        "created_at": rec.get("created_at"),
        "domains": rec.get("domains") or [],
        "price_usd": rec.get("price_usd"),
        "price_raw": rec.get("price_raw"),
        "premium_tier": rec.get("premium_tier"),
        "source_page": rec.get("source_page"),
        "source": rec.get("source") or "web-mention",
        "collected_at": rec["collected_at"],
        "poster_kind": "individual",
        "query": rec.get("query"),
    }


def sale_row(rec: dict[str, Any]) -> dict[str, Any]:
    row = tweet_row(rec)
    row["tweet_url"] = rec["url"]
    return row


def main() -> int:
    urls_file = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/dd-hunt/urls/priority.txt")
    workers = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    urls = [u.strip() for u in urls_file.read_text().splitlines() if u.strip() and not u.startswith("#")]
    seen_u = set()
    uniq = []
    for u in urls:
        if u not in seen_u:
            seen_u.add(u)
            uniq.append(u)
    urls = uniq
    print(f"urls={len(urls)} workers={workers}", flush=True)

    company = load_company()
    known = load_known_ids()
    start_known = len(known)
    print(f"known_ids={start_known} company_handles={len(company)}", flush=True)

    collected_at = now_iso()
    new_rows: list[dict[str, Any]] = []
    skipped_company = 0
    skipped_nonsale = 0
    skipped_known = 0
    pages_ok = 0
    pages_fail = 0
    pages_noembed = 0
    pages_with_new = 0
    fail_hosts: Counter[str] = Counter()
    ok_hosts: Counter[str] = Counter()
    new_hosts: Counter[str] = Counter()
    new_users: Counter[str] = Counter()
    errors: list[str] = []
    site_status: dict[str, dict[str, int]] = {}

    def note_site(host: str, key: str) -> None:
        site_status.setdefault(host, Counter())
        site_status[host][key] += 1

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(curl_fetch, u) for u in urls]
        for i, fut in enumerate(as_completed(futs), 1):
            url, code, size, path = fut.result()
            host = host_of(url)
            if code != 200 or not path or not path.exists() or size < 1500:
                pages_fail += 1
                fail_hosts[host] += 1
                note_site(host, f"fail_{code or '0'}")
                errors.append(f"{code} {url}")
                if path and path.exists() and size < 8000:
                    path.unlink(missing_ok=True)
                if i % 40 == 0 or i == len(urls):
                    print(
                        f"  {i}/{len(urls)} new={len(new_rows)} fail={pages_fail} "
                        f"ok={pages_ok} elapsed={time.time()-t0:.1f}s",
                        flush=True,
                    )
                continue
            html = path.read_text(errors="replace")
            if "sucuri_cloudproxy_js" in html or "sgcaptcha" in html[:800] or "Just a moment" in html[:800]:
                pages_fail += 1
                fail_hosts[host] += 1
                note_site(host, "fail_challenge")
                errors.append(f"challenge {url}")
                path.unlink(missing_ok=True)
                continue
            tweets = extract_blockquotes(html)
            pages_ok += 1
            ok_hosts[host] += 1
            note_site(host, "ok")
            if not tweets:
                pages_noembed += 1
                note_site(host, "noembed")
                path.unlink(missing_ok=True)
                if i % 40 == 0 or i == len(urls):
                    print(
                        f"  {i}/{len(urls)} new={len(new_rows)} fail={pages_fail} "
                        f"ok={pages_ok} elapsed={time.time()-t0:.1f}s",
                        flush=True,
                    )
                continue
            cm = CANON.search(html) or CANON2.search(html)
            page_url = htmlmod.unescape(cm.group(1)).strip() if cm else url
            page_new = 0
            for tw in tweets:
                tid = tw["id"]
                if tid in known:
                    skipped_known += 1
                    continue
                user = tw["username"]
                if is_company(user, company):
                    skipped_company += 1
                    continue
                parsed = parse_sale(tw["text"])
                if not keep_sale(tw["text"], parsed, user):
                    skipped_nonsale += 1
                    continue
                known.add(tid)
                rec = {
                    "id": tid,
                    "url": tw["url"],
                    "username": user,
                    "text": tw["text"][:800],
                    "created_at": tw.get("created_at"),
                    "domains": parsed["domains"],
                    "price_usd": parsed["price_usd"],
                    "price_raw": parsed["price_raw"],
                    "premium_tier": parsed["premium_tier"],
                    "source_page": page_url,
                    "source": "web-mention",
                    "collected_at": collected_at,
                    "poster_kind": "individual",
                    "query": host,
                }
                new_rows.append(rec)
                page_new += 1
                new_hosts[host] += 1
                new_users[user] += 1
            if page_new:
                pages_with_new += 1
                note_site(host, "with_new")
            else:
                note_site(host, "embeds_nonew")
            if i % 40 == 0 or i == len(urls):
                print(
                    f"  {i}/{len(urls)} new={len(new_rows)} fail={pages_fail} "
                    f"ok={pages_ok} elapsed={time.time()-t0:.1f}s",
                    flush=True,
                )

    trows = [tweet_row(r) for r in new_rows]
    append_jsonl(TWEETS, trows)
    append_jsonl(TWEETS_IND, trows)
    append_jsonl(SALES, [sale_row(r) for r in new_rows])
    append_jsonl(PREMIUM, [tweet_row(r) for r in new_rows if r.get("premium_tier")])
    append_jsonl(TWEETS_2526, [tweet_row(r) for r in new_rows if in_2526(r.get("created_at"))])

    ind_total = 0
    if TWEETS_IND.is_file():
        with TWEETS_IND.open() as f:
            for line in f:
                if line.strip():
                    ind_total += 1

    progress = {
        "source": "web-mention",
        "collected_at": collected_at,
        "new_unique_individual_ids": len(new_rows),
        "start_known_numeric_ids": start_known,
        "individuals_total_after": ind_total,
        "tweets_appended": len(new_rows),
        "sales_appended": len(new_rows),
        "premium_appended": sum(1 for r in new_rows if r.get("premium_tier")),
        "tweets_2025_2026_appended": sum(1 for r in new_rows if in_2526(r.get("created_at"))),
        "pages_queued": len(urls),
        "pages_ok": pages_ok,
        "pages_fail": pages_fail,
        "pages_noembed": pages_noembed,
        "pages_with_new": pages_with_new,
        "skipped_company": skipped_company,
        "skipped_nonsale": skipped_nonsale,
        "skipped_known": skipped_known,
        "new_by_host": dict(new_hosts),
        "ok_by_host": dict(ok_hosts),
        "fail_by_host": dict(fail_hosts),
        "site_status": {k: dict(v) for k, v in site_status.items()},
        "top_new_usernames": new_users.most_common(25),
        "sample_new_urls": [r["url"] for r in new_rows[:12]],
        "sample_pages": [r["source_page"] for r in new_rows[:12]],
        "errors": errors[-40:],
        "notes": [
            "Only twitter-tweet blockquotes with real /status/ IDs. No invented IDs.",
            "Skipped company/marketplace/news handles via company-accounts.json + extras.",
            "Did not scrape x.com HTML, Nitter, or X API.",
        ],
    }
    PROGRESS.write_text(json.dumps(progress, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({
        "new_unique_individual_ids": len(new_rows),
        "individuals_total_after": ind_total,
        "by_host": dict(new_hosts),
        "top_users": new_users.most_common(15),
        "pages_ok": pages_ok,
        "pages_fail": pages_fail,
        "pages_noembed": pages_noembed,
        "fail_by_host": dict(fail_hosts),
        "sample": [r["url"] for r in new_rows[:8]],
    }, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
