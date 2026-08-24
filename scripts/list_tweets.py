from pathlib import Path, html as H
import re, html
t=Path("/workspace/domain-diaries/data/raw/poast-ok.html").read_text(errors="replace")
blocks=re.findall(r"<div class=\"timeline-item[^\"]*\"[\s\S]*?(?=<div class=\"timeline-item|class=\"show-more\"|$)", t)
print("blocks", len(blocks))
for i,b in enumerate(blocks):
    m=re.search(r"href=\"/([A-Za-z0-9_]+)/status/(\d+)", b)
    c=re.search(r"tweet-content[^>]*>([\s\S]*?)</div>", b)
    txt=re.sub(r"<[^>]+>", " ", c.group(1) if c else "")
    txt=html.unescape(re.sub(r"\s+", " ", txt)).strip()
    print(i, m.group(1) if m else "?", m.group(2) if m else "?", txt[:160])
