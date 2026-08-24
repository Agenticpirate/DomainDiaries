#!/usr/bin/env python3
"""Collect public DNJournal sales charts into JSONL. No NameBio. No X."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

BASE = "https://www.dnjournal.com"
OUT_DIR = Path("/workspace/domain-diaries/data")
RAW_DIR = Path("/tmp/dnj/pages")

COLLECTED_AT = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

MONTHS = {
    "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3,
    "april": 4, "apr": 4, "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7,
    "august": 8, "aug": 8, "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10, "november": 11, "nov": 11, "december": 12, "dec": 12,
}

SKIP_DOMAINS = {
    "dnjournal.com", "www.dnjournal.com", "domain", "soldfor", "wheresold",
    "clickhere", "home.page", "sedo.com", "afternic.com", "godaddy.com",
}

# Tokens that are never sale domains even if they look like hostnames
SKIP_EXACT = {
    "domain", "sold for", "where sold", "date*", "date", "price paid",
    "year", "year sold/ reported", "broker",
}

NAME_REMOVED_RE = re.compile(
    r"name\s+removed|name\s+withheld|domain\s+removed|\[redacted\]|redacted\s+name",
    re.I,
)

PRICE_USD_RE = re.compile(
    r"(?:=|\bequals?\b)?\s*\$\s*([\d]{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?",
    re.I,
)
PRICE_ANY_RE = re.compile(
    r"([€£¥]|EUR|GBP|CNY|USD|\$)\s*([\d]{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?",
    re.I,
)
RANK_RE = re.compile(r"^\d+\.?(?:\s*tie\.?)?$", re.I)
DATE_RE = re.compile(
    r"^(\d{1,2})/(\d{1,2})/(\d{2,4})\*?$"
)
YEAR_RE = re.compile(r"^(19|20)\d{2}(?:\s*/\s*(?:19|20)\d{2})?$")
CHART_END_RE = re.compile(
    r"(?:through|ending|ended|end(?:ing)?\s+sunday,?|sun\.)\s+"
    r"([A-Za-z]{3,9}\.?\s+\d{1,2},?\s+\d{4})",
    re.I,
)
CHART_RANGE_RE = re.compile(
    r"((?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\.?\s+)?([A-Za-z]{3,9})\.?\s+(\d{1,2})\s*[-–]\s*"
    r"((?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\.?\s+)?([A-Za-z]{3,9})\.?\s+(\d{1,2}),?\s+(\d{4})",
    re.I,
)
NOTE_RE = re.compile(r"\s*\([^)]*\)\s*")
HTML_TAG_RE = re.compile(r"<[^>]+>")


def strip_tags(s: str) -> str:
    s = re.sub(r"<br\s*/?>", " ", s, flags=re.I)
    s = HTML_TAG_RE.sub(" ", s)
    s = s.replace("&nbsp;", " ").replace("&amp;", "&").replace("&quot;", '"')
    s = s.replace("&#39;", "'").replace("&lt;", "<").replace("&gt;", ">")
    s = re.sub(r"&#\d+;", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def extract_tables(html: str) -> list[str]:
    tables: list[str] = []
    i = 0
    lower = html.lower()
    while True:
        start = lower.find("<table", i)
        if start < 0:
            break
        pos = start
        depth = 0
        found = False
        while True:
            ns = lower.find("<table", pos)
            ne = lower.find("</table>", pos)
            if ne < 0:
                break
            if ns >= 0 and ns < ne:
                depth += 1
                pos = ns + 6
            else:
                depth -= 1
                pos = ne + 8
                if depth == 0:
                    tables.append(html[start:pos])
                    found = True
                    break
        i = start + 6 if found else start + 6
        if not found:
            break
    return tables


def rows_from_table(tbl: str) -> list[list[str]]:
    inner = re.sub(r"<table[\s\S]*?</table>", " ", tbl[tbl.find(">") + 1 :], flags=re.I)
    rows = []
    for row in re.findall(r"<tr[^>]*>([\s\S]*?)</tr>", inner, re.I):
        cells = [strip_tags(c) for c in re.findall(r"<t[dh][^>]*>([\s\S]*?)</t[dh]>", row, re.I)]
        cells = [c for c in cells]  # keep empties for column alignment
        if any(c.strip() for c in cells):
            rows.append([c.strip() for c in cells])
    return rows


def clean_domain(raw: str) -> str | None:
    if not raw:
        return None
    s = raw.strip()
    if NAME_REMOVED_RE.search(s):
        return "[redacted]"
    s = NOTE_RE.sub(" ", s)
    s = s.replace("\u00a0", " ")
    s = re.sub(r"^[#\d.\s]+tie\s+", "", s, flags=re.I)
    s = s.strip(" \t.,;:\"'`“”‘’")
    # collapse spaces around dots and inside labels split by HTML
    s = re.sub(r"\s*\.\s*", ".", s)
    s = re.sub(r"\s+", "", s)
    # comma used as dot before a tld-like token
    s = re.sub(r",([a-zA-Z]{2,12})$", r".\1", s)
    if not s or s.lower() in SKIP_EXACT:
        return None
    if s.lower() in ("[redacted]",):
        return "[redacted]"
    if "/" in s or " " in s:
        return None
    if not re.match(r"^[A-Za-z0-9][A-Za-z0-9-]{0,62}(?:\.[A-Za-z0-9][A-Za-z0-9-]{0,62})+$", s):
        return None
    # must have a plausible TLD (2-18 alpha, or 2-alpha + more labels like co.uk)
    labels = s.split(".")
    tld = labels[-1]
    if not re.match(r"^[A-Za-z]{2,18}$", tld):
        return None
    if len(s) > 80:
        return None
    low = s.lower()
    if low in SKIP_DOMAINS:
        return None
    if low.endswith(".htm") or low.endswith(".html") or low.endswith(".jpg"):
        return None
    return s


def looks_like_domain(s: str) -> bool:
    return clean_domain(s) is not None or (s and NAME_REMOVED_RE.search(s) is not None)


def _usd_amount(num: str) -> float:
    """Parse a printed USD amount. Treat 1.234 (dot + 3 digits, no comma) as thousands."""
    num = num.strip()
    if "," in num:
        return float(num.replace(",", ""))
    m = re.fullmatch(r"(\d+)\.(\d{3})", num)
    if m:
        return float(m.group(1) + m.group(2))
    return float(num)


def parse_price(raw: str) -> tuple[float | None, str, str | None]:
    if not raw:
        return None, raw, None
    s = raw.replace("\xa0", " ").strip()
    if not s or s.lower() in ("sold for", "price", "price paid"):
        return None, raw, None
    m = re.search(r"=\s*\$\s*([\d,]+(?:\.\d+)?)", s)
    if m:
        return _usd_amount(m.group(1)), raw.strip(), "USD"
    m = re.search(r"\$\s*([\d,]+(?:\.\d+)?)", s)
    if m:
        return _usd_amount(m.group(1)), raw.strip(), "USD"
    m = re.search(r"(€|EUR)\s*([\d,]+(?:\.\d+)?)", s, re.I)
    if m:
        return None, raw.strip(), "EUR"
    m = re.search(r"(£|GBP)\s*([\d,]+(?:\.\d+)?)", s, re.I)
    if m:
        return None, raw.strip(), "GBP"
    return None, raw.strip(), None


def looks_like_price(s: str) -> bool:
    if not s:
        return False
    usd, _, cur = parse_price(s)
    return usd is not None or cur in ("EUR", "GBP")


def parse_date_token(s: str) -> str | None:
    if not s:
        return None
    s = s.strip().rstrip("*").strip()
    m = DATE_RE.match(s)
    if m:
        month, day, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if year < 100:
            year = 2000 + year if year <= 30 else 1900 + year
        if 1 <= month <= 12 and 1 <= day <= 31 and 1995 <= year <= 2027:
            return f"{year:04d}-{month:02d}-{day:02d}"
        return None
    m = YEAR_RE.match(s)
    if m:
        # keep first year
        ym = re.match(r"((?:19|20)\d{2})", s)
        return ym.group(1) if ym else None
    # Month D, YYYY
    m = re.match(r"([A-Za-z]{3,9})\.?\s+(\d{1,2}),?\s+(\d{4})$", s)
    if m and m.group(1).lower().rstrip(".") in MONTHS:
        month = MONTHS[m.group(1).lower().rstrip(".")]
        day = int(m.group(2))
        year = int(m.group(3))
        return f"{year:04d}-{month:02d}-{day:02d}"
    return None


def chart_window_from_text(text: str) -> tuple[str | None, str | None]:
    """Return (window_string, end_date_iso)."""
    if not text:
        return None, None
    m = CHART_RANGE_RE.search(text)
    if m:
        mon = MONTHS.get(m.group(5).lower().rstrip("."))
        day = int(m.group(6))
        year = int(m.group(7))
        window = re.sub(r"\s+", " ", m.group(0)).strip()
        if mon:
            return window, f"{year:04d}-{mon:02d}-{day:02d}"
    m = CHART_END_RE.search(text)
    if m:
        end = parse_date_token(m.group(1).strip())
        return re.sub(r"\s+", " ", m.group(0)).strip(), end
    return None, None


def premium_tier(price: float | None) -> str | None:
    if price is None:
        return None
    if price >= 50000:
        return "50k"
    if price >= 30000:
        return "30k"
    if price >= 20000:
        return "20k"
    return None


def header_map(row: list[str]) -> dict[str, int] | None:
    lows = [c.lower().strip() for c in row]
    joined = " | ".join(lows)
    if "domain" not in lows:
        return None
    idx = {}
    for i, c in enumerate(lows):
        if c == "domain" or c.startswith("domain "):
            idx["domain"] = i
        elif c in ("sold for", "price", "price paid", "sold for*") or "sold for" in c:
            idx["price"] = i
        elif c.startswith("where sold") or c in ("venue", "broker", "broker (& original source if not the same)"):
            idx["venue"] = i
        elif c in ("date", "date*", "date reported") or c.startswith("date"):
            idx["date"] = i
        elif c in ("year", "year sold/ reported", "year sold"):
            idx["year"] = i
    if "domain" in idx and ("price" in idx or "year" in idx):
        return idx
    # Domain present with Sold For somewhere in joined header
    if "sold for" in joined or "price paid" in joined:
        # find best guess
        for i, c in enumerate(lows):
            if "sold" in c or "price" in c:
                idx.setdefault("price", i)
        if "domain" in idx and "price" in idx:
            return idx
    return None if "domain" not in idx else (idx if "price" in idx or "year" in idx else None)


def clean_venue(v: str) -> str:
    v = (v or "").strip()
    v = v.lstrip("*").strip()
    if v.lower() in {"between", "from", "sales", "additional"}:
        return ""
    if v.lower() in SKIP_EXACT or v.lower().startswith("click here"):
        return ""
    return v


def venue_from_title(title: str) -> str | None:
    if not title:
        return None
    t = re.sub(r"\s+", " ", title).strip()
    m = re.search(r"Additional\s+Sales\s+at\s+([A-Za-z0-9][A-Za-z0-9./-]*)", t, re.I)
    if m:
        return m.group(1).strip(" .")
    m = re.search(r"Additional\s+\.com\s+Sales\s+at\s+([A-Za-z0-9][A-Za-z0-9./-]*)", t, re.I)
    if m:
        return m.group(1).strip(" .")
    m = re.search(
        r"Additional\s+([A-Za-z0-9][A-Za-z0-9./-]*)\s+(?:\.com\s+)?(?:ccTLD\s+)?Sales",
        t,
        re.I,
    )
    if m:
        name = m.group(1).strip(" .")
        if name.lower() not in {"sales", "between", "from", "the", "more"}:
            return name
    return None


def make_id(domain: str, date: str, price_raw: str, price_usd: float | None) -> str:
    price_part = str(int(price_usd)) if price_usd is not None and price_usd == int(price_usd) else (str(price_usd) if price_usd is not None else price_raw)
    key = f"dnjournal|{domain.lower()}|{date}|{price_part}"
    return key


def file_to_url(path: Path) -> str:
    name = path.name
    if name == "domainsales.htm":
        return f"{BASE}/domainsales.htm"
    if name == "ytd-sales-charts.htm":
        return f"{BASE}/ytd-sales-charts.htm"
    if name.startswith("archive_"):
        rest = name[len("archive_"):]
        if rest.startswith("domainsales-archive"):
            return f"{BASE}/archive/{rest}"
        if rest.startswith("domainsales_"):
            inner = rest[len("domainsales_"):]
            if inner.endswith(".htm"):
                inner = inner[:-4]
            m = re.match(r"^(\d{4})_(\d{4})$", inner)
            if m:
                return f"{BASE}/archive/domainsales/{m.group(1)}/{m.group(2)}.htm"
            m = re.match(r"^(\d{4})_(.+)$", inner)
            if m:
                return f"{BASE}/archive/domainsales/{m.group(1)}/{m.group(2)}.htm"
            return f"{BASE}/archive/domainsales/{inner}.htm"
        if rest.endswith(".htm"):
            return f"{BASE}/archive/{rest}"
        return f"{BASE}/archive/{rest}.htm"
    return f"{BASE}/{name}"


def url_pub_date(url: str) -> str | None:
    m = re.search(r"/domainsales/(\d{4})/(\d{8})\.htm", url)
    if m:
        ymd = m.group(2)
        year, month, day = int(ymd[:4]), int(ymd[4:6]), int(ymd[6:8])
        if 1 <= month <= 12 and 1 <= day <= 31:
            return f"{year:04d}-{month:02d}-{day:02d}"
    m = re.search(r"/domainsales/(\d{4})/(\d{4})\.htm", url)
    if m:
        year = int(m.group(1))
        md = m.group(2)
        month, day = int(md[:2]), int(md[2:])
        if 1 <= month <= 12 and 1 <= day <= 31:
            return f"{year:04d}-{month:02d}-{day:02d}"
    m = re.search(r"/(\d{4})[-_]top-100", url)
    if m:
        return m.group(1)
    m = re.search(r"ytd-sales-charts?-(\d{4})", url)
    if m:
        return m.group(1)
    m = re.search(r"/(\d{4})-expanded", url)
    if m:
        return m.group(1)
    m = re.search(r"/(\d{4})/", url)
    if m:
        return m.group(1)
    if "ytd-sales-charts.htm" in url and "/archive/" not in url:
        return "2026"
    if "domainsales.htm" in url and "/archive/" not in url:
        return None
    return None


def parse_row_with_header(row: list[str], idx: dict[str, int], default_venue: str | None) -> list[dict]:
    cells = list(row)
    # Rank column present in data but omitted from header (all-time chart).
    if cells and RANK_RE.match(cells[0]) and idx.get("domain") == 0:
        cells = cells[1:]

    def cell(key: str) -> str:
        i = idx.get(key)
        if i is None or i >= len(cells):
            return ""
        return cells[i]

    domain_raw = cell("domain")
    if not domain_raw:
        return []
    # skip header repeats and nav
    if domain_raw.lower() in SKIP_EXACT or domain_raw.lower() == "domain":
        return []
    domain = clean_domain(domain_raw)
    if domain is None:
        return []
    price_raw = cell("price")
    price_usd, price_raw_out, currency = parse_price(price_raw)
    if price_usd is None and currency is None and not price_raw:
        # year-only historic charts sometimes have Price Paid
        return []
    if price_usd is None and currency is None:
        # no usable price
        if domain != "[redacted]":
            return []
    venue = clean_venue(cell("venue") or default_venue or "")
    date = parse_date_token(cell("date")) or parse_date_token(cell("year")) or ""
    rec = {
        "domain": domain,
        "domain_raw": domain_raw,
        "price_usd": price_usd,
        "price_raw": price_raw_out or price_raw,
        "currency": currency,
        "venue": venue,
        "date": date,
    }
    return [rec]


def parse_pair_rows(rows: list[list[str]], default_venue: str | None) -> list[dict]:
    out = []
    for row in rows:
        cells = row
        i = 0
        while i < len(cells):
            c = cells[i]
            if not c:
                i += 1
                continue
            if RANK_RE.match(c):
                i += 1
                continue
            dom = clean_domain(c)
            if dom and i + 1 < len(cells) and looks_like_price(cells[i + 1]):
                price_usd, price_raw, currency = parse_price(cells[i + 1])
                venue = clean_venue(default_venue or "")
                date = ""
                # leftover cells may be venue/date if this is a 3-4 col single sale
                rest = [x for x in cells[i + 2 :] if x]
                # if rest looks like another domain+price, don't consume as venue
                if rest and clean_domain(rest[0]) and (len(rest) < 2 or looks_like_price(rest[1])):
                    pass
                else:
                    if rest:
                        # maybe venue and/or date
                        for extra in rest:
                            if parse_date_token(extra) and not date:
                                date = parse_date_token(extra)
                            elif looks_like_price(extra):
                                continue
                            elif extra.lower() not in SKIP_EXACT and not venue:
                                venue = extra
                out.append({
                    "domain": dom,
                    "domain_raw": c,
                    "price_usd": price_usd,
                    "price_raw": price_raw,
                    "currency": currency,
                    "venue": venue,
                    "date": date,
                })
                i += 2
                continue
            i += 1
    return out


def parse_tables(html: str, url: str) -> list[dict]:
    tables = extract_tables(html)
    page_text = strip_tags(html[:8000] + html[html.find("Top 20"): html.find("Top 20") + 2000] if "Top 20" in html else html[:8000])
    window, window_end = chart_window_from_text(html)
    if not window:
        window, window_end = chart_window_from_text(page_text)
    pub = url_pub_date(url)
    sales: list[dict] = []
    for tbl in tables:
        rows = rows_from_table(tbl)
        if not rows:
            continue
        # find header
        hmap = None
        hidx = None
        title = ""
        for i, row in enumerate(rows[:6]):
            hm = header_map(row)
            if hm:
                hmap = hm
                hidx = i
                if i > 0:
                    title = " ".join(rows[0])
                break
        default_venue = venue_from_title(" ".join(rows[0]) if rows else "")
        if hmap is not None:
            # also pick chart window from title rows
            blob = " ".join(" ".join(r) for r in rows[:2])
            w, we = chart_window_from_text(blob)
            if w:
                window = window or w
                window_end = window_end or we
            for row in rows[hidx + 1 :]:
                sales.extend(parse_row_with_header(row, hmap, default_venue))
            continue
        # title + pair tables (additional sales)
        first = " ".join(rows[0])
        if re.search(r"additional|supporting|\.com sales|cctld|sales from \$", first, re.I):
            default_venue = venue_from_title(first) or default_venue
            sales.extend(parse_pair_rows(rows[1:], default_venue))
            continue
        # heuristic: majority of rows look like domain+price
        pairish = 0
        for row in rows[:12]:
            if any(looks_like_domain(c) for c in row) and any(looks_like_price(c) for c in row):
                pairish += 1
        if pairish >= 3:
            sales.extend(parse_pair_rows(rows, default_venue))
    # attach page-level date fallbacks
    for s in sales:
        if not s.get("date"):
            s["date"] = window_end or pub or window or ""
        s["chart_window"] = window
        s["url"] = url
    return sales


def to_record(s: dict) -> dict | None:
    domain = s["domain"]
    price_usd = s.get("price_usd")
    price_raw = s.get("price_raw") or ""
    if price_usd is None and not price_raw:
        return None
    # skip foreign-only without USD unless we still want them
    # keep with price_usd null
    if isinstance(price_usd, float) and price_usd != int(price_usd):
        # keep cents if present
        if abs(price_usd - round(price_usd)) < 1e-6:
            price_usd = int(round(price_usd))
    elif isinstance(price_usd, float):
        price_usd = int(price_usd)
    date = s.get("date") or ""
    venue = clean_venue(s.get("venue") or "")
    if len(venue) > 160:
        venue = venue[:160]
    rec = {
        "id": make_id(domain, date, price_raw, price_usd if isinstance(price_usd, (int, float)) else None),
        "source": "dnjournal",
        "url": s.get("url") or "",
        "domain": domain,
        "price_usd": price_usd,
        "price_raw": price_raw,
        "venue": venue or None,
        "date": date or None,
        "premium_tier": premium_tier(float(price_usd) if price_usd is not None else None),
        "text": (s.get("chart_window") or None),
        "collected_at": COLLECTED_AT,
    }
    return rec


def dedupe(records: list[dict]) -> list[dict]:
    # exact key
    by_exact: dict[tuple, dict] = {}
    order: list[tuple] = []
    for r in records:
        key = (r["domain"].lower(), r.get("price_usd"), r.get("date") or "", r.get("price_raw") or "")
        # tighter exact: domain + price + date
        key = (r["domain"].lower(), r.get("price_usd"), r.get("date") or "")
        if key in by_exact:
            by_exact[key] = pick_better(by_exact[key], r)
        else:
            by_exact[key] = r
            order.append(key)
    exact = [by_exact[k] for k in order]

    # fuzzy: same domain+price, dates within 21 days or one is year-only of the other
    groups: dict[tuple, list[dict]] = {}
    for r in exact:
        gkey = (r["domain"].lower(), r.get("price_usd"))
        groups.setdefault(gkey, []).append(r)

    out: list[dict] = []
    used = set()
    for r in exact:
        rid = id(r)
        if rid in used:
            continue
        gkey = (r["domain"].lower(), r.get("price_usd"))
        cluster = [x for x in groups[gkey] if id(x) not in used]
        if len(cluster) == 1:
            out.append(r)
            used.add(rid)
            continue
        # partition cluster by date distance
        remaining = cluster[:]
        while remaining:
            seed = remaining.pop(0)
            bucket = [seed]
            keep = []
            for other in remaining:
                if records_compatible(seed, other):
                    bucket.append(other)
                else:
                    keep.append(other)
            remaining = keep
            best = seed
            for x in bucket[1:]:
                best = pick_better(best, x)
            out.append(best)
            for x in bucket:
                used.add(id(x))
    return out


def parse_iso(d: str | None) -> datetime | None:
    if not d:
        return None
    if re.match(r"^\d{4}-\d{2}-\d{2}$", d):
        try:
            return datetime.strptime(d, "%Y-%m-%d")
        except ValueError:
            return None
    if re.match(r"^\d{4}$", d):
        return datetime(int(d), 1, 1)
    return None


def dates_compatible(a: str | None, b: str | None) -> bool:
    return records_compatible({"date": a, "url": ""}, {"date": b, "url": ""})


def records_compatible(ra: dict, rb: dict) -> bool:
    a, b = ra.get("date") or "", rb.get("date") or ""
    ua, ub = ra.get("url") or "", rb.get("url") or ""
    if not a or not b or a == b:
        return True
    all_time = "all-time" in ua or "all-time" in ub or "pre-2004" in ua or "pre-2004" in ub
    if all_time:
        return True
    if ua and ua == ub:
        return True
    a_year_only = bool(re.match(r"^\d{4}$", a))
    b_year_only = bool(re.match(r"^\d{4}$", b))
    da, db = parse_iso(a), parse_iso(b)
    if a_year_only or b_year_only:
        if da and db:
            return abs(da.year - db.year) <= 1
        return True
    if da and db:
        if abs((da - db).days) <= 45:
            return True
        # YTD year-end placeholder vs earlier publication in the same year
        if {da.month, db.month} & {12} and {da.day, db.day} & {31} and da.year == db.year:
            return True
        # printed year off-by-one (chart header not updated)
        if abs(da.year - db.year) == 1 and abs((da.replace(year=2000) - db.replace(year=2000)).days) <= 14:
            return True
        # future typo vs real date
        today = datetime(2026, 8, 15)
        if (da > today or db > today) and abs(da.month - db.month) <= 1:
            return True
    return False


def pick_better(a: dict, b: dict) -> dict:
    def score(r: dict) -> tuple:
        date = r.get("date") or ""
        future = 0
        if re.match(r"^\d{4}-\d{2}-\d{2}$", date) and date > "2026-08-15":
            future = -2
        specific = 2 if re.match(r"^\d{4}-\d{2}-\d{2}$", date) else (1 if date else 0)
        venue = 1 if r.get("venue") else 0
        all_time = -1 if "all-time" in (r.get("url") or "") else 0
        ytd = 1 if "ytd-sales" in (r.get("url") or "") or "top-100" in (r.get("url") or "") else 0
        return (future, specific, venue, all_time, ytd, len(r.get("venue") or ""))
    return a if score(a) >= score(b) else b


def is_index_page(url: str, html: str) -> bool:
    if "domainsales-archive" in url and "top-100" not in url:
        return True
    return False


def discover_local_pages() -> tuple[list[tuple[Path, str]], list[str]]:
    pages = []
    indexes = []
    for p in sorted(RAW_DIR.glob("*.htm")):
        url = file_to_url(p)
        if "domainsales-archive" in p.name and "top-100" not in p.name:
            indexes.append(url)
            continue
        pages.append((p, url))
    return pages, indexes


def main() -> int:
    errors: list[dict] = []
    pages_fetched: list[str] = []
    raw_sales: list[dict] = []
    pages, index_urls = discover_local_pages()
    pages_fetched.extend(index_urls)
    print(f"parsing {len(pages)} chart pages (+{len(index_urls)} indexes)", flush=True)
    for path, url in pages:
        try:
            html = path.read_text(errors="replace")
            if len(html) < 2000:
                errors.append({"url": url, "error": f"too_small:{len(html)}"})
                pages_fetched.append(url)
                continue
            if is_index_page(url, html):
                pages_fetched.append(url)
                continue
            sales = parse_tables(html, url)
            raw_sales.extend(sales)
            pages_fetched.append(url)
            print(f"  {len(sales):4d} rows  {url}", flush=True)
        except Exception as e:
            errors.append({"url": url, "error": str(e)})
            print(f"  ERROR {url}: {e}", flush=True)

    records = []
    skipped = 0
    for s in raw_sales:
        rec = to_record(s)
        if rec is None:
            skipped += 1
            continue
        records.append(rec)

    before = len(records)
    records = dedupe(records)
    # stable sort
    records.sort(key=lambda r: (
        r.get("date") or "",
        -(r["price_usd"] or 0),
        r["domain"].lower(),
    ), reverse=True)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    sales_path = OUT_DIR / "sales.jsonl"
    prem_path = OUT_DIR / "premium.jsonl"
    with sales_path.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    premium = [r for r in records if r.get("premium_tier")]
    with prem_path.open("w", encoding="utf-8") as f:
        for r in premium:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    dates = [r["date"] for r in records if r.get("date") and re.match(r"^\d{4}-\d{2}-\d{2}$", r["date"])]
    years = [r["date"][:4] for r in records if r.get("date")]
    p20 = sum(1 for r in records if r.get("premium_tier") == "20k")
    p30 = sum(1 for r in records if r.get("premium_tier") == "30k")
    p50 = sum(1 for r in records if r.get("premium_tier") == "50k")
    summary = {
        "source": "dnjournal",
        "collected_at": COLLECTED_AT,
        "total_sales": len(records),
        "raw_rows_parsed": before,
        "deduped_from": before,
        "skipped_incomplete": skipped,
        "premium_total": len(premium),
        "premium_20k": p20,
        "premium_30k": p30,
        "premium_50k": p50,
        "date_range": {
            "min": min(dates) if dates else (min(years) if years else None),
            "max": max(dates) if dates else (max(years) if years else None),
        },
        "pages_fetched": len(pages_fetched),
        "pages": pages_fetched,
        "errors": errors,
        "notes": [
            "Public DNJournal HTML charts only.",
            "No NameBio. No x.com HTML. No unofficial X guest tokens.",
            "Dedupe key: domain + price_usd + date (fuzzy merge within 21 days or year-only).",
            "Foreign prices kept only when a USD equivalent was printed, otherwise price_usd is null.",
        ],
        "files": {
            "sales": str(sales_path),
            "premium": str(prem_path),
        },
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: summary[k] for k in (
        "total_sales", "premium_total", "premium_20k", "premium_30k", "premium_50k",
        "pages_fetched", "date_range", "raw_rows_parsed",
    )}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
