"""Download Geograph thumbnails for the photos the site uses into docs/photos/.

Run by GitHub Actions after the data changes (Geograph's servers are not reachable
from every environment). Images are stored unaltered; credits are shown on the site.
"""
import json, os, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "photos")
os.makedirs(OUT, exist_ok=True)
data = json.load(open(os.path.join(ROOT, "docs", "data", "listings.json")))
wanted = {x["photo"]["id"]: x["photo"]["thumb"] for x in data["listings"] + data.get("extras", []) if x.get("photo")}
got = 0
for pid, url in wanted.items():
    dest = os.path.join(OUT, f"{pid}.jpg")
    if os.path.exists(dest):
        continue
    for u in (url, url.replace("_213x160.", "_120x120.")):
        try:
            req = urllib.request.Request(u, headers={"User-Agent": "former. site builder (not-for-profit)"})
            with urllib.request.urlopen(req, timeout=30) as r:
                body = r.read()
            if body[:3] == b"\xff\xd8\xff":
                open(dest, "wb").write(body)
                got += 1
                break
        except Exception as e:
            print("failed", u, e)
# remove photos no longer used
for f in os.listdir(OUT):
    if f.endswith(".jpg") and f[:-4] not in wanted:
        os.remove(os.path.join(OUT, f))
print(f"{got} new photos, {len(wanted)} in use")
