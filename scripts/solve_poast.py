#!/usr/bin/env python3
import hashlib, re, sys, time, urllib.request, http.cookiejar

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
BASE = "https://nitter.poast.org"

def fetch(url, cj):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html"})
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    with opener.open(req, timeout=30) as r:
        return r.getcode(), r.read().decode("utf-8", "replace"), r.geturl()

def solve_pow(html):
    m = re.search(r"const a0_0x2a54=(\[[^\]]+\])", html)
    if not m:
        return None
    arr = eval(m.group(1), {"__builtins__": {}})
    n = re.search(r"_0x4457dc\(\+\+_0x2a548e\);\}\(a0_0x2a54,(0x[0-9a-fA-F]+|\d+)\)", html)
    if not n:
        # fallback documented 0x178
        rot = 0x178
    else:
        rot = int(n.group(1), 0)
    # IIFE does ++arg then while(--x) rotate, so rotate rot times
    for _ in range(rot):
        arr.append(arr.pop(0))
    # c is index 2 after typical obfuscation ("0x2")
    c = arr[2] if arr[2].startswith("0") or len(arr[2]) > 8 else None
    cookie_prefix = None
    digest_meth = None
    for x in arr:
        if x.startswith("res="):
            cookie_prefix = x
        if x == "array":
            digest_meth = x
    if c is None:
        for x in arr:
            if re.fullmatch(r"[0-9A-Fa-f]{20,}", x):
                c = x
    if not c or not cookie_prefix:
        return None
    n1 = int(c[0], 16)
    target0, target1 = 0xB0, 0x0B
    for i in range(0, 2_000_000):
        s = hashlib.sha1((c + str(i)).encode()).digest()
        if s[n1] == target0 and s[n1 + 1] == target1:
            return cookie_prefix + c + str(i)
    return None

def main():
    url = sys.argv[1] if len(sys.argv) > 1 else BASE + "/search?f=tweets&q=just+sold+domain"
    out = sys.argv[2] if len(sys.argv) > 2 else "/workspace/domain-diaries/data/raw/poast-solved.html"
    cj = http.cookiejar.CookieJar()
    code, html, final = fetch(url, cj)
    print("first", code, len(html), "verify" if "Verifying your browser" in html else "content", final)
    if "Verifying your browser" in html:
        cookie = solve_pow(html)
        print("pow_cookie", cookie)
        if not cookie:
            Path(out).write_text(html)
            print("FAIL no pow")
            return 2
        # set cookie
        name, val = cookie.split("=", 1)
        from http.cookiejar import Cookie
        ck = Cookie(0, name, val, None, False, "nitter.poast.org", True, False, "/", True, False, None, False, None, None, {})
        cj.set_cookie(ck)
        time.sleep(0.2)
        code, html, final = fetch(url, cj)
        print("second", code, len(html), "verify" if "Verifying your browser" in html else "content", final)
    Path(out).write_text(html)
    print("wrote", out, "status" in html, html.count("/status/"))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
