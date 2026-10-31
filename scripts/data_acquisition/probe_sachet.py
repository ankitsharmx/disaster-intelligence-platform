import requests
import re
import urllib3

urllib3.disable_warnings()

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

chunks = [
  "static/chunks/2-u6r8noh-6wk.js",
  "static/chunks/268grksaps04t.js",
  "static/chunks/0zuu3a5k01-at.js",
  "static/chunks/0rzytlihws3fc.js",
  "static/chunks/0nruqwzrbr-3c.js",
  "static/chunks/0h7itapft6hyq.js",
]

for ch in chunks:
    r = requests.get(f"https://sachet.ndma.gov.in/_next/{ch}", headers=headers, timeout=15, verify=False)
    matches = set(re.findall(r'https?://[^\s"\'`<>]+', r.text) + re.findall(r'/[a-zA-Z0-9_\-\./]*(?:rss|feed|cap|xml|api)[a-zA-Z0-9_\-\./]*', r.text, re.IGNORECASE))
    print("Chunk:", ch, "Length:", len(r.text))
    for m in matches:
        print("  Match:", m)
    # search for rss or punjab
    for line in r.text.split(";"):
        if any(k in line.lower() for k in ["rss", "punjab", "subscribe", ".xml"]):
            print("  Snippet:", line[:120].strip())
