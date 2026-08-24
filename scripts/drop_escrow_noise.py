import json
from pathlib import Path

drop=set()
keep=[]
for line in Path("/workspace/domain-diaries/data/sales.jsonl").read_text().splitlines():
    if not line.strip(): continue
    o=json.loads(line)
    if o.get("source")=="x-public" and (o.get("username") or "").lower()=="escrow_com":
        domains=o.get("domains") or []
        text=(o.get("text") or "").lower()
        only_escrow=set(d.lower() for d in domains)<= {"escrow.com"}
        saleish=("sold for" in text) or ("just sold" in text) or ("domain sold" in text)
        if only_escrow and not saleish:
            drop.add(o["id"])
            continue
    keep.append(o)
print("drop", len(drop), "keep", len(keep))
with Path("/workspace/domain-diaries/data/sales.jsonl").open("w") as fh:
    for o in keep:
        fh.write(json.dumps(o, ensure_ascii=False)+"\n")
# premium
pk=[]
for line in Path("/workspace/domain-diaries/data/premium.jsonl").read_text().splitlines():
    if not line.strip(): continue
    o=json.loads(line)
    if o.get("id") in drop: continue
    pk.append(o)
with Path("/workspace/domain-diaries/data/premium.jsonl").open("w") as fh:
    for o in pk:
        fh.write(json.dumps(o, ensure_ascii=False)+"\n")
print("premium_keep", len(pk))
