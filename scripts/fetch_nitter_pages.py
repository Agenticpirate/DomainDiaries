#!/usr/bin/env python3
"""Download public Nitter HTML pages. Cookie comes from env NITTER_COOKIE."""
from __future__ import annotations

import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "https://nitter.poast.org"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
OUT = Path("/workspace/domain-diaries/data/raw/pages")
MORE_RE = re.compile(r'class="show-more"[^>]*>\s*<a href="([^"]+)"', re.I)


def fetch(url: str, cookie: str) -> tuple[int, str]:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": UA, "Accept": "text/html", "Cookie": cookie},
    )
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return r.getcode(), r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def crawl(start: str, slug: str, cookie: str, max_pages: int) -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    url = start
    n = 0
    for i in range(1, max_pages + 1):
        code, html = fetch(url, cookie)
        path = OUT / f"{slug}-{i:03d}.html"
        path.write_text(html, encoding="utf-8")
        n += 1
        items = html.count("timeline-item")
        print(f"{slug} p{i} {code} items={items} bytes={len(html)}", flush=True)
        if "Verifying your browser" in html or items == 0:
            break
        m = MORE_RE.search(html)
        if not m:
            break
        more = m.group(1).replace("&amp;", "&")
        if more.startswith("http"):
            url = more
        elif more.startswith("/"):
            url = BASE + more
        else:
            path_only = urllib.parse.urlparse(url).path
            url = BASE + path_only + (more if more.startswith("?") else "?" + more)
        time.sleep(0.65)
    return n


def main() -> int:
    cookie = os.environ.get("NITTER_COOKIE", "").strip()
    if not cookie:
        print("NITTER_COOKIE missing", file=sys.stderr)
        return 2
    jobs = [
        ("justsold", BASE + "/search?f=tweets&q=just+sold+domain", 20),
        ("soldfor", BASE + "/search?f=tweets&q=%22sold%20for%22%20domain", 20),
        ("domainsold", BASE + "/search?f=tweets&q=domain%20sold%20%24", 15),
        ("justsoldcom", BASE + "/search?f=tweets&q=%22just%20sold%22%20.com", 15),
        ("soldforcom", BASE + "/search?f=tweets&q=%22sold%20for%22%20.com", 20),
        ("justclosed", BASE + "/search?f=tweets&q=%22just%20closed%22%20domain", 10),
        ("namebio", BASE + "/search?f=tweets&q=namebio%20sold", 10),
        ("escrow", BASE + "/search?f=tweets&q=escrow.com%20sold%20domain", 8),
        ("hashdomains", BASE + "/search?f=tweets&q=%23domains%20sold", 10),
        ("fromdnw", BASE + "/search?f=tweets&q=from%3ADomainNameWire%20sold", 10),
        ("fromrosener", BASE + "/search?f=tweets&q=from%3Aandrewrosener%20sold", 8),
        ("fromdi", BASE + "/search?f=tweets&q=from%3ADomainInvesting%20sold", 8),
        ("fromshane", BASE + "/search?f=tweets&q=from%3ADomainShane%20sold", 8),
        ("fromnamebio", BASE + "/search?f=tweets&q=from%3ANameBio%20sold", 8),
        ("p_DomainNameWire", BASE + "/DomainNameWire", 6),
        ("p_andrewrosener", BASE + "/andrewrosener", 6),
        ("p_jamesiles", BASE + "/jamesiles", 4),
        ("p_ishmilly", BASE + "/ishmilly", 4),
        ("p_DomainSherpa", BASE + "/DomainSherpa", 4),
        ("p_DNJournal", BASE + "/DNJournal", 4),
        ("p_Escrow_com", BASE + "/Escrow_com", 4),
        ("p_DomainInvesting", BASE + "/DomainInvesting", 6),
        ("p_DomainShane", BASE + "/DomainShane", 6),
        ("p_MorganLinton", BASE + "/MorganLinton", 4),
        ("p_NameBio", BASE + "/NameBio", 4),
        ("p_AndrewAllemann", BASE + "/AndrewAllemann", 4),
        ("p_GoDaddyAuctions", BASE + "/GoDaddyAuctions", 4),
    ]
    total = 0
    for slug, url, pages in jobs:
        total += crawl(url, slug, cookie, pages)
    print("pages_saved", total)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
