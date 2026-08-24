#!/usr/bin/env python3
"""Parse domain names and USD prices from a domain-sale post.

Used by collect_x_sales.py. Run this file directly for the self-check
(no network, no API token).
"""

from __future__ import annotations

import re
import sys
from typing import Any

# Social / shortener hosts that appear as links, not as the name being sold.
_SKIP_HOSTS = {
    "t.co",
    "x.com",
    "twitter.com",
    "pic.twitter.com",
    "bit.ly",
    "ow.ly",
    "tinyurl.com",
    "buff.ly",
    "dlvr.it",
    "youtu.be",
    "youtube.com",
    "instagram.com",
    "facebook.com",
    "fb.com",
    "linkedin.com",
    "threads.net",
    "bsky.app",
    "reddit.com",
    "tiktok.com",
    "google.com",
    "goo.gl",
}

# Two-label public suffixes common in the aftermarket.
_MULTI_TLDS = (
    "co.uk",
    "org.uk",
    "ac.uk",
    "me.uk",
    "com.au",
    "net.au",
    "org.au",
    "co.nz",
    "co.za",
    "com.br",
    "co.in",
    "org.in",
    "com.mx",
    "co.jp",
    "com.cn",
    "com.sg",
    "co.kr",
    "com.hk",
    "co.il",
)

# Single-label TLDs that show up in domain-sale posts.
_TLDS = (
    "com",
    "net",
    "org",
    "io",
    "ai",
    "co",
    "xyz",
    "app",
    "dev",
    "me",
    "info",
    "biz",
    "us",
    "tv",
    "cc",
    "to",
    "so",
    "gg",
    "sh",
    "ly",
    "is",
    "it",
    "es",
    "fr",
    "de",
    "nl",
    "ch",
    "se",
    "no",
    "fi",
    "pl",
    "cz",
    "be",
    "at",
    "dk",
    "ie",
    "pt",
    "uk",
    "ca",
    "au",
    "in",
    "jp",
    "kr",
    "cn",
    "tw",
    "hk",
    "sg",
    "my",
    "ph",
    "id",
    "vn",
    "br",
    "mx",
    "ar",
    "cl",
    "za",
    "ng",
    "ke",
    "ae",
    "sa",
    "il",
    "tr",
    "ru",
    "ua",
    "shop",
    "store",
    "online",
    "site",
    "tech",
    "cloud",
    "digital",
    "agency",
    "media",
    "news",
    "blog",
    "club",
    "vip",
    "pro",
    "nyc",
    "inc",
    "llc",
    "law",
    "health",
    "finance",
    "money",
    "crypto",
    "nft",
    "dao",
    "web3",
    "xyz",
)

_LABEL = r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?"
_MULTI_ALT = "|".join(re.escape(t) for t in _MULTI_TLDS)
_TLD_ALT = "|".join(re.escape(t) for t in _TLDS)

# example.com / foo.co.uk — not 25.00 or .com alone.
_DOMAIN_RE = re.compile(
    rf"(?<![a-zA-Z0-9-])(?:https?://)?(?:www\.)?"
    rf"((?:{_LABEL}\.)+(?:{_MULTI_ALT}|{_TLD_ALT}))"
    rf"(?![a-zA-Z0-9-])",
    re.IGNORECASE,
)

# Sale-ish words used to score a price candidate.
_SALE_NEAR = re.compile(
    r"\b(sold|selling|closed|closing|bought|acquired|acquisition|"
    r"paid|paying|escrow)\b",
    re.IGNORECASE,
)
_NOISE_NEAR = re.compile(
    r"\b(followers?|likes?|views?|impressions?|retweets?|reposts?|"
    r"subscribers?|people|users|members)\b",
    re.IGNORECASE,
)

