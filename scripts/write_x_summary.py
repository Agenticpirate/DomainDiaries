import json
from datetime import datetime, timezone
from pathlib import Path
from collections import Counter

sales=[]
prem=[]
for line in Path("/workspace/domain-diaries/data/sales.jsonl").read_text().splitlines():
    if not line.strip(): continue
    o=json.loads(line)
    if o.get("source")=="x-public":
        sales.append(o)
for line in Path("/workspace/domain-diaries/data/premium.jsonl").read_text().splitlines():
    if not line.strip(): continue
    o=json.loads(line)
    if o.get("source")=="x-public":
        prem.append(o)

pages=list(Path("/workspace/domain-diaries/data/raw/pages").glob("*.html"))
ok=sum(1 for p in pages if "timeline-item" in p.read_text(errors="replace"))
users=Counter(r.get("username") for r in sales)
q=Counter(r.get("query") for r in sales)
tiers=Counter(r.get("premium_tier") for r in sales)
with_url=sum(1 for r in sales if r.get("url","").startswith("https://x.com/") and "/status/" in r["url"])
with_id=sum(1 for r in sales if r.get("id") and str(r["id"]).isdigit())

now=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
summary={
    "source": "x-public",
    "collected_at": now,
    "frontend_worked": "nitter.poast.org",
    "frontends_tried": {
        "xcancel.com": "blocked — CAP/WASM antibot + image captcha; RSS requires reader whitelist",
        "nitter.poast.org": "worked after public JS proof-of-work cookie; later 429 on some cursors",
        "nitter.net": "TLS unexpected EOF",
        "nitter.tiekoetter.com": "bot check page",
        "nitter.catsarch.com": "HTTP 403",
        "lightbrd.com": "Cloudflare challenge",
        "nitter.space": "Cloudflare challenge",
        "nitter.privacyredirect.com": "TLS unexpected EOF",
        "nitter.kareem.one": "Cloudflare challenge",
        "nitter.cz": "bot check page",
    },
    "html_pages_saved": len(pages),
    "html_pages_with_tweets": ok,
    "x_public_sales": len(sales),
    "x_public_premium": len(prem),
    "all_have_status_id": with_id==len(sales),
    "all_have_x_com_url": with_url==len(sales),
    "unique_usernames": len(users),
    "premium_tiers": {k or "null": v for k,v in tiers.items()},
    "with_parsed_domain": sum(1 for r in sales if r.get("domains")),
    "with_parsed_price": sum(1 for r in sales if r.get("price_usd") is not None),
    "top_usernames": users.most_common(12),
    "queries": q.most_common(),
    "blockers": [
        "xcancel.com captcha/antibot (HTML samples in data/raw/)",
        "xcancel RSS: reader not whitelisted",
        "nitter.poast.org HTTP 429 after ~15-20 search pages on some queries",
        "Several other Nitter hosts: Cloudflare/TLS/bot-check",
        "Official X API / x.com not used (as requested)",
    ],
    "note": "Every x-public record has url=https://x.com/{user}/status/{id}. Posts without a status id were skipped. Not invented.",
}
Path("/workspace/domain-diaries/data/xcancel-summary.json").write_text(json.dumps(summary, indent=2)+"\n")

# merge into existing summary.json without wiping dnjournal
sp=Path("/workspace/domain-diaries/data/summary.json")
base=json.loads(sp.read_text()) if sp.exists() else {}
base["x_public"] = {
    "collected_at": now,
    "frontend": "nitter.poast.org",
    "sales": len(sales),
    "premium": len(prem),
    "pages": len(pages),
}
sp.write_text(json.dumps(base, indent=2)+"\n")
print(json.dumps(summary, indent=2))
print("EXAMPLES")
# prefer domain+price
good=[r for r in sales if r.get("domains") and r.get("price_usd") and r.get("price_usd",0)>=1000]
# stable first 5 distinctive
seen=set()
n=0
for r in good:
    key=(tuple(r.get("domains") or []), r.get("price_usd"))
    if key in seen: continue
    seen.add(key)
    print(r["url"])
    print(" ", r["username"], r.get("price_raw"), r.get("domains"), r.get("created_at"))
    print(" ", r["text"][:160].replace("\n"," "))
    n+=1
    if n>=5: break
