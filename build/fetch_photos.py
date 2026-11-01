"""Download the photos each site uses: Geograph thumbnails and Wikimedia Commons images.

formerly.uk's go to docs/photos/, grandly.uk's to grandly/site/photos/. Run by GitHub Actions
after the data changes (these servers are not reachable from every environment). Images are
stored unaltered; credits and licences are shown on the sites.
"""
import json, os, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = {"User-Agent": "formerly.uk / grandly.uk site builder (not-for-profit; hello@formerly.uk)"}


def sync(data_path, out_dir):
    if not os.path.exists(data_path):
        return
    os.makedirs(out_dir, exist_ok=True)
    data = json.load(open(data_path))
    wanted = {x["photo"]["id"]: x["photo"]["thumb"] for x in data["listings"] + data.get("extras", []) if x.get("photo")}
    got = 0
    for pid, url in wanted.items():
        dest = os.path.join(out_dir, f"{pid}.jpg")
        if os.path.exists(dest):
            continue
        for u in (url, url.replace("_213x160.", "_120x120.")):
            try:
                with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30) as r:
                    body = r.read()
                if body[:3] == b"\xff\xd8\xff":
                    open(dest, "wb").write(body)
                    got += 1
                    break
            except Exception as e:
                print("failed", u, e)
    for f in os.listdir(out_dir):  # remove photos no longer used
        if f.endswith(".jpg") and f[:-4] not in wanted:
            os.remove(os.path.join(out_dir, f))
    print(f"{os.path.relpath(out_dir, ROOT)}: {got} new photos, {len(wanted)} in use")


sync(os.path.join(ROOT, "docs", "data", "listings.json"), os.path.join(ROOT, "docs", "photos"))
sync(os.path.join(ROOT, "grandly", "site", "data", "listings.json"), os.path.join(ROOT, "grandly", "site", "photos"))