# Ordered from more specific to less. Each match has raw + num + optional dec/suf/word.
_PRICE_RES = [
    # $30 million / 2.5 million / 25 thousand (before bare $30)
    re.compile(
        r"(?P<raw>\$?\s*(?P<num>\d{1,3}(?:,\d{3})+|\d+)(?:\.(?P<dec>\d+))?\s*(?P<word>millions?|mil\b|thousands?)\b)",
        re.IGNORECASE,
    ),
    # $2.5m / $25k / $25.5K
    re.compile(
        r"(?P<raw>(?<![A-Za-z])\$\s*(?P<num>\d{1,3}(?:,\d{3})+|\d+)(?:\.(?P<dec>\d+))?\s*(?P<suf>[kKmM])\b)"
    ),
    # USD 25k / US$2.5m
    re.compile(
        r"(?P<raw>(?:USD|US\$)\s*(?P<num>\d{1,3}(?:,\d{3})+|\d+)(?:\.(?P<dec>\d+))?\s*(?P<suf>[kKmM])\b)",
        re.IGNORECASE,
    ),
    # $25,000.00 / $25,000 / $25000 (4+ digits or grouped thousands)
    re.compile(
        r"(?P<raw>(?<![A-Za-z])\$\s*(?P<num>\d{1,3}(?:,\d{3})+(?:\.\d{1,2})?|\d{4,}(?:\.\d{1,2})?))"
    ),
    # USD 25,000 / USD 25000 / US$25000
    re.compile(
        r"(?P<raw>(?:USD|US\$)\s*(?P<num>\d{1,3}(?:,\d{3})+(?:\.\d{1,2})?|\d{3,}))",
        re.IGNORECASE,
    ),
    # 25,000 USD / 25000 dollars
    re.compile(
        r"(?P<raw>(?P<num>\d{1,3}(?:,\d{3})+|\d{4,})\s*(?:USD|dollars?|bucks)\b)",
        re.IGNORECASE,
    ),
    # 25k / 2.5m / 25K USD
    re.compile(
        r"(?P<raw>(?P<num>\d{1,3}(?:,\d{3})+|\d+)(?:\.(?P<dec>\d+))?\s*(?P<suf>[kKmM])(?:\s*(?:USD|dollars?))?\b)",
        re.IGNORECASE,
    ),
    # $25 / $99.00 (small dollar amounts — last)
    re.compile(r"(?P<raw>(?<![A-Za-z])\$\s*(?P<num>\d{1,3}(?:\.\d{1,2})?))\b"),
]


def _normalize(text: str) -> str:
    if not text:
        return ""
    trans = {
        "\u201c": '"',
        "\u201d": '"',
        "\u2018": "'",
        "\u2019": "'",
        "\uff04": "$",
        "\u00a0": " ",
        "\u202f": " ",
    }
    out = text
    for a, b in trans.items():
        out = out.replace(a, b)
    return out


def _to_int_usd(num: str, dec: str | None, suf: str | None, word: str | None) -> int | None:
    raw_num = num.replace(",", "")
    try:
        value = float(raw_num)
    except ValueError:
        return None
    if dec:
        try:
            value = float(f"{raw_num}.{dec}")
        except ValueError:
            return None
    token = (suf or word or "").lower()
    if token in {"k"}:
        value *= 1_000
    elif token in {"m"}:
        value *= 1_000_000
    elif token.startswith("mil"):
        value *= 1_000_000
    elif token.startswith("thousand"):
        value *= 1_000
    if value < 0:
        return None
    return int(round(value))


def _window(text: str, start: int, end: int, radius: int = 40) -> str:
    return text[max(0, start - radius) : min(len(text), end + radius)]


def parse_price(text: str) -> tuple[int | None, str | None]:
    """Return (price_usd, price_raw) for the best sale-price candidate."""
    text = _normalize(text)
    if not text:
        return None, None

    seen_spans: set[tuple[int, int]] = set()
    candidates: list[tuple[int, int, int, str]] = []  # score, usd, start, raw

    for cre in _PRICE_RES:
        for m in cre.finditer(text):
            span = m.span()
            if any(not (span[1] <= a or span[0] >= b) for a, b in seen_spans):
                continue
            gd = m.groupdict()
            usd = _to_int_usd(gd["num"], gd.get("dec"), gd.get("suf"), gd.get("word"))
            if usd is None:
                continue
            # Bare 4-digit years without $ / k / USD context.
            raw = gd["raw"].strip()
            if (
                usd >= 1900
                and usd <= 2100
                and "$" not in raw
                and not gd.get("suf")
                and not gd.get("word")
                and "usd" not in raw.lower()
                and "dollar" not in raw.lower()
            ):
                continue
            # Implausible domain-sale outliers (keep millions; drop billions+).
            if usd > 500_000_000:
                continue
            near = _window(text, span[0], span[1])
            score = 0
            if "$" in raw or "usd" in raw.lower() or "dollar" in raw.lower():
                score += 5
            if gd.get("suf") or gd.get("word"):
                score += 3
            sale_hit = bool(_SALE_NEAR.search(near))
            noise_hit = bool(_NOISE_NEAR.search(near))
            if noise_hit and not sale_hit:
                continue
            if sale_hit:
                score += 6
            if noise_hit:
                score -= 8
            # Prefer amounts that look like aftermarket prices.
            if 100 <= usd <= 10_000_000:
                score += 2
            if score < 2:
                continue
            seen_spans.add(span)
            candidates.append((score, usd, span[0], raw))

    if not candidates:
        return None, None
    candidates.sort(key=lambda c: (c[0], c[1]), reverse=True)
    best = candidates[0]
    return best[1], best[3]


