"""Find a Geograph photograph for buildings added since the last run.

Runs in GitHub Actions (Geograph is not reachable from every environment). For each
listing with coordinates and no entry in photos.json or photos-tried.json, it searches
Geograph's public search API for photos whose title names the kind of building, nearest
first, and keeps the nearest one within MAX_METRES. Every listing searched is recorded in
photos-tried.json, so it is only searched once.

Rows written to photos.json: [photo id, title, author, year, server, path, ok]; ok=1 means
it is shown on the site (credited to the photographer, CC BY-SA 2.0).
"""
import json, math, os, re, time, urllib.parse, urllib.request
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API = "https://api.geograph.org.uk/api-facetql.php"
MAX_METRES = 120
STREET = re.compile(r"\b\w+\s+(lane|road|street|way|close|drive|avenue|row|hill|walk|place|terrace|yard)\b", re.I)

WORDS = {
    "chapel": ["chapel", "methodist", "baptist", "wesleyan", "congregational", "primitive", "bethel", "ebenezer", "zion", "meeting house"],
    "church": ["church"],
    "school": ["school"],
    "mill": ["mill", "mills", "watermill", "windmill"],
    "windmill": ["windmill", "mill"],
    "oast": ["oast", "oasts", "oasthouse"],
    "pub": ["inn", "pub", "arms", "tavern", "head", "hotel"],
    "station": ["station", "signal box"],
    "toll": ["toll", "tollhouse"],
    "tower": ["tower"],
    "coach": ["coach house", "stables"],
    "police": ["police"],
    "fire": ["fire station"],
    "bank": ["bank"],
    "postoffice": ["post office"],
    "dairy": ["dairy", "creamery"],
    "forge": ["forge", "smithy", "blacksmith"],
    "granary": ["granary"],
    "malthouse": ["maltings", "malthouse", "malt house"],
    "bakery": ["bakery", "bakehouse"],
    "hall": ["hall", "institute", "reading room"],
    "works": ["works", "warehouse", "factory", "pumping station", "engine house"],
}


def load(name, default):
    p = os.path.join(ROOT, name)
    return json.load(open(p)) if os.path.exists(p) else default


def search(lat, lng, words):
    terms = "|".join(f'"{w}"' if " " in w else w for w in words)
    q = {
        "select": f"id,title,realname,takenday,hash,GEODIST(wgs84_lat,wgs84_long,{math.radians(lat)},{math.radians(lng)}) as d",
        "match": f"@title ({terms})",
        "order": "d asc",
        "limit": "15",
    }
    req = urllib.request.Request(API + "?" + urllib.parse.urlencode(q),
                                 headers={"User-Agent": "formerly.uk site builder (not-for-profit)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r).get("rows") or []


def path_for(pid, h):
    n = int(pid)
    if n < 1_000_000:
        s = f"{n:06d}"
        return f"photos/{s[0:2]}/{s[2:4]}/{s}_{h}"
    s = f"{n:08d}"
    return f"geophotos/{s[0:2]}/{s[2:4]}/{s[4:6]}/{pid}_{h}"


def main():
    photos = load("photos.json", {})
    tried = load("photos-tried.json", {})
    listings = load("docs/data/listings.json", {"listings": []})["listings"]
    found = 0
    for x in listings:
        lid = str(x["id"])
        if lid in photos or lid in tried or not x.get("lat") or not x.get("lng"):
            continue
        words = WORDS.get(x.get("type"), [])
        if not words:
            tried[lid] = date.today().isoformat()
            continue
        try:
            rows = search(x["lat"], x["lng"], words)
        except Exception as e:
            print("search failed", lid, e)
            continue  # try again next run
        tried[lid] = date.today().isoformat()
        pat = re.compile(r"\b(" + "|".join(re.escape(w) for w in words) + r")\b", re.I)
        for r in rows:
            if float(r.get("d") or 9e9) > MAX_METRES:
                break
            # Ignore titles where the word is only part of a street name ("Mill Lane", "Chapel Road")
            title = STREET.sub("", r.get("title") or "")
            if pat.search(title) and r.get("hash"):
                pid = str(r["id"])
                photos[lid] = [pid, r["title"], r.get("realname") or "", (r.get("takenday") or "")[:4],
                               str(int(pid) % 4), path_for(pid, r["hash"]), 1]
                found += 1
                print(f"{lid}: {r['title']} by {r.get('realname')}, {float(r['d']):.0f} m")
                break
        time.sleep(1)
    json.dump(photos, open(os.path.join(ROOT, "photos.json"), "w"), ensure_ascii=False, separators=(",", ":"))
    json.dump(tried, open(os.path.join(ROOT, "photos-tried.json"), "w"), indent=0, sort_keys=True)
    print(f"{found} new photos matched")


if __name__ == "__main__":
    main()
