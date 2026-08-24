from pathlib import Path
import json, re, html, sys
sys.path.insert(0, "/workspace/domain-diaries/scripts")
from parse_sale import parse_sale
from datetime import datetime, timezone

SALE = re.compile(r"\b(just sold|sold for|domain sold|just closed|namebio|escrow\.com|acquired|purchased|sold via|closed at)\b|\bsold\b.{0,40}\$|\$.{0,40}\bsold\b", re.I|re.S)
ITEM = re.compile(r'<div class="timeline-item[^"]*"([^>]*)>([\s\S]*?)(?=<div class="timeline-item|class="show-more"|$)')
ST = re.compile(r"/([A-Za-z0-9_]+)/status/(\d+)")
CT = re.compile(r'<div class="tweet-content[^"]*"[^>]*>([\s\S]*?)</div>')
DT = re.compile(r'class="tweet-date"><a href="[^"]+" title="([^"]+)"')
FN = re.compile(r'class="fullname"[^>]*title="([^"]+)"')

def text_of(s):
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", html.unescape(s)).strip()

def pdate(t):
    if not t: return None
    t = html.unescape(t).replace("·"," ").replace(" UTC","").strip()
    t = re.sub(r"\s+", " ", t)
    try:
        return datetime.strptime(t, "%b %d, %Y %I:%M %p").replace(tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    except Exception:
        return None

seen=set()
sales_path=Path("/workspace/domain-diaries/data/sales.jsonl")
if sales_path.exists() and sales_path.stat().st_size:
    for line in sales_path.read_text().splitlines():
        if line.strip():
            try: seen.add(json.loads(line)["id"])
            except Exception: pass

now=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
new=[]
files=list(Path("/workspace/domain-diaries/data/raw/pages").glob("*.html"))
extra=Path("/workspace/domain-diaries/data/raw/poast-ok.html")
if extra.exists(): files.append(extra)
for p in files:
    raw=p.read_text(errors="replace")
    if "timeline-item" not in raw: continue
    q=p.stem.rsplit("-",1)[0]
    for attrs, body in ITEM.findall(raw):
        m=ST.search(body)
        if not m: continue
        user, tid = m.group(1), m.group(2)
        um=re.search(r'data-username="([^"]+)"', attrs)
        if um: user=um.group(1)
        cm=CT.search(body)
        if not cm: continue
        txt=text_of(cm.group(1))
        if not txt or tid in seen: continue
        parsed=parse_sale(txt)
        if not SALE.search(txt): continue
        if not parsed["domains"] and parsed["price_usd"] is None: continue
        seen.add(tid)
        url=f"https://x.com/{user}/status/{tid}"
        dm=DT.search(body); nm=FN.search(body)
        new.append({
            "id": tid, "url": url, "tweet_url": url, "text": txt,
            "created_at": pdate(dm.group(1) if dm else None),
            "author_id": None, "username": user,
            "name": html.unescape(nm.group(1)) if nm else None,
            "domains": parsed["domains"], "price_usd": parsed["price_usd"],
            "price_raw": parsed["price_raw"], "premium_tier": parsed["premium_tier"],
            "likes": 0, "reposts": 0, "quotes": 0, "replies": 0,
            "query": q, "source": "x-public", "collected_at": now,
        })

with sales_path.open("a") as fh:
    for r in new: fh.write(json.dumps(r, ensure_ascii=False)+"\n")
prem=[r for r in new if r.get("premium_tier")]
if prem:
    with Path("/workspace/domain-diaries/data/premium.jsonl").open("a") as fh:
        for r in prem: fh.write(json.dumps(r, ensure_ascii=False)+"\n")
summary={"new_sales":len(new),"new_premium":len(prem),"sales_total":len(seen),"files":len(files),"frontend":"nitter.poast.org"}
Path("/workspace/domain-diaries/data/xcancel-summary.json").write_text(json.dumps(summary, indent=2)+"\n")
print(json.dumps(summary))
for r in new[:6]:
    print(r["url"], r.get("price_raw"), r.get("domains"), r["text"][:120])