def parse_domains(text: str) -> list[str]:
    """Return unique lowercase registrable names mentioned in text."""
    text = _normalize(text)
    if not text:
        return []
    found: list[str] = []
    seen: set[str] = set()
    for m in _DOMAIN_RE.finditer(text):
        host = m.group(1).lower().rstrip(".")
        if host.startswith("www."):
            host = host[4:]
        labels = host.split(".")
        registrable = ".".join(labels[-2:]) if len(labels) >= 2 else host
        if host in _SKIP_HOSTS or registrable in _SKIP_HOSTS:
            continue
        after = text[m.end() : m.end() + 1]
        if after == "/" and (host in _SKIP_HOSTS or registrable in _SKIP_HOSTS):
            continue
        if host in seen:
            continue
        # Require a real SLD (not ".com").
        labels = host.split(".")
        if len(labels) < 2 or not labels[0]:
            continue
        seen.add(host)
        found.append(host)
    return found


def premium_tier(price_usd: int | None) -> str | None:
    """Highest matching flag: 50k, then 30k, then 20k."""
    if price_usd is None:
        return None
    if price_usd >= 50_000:
        return "50k"
    if price_usd >= 30_000:
        return "30k"
    if price_usd >= 20_000:
        return "20k"
    return None


def parse_sale(text: str) -> dict[str, Any]:
    """Parse domains, USD price, and premium tier from post text."""
    price_usd, price_raw = parse_price(text)
    return {
        "domains": parse_domains(text),
        "price_usd": price_usd,
        "price_raw": price_raw,
        "premium_tier": premium_tier(price_usd),
    }


def _self_check() -> int:
    cases: list[tuple[str, dict[str, Any]]] = [
        (
            "Just sold Example.com for $25k",
            {"domains": ["example.com"], "price_usd": 25000, "price_raw": "$25k", "premium_tier": "20k"},
        ),
        (
            "Voice.com sold for $30 million",
            {"domains": ["voice.com"], "price_usd": 30000000, "price_raw": "$30 million", "premium_tier": "50k"},
        ),
        (
            "closed cars.io at USD 50,000 via escrow",
            {"domains": ["cars.io"], "price_usd": 50000, "price_raw": "USD 50,000", "premium_tier": "50k"},
        ),
        (
            "sold brand.ai for 25,000 USD",
            {"domains": ["brand.ai"], "price_usd": 25000, "price_raw": "25,000 USD", "premium_tier": "20k"},
        ),
        (
            "Just sold foo.co.uk for 25k",
            {"domains": ["foo.co.uk"], "price_usd": 25000, "price_raw": "25k", "premium_tier": "20k"},
        ),
        (
            "acquired Shop.app for $2.5m",
            {"domains": ["shop.app"], "price_usd": 2500000, "price_raw": "$2.5m", "premium_tier": "50k"},
        ),
        (
            "sold bar.net for $15,000",
            {"domains": ["bar.net"], "price_usd": 15000, "price_raw": "$15,000", "premium_tier": None},
        ),
        (
            "sold thing.com for $30k",
            {"domains": ["thing.com"], "price_usd": 30000, "price_raw": "$30k", "premium_tier": "30k"},
        ),
        (
            "Just sold two names, no price yet — wait for NameBio",
            {"domains": [], "price_usd": None, "price_raw": None, "premium_tier": None},
        ),
        (
            "Check https://x.com/DomainNameWire/status/123 and t.co/abcd — sold zenith.com for US$42,000",
            {"domains": ["zenith.com"], "price_usd": 42000, "price_raw": "US$42,000", "premium_tier": "30k"},
        ),
        (
            "Great year 2024 for sales, still hunting",
            {"domains": [], "price_usd": None, "price_raw": None, "premium_tier": None},
        ),
        (
            "Hit 25k followers today, not a sale",
            {"domains": [], "price_usd": None, "price_raw": None, "premium_tier": None},
        ),
        (
            "www.Premium.AI just sold for $75,000.00",
            {"domains": ["premium.ai"], "price_usd": 75000, "price_raw": "$75,000.00", "premium_tier": "50k"},
        ),
        (
            "Sold example.com and other.io as a package for $20,000",
            {
                "domains": ["example.com", "other.io"],
                "price_usd": 20000,
                "price_raw": "$20,000",
                "premium_tier": "20k",
            },
        ),
    ]

    failed = 0
    for text, expected in cases:
        got = parse_sale(text)
        for key, want in expected.items():
            have = got[key]
            if have != want:
                failed += 1
                print(f"FAIL {key!r} for {text!r}\n  want {want!r}\n  got  {have!r}", file=sys.stderr)
    if failed:
        print(f"parse_sale self-check: {failed} assertion(s) failed", file=sys.stderr)
        return 1
    print(f"parse_sale self-check: {len(cases)} cases passed")
    return 0


if __name__ == "__main__":
    sys.exit(_self_check())
