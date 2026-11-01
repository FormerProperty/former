"""Suggest Geograph photographs for buildings.

suggest() is used by the sync job: each candidate in the review queue gets a suggested
photo, which Tanya keeps or drops on the review card. main() is a manual tool that matches
photos for buildings already on the site (it publishes them without review).


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
MAX_METRES = 120          # main(): published without review
SUGGEST_METRES = 200      # suggest(): reviewed on the card
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


# grandly.uk types (some keys match formerly.'s but mean something else, e.g. "hall", "tower")
GRAND_WORDS = {
    "castle": ["castle", "keep", "tower"], "tower": ["tower", "pele", "bastle", "castle"],
    "manor": ["manor", "hall", "court", "house"], "hall": ["hall", "court", "house"],
    "country": ["house", "hall", "court", "park", "place", "grange"], "mansion": ["mansion", "house", "hall"],
    "estate": ["house", "hall", "park", "estate", "lodge"], "townhouse": ["terrace", "crescent", "square", "house"],
    "other": ["house", "hall", "castle", "manor"],
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
        "limit": "40",
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


def _row(r):
    pid = str(r["id"])
    return [pid, r["title"], r.get("realname") or "", (r.get("takenday") or "")[:4],
            str(int(pid) % 4), path_for(pid, r["hash"]), 0]


def suggest(lat, lng, kind, site="formerly"):
    """Best Geograph photo for a building, as a photos.json row with ok=0, or None.

    Looser than the old automatic matching, because Tanya checks every suggestion:
    the nearest photo within SUGGEST_METRES whose title names the kind of building.
    (Matching on "former", "old" or "converted" was tried and dropped: it found the wrong
    buildings, such as an old post office for a chapel.)
    """
    if lat is None or lng is None:
        return None
    words = (GRAND_WORDS if site == "grandly" else WORDS).get(kind, [])
    if not words:
        return None
    rows = search(lat, lng, words)
    time.sleep(1)
    def has(words, r):
        return words and re.search(r"\b(" + "|".join(re.escape(w) for w in words) + r")\b",
                                   STREET.sub("", r.get("title") or ""), re.I)
    usable = [r for r in rows if r.get("hash")]
    for r in usable:
        if float(r.get("d") or 9e9) <= SUGGEST_METRES and has(words, r):
            return _row(r)
    return None


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


# ---- Wikimedia Commons (grandly.uk) ----
# Famous and listed houses are far better covered on Commons than on Geograph, but mostly by
# name, not by location. Rows use the Commons format described in build.py's photo_for().
COMMONS = "https://commons.wikimedia.org/w/api.php"
UA = "formerly.uk / grandly.uk site builder (not-for-profit; hello@formerly.uk)"


def _commons(params):
    q = urllib.parse.urlencode({**params, "format": "json", "formatversion": "2"})
    req = urllib.request.Request(f"{COMMONS}?{q}", headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def _strip(html):
    return re.sub(r"<[^>]+>", "", html or "").strip()


def commons_rows(titles):
    """Image details for Commons file titles, as photos.json rows (ok=0), JPEGs only."""
    if not titles:
        return []
    d = _commons({"action": "query", "titles": "|".join(titles[:40]), "prop": "imageinfo",
                  "iiprop": "url|extmetadata|mime", "iiurlwidth": "640"})
    rows = []
    for p in d.get("query", {}).get("pages", []):
        ii = (p.get("imageinfo") or [{}])[0]
        if ii.get("mime") != "image/jpeg" or not (ii.get("thumburl") or ii.get("url")):
            continue
        md = ii.get("extmetadata") or {}
        get = lambda k: _strip((md.get(k) or {}).get("value", ""))
        licence = get("LicenseShortName")
        if not licence:
            continue
        author = get("Artist")[:80] or "Unknown"
        m = re.search(r"(1[89]\d\d|20\d\d)", get("DateTimeOriginal") or get("DateTime"))
        year = m.group(1) if m else ""
        title = re.sub(r"^File:|\.[a-z]+$", "", p.get("title", ""), flags=re.I).replace("_", " ")
        rows.append([f"c{p.get('pageid')}", title[:150], author, year, "",
                     ii.get("thumburl") or ii["url"], 0, licence, get("LicenseUrl"), ii.get("descriptionurl", "")])
    return rows


def commons_suggest(name, lat=None, lng=None):
    """Best Commons photo for a named house: a file whose title contains the name, preferring
    ones taken near the house. None if nothing fits."""
    name = (name or "").strip()
    if len(name) < 4:
        return None
    hits = _commons({"action": "query", "list": "search", "srsearch": f'"{name}"', "srnamespace": "6",
                     "srlimit": "30"}).get("query", {}).get("search", [])
    words = [w for w in re.findall(r"[a-z]{3,}", name.lower()) if w not in ("the", "and")]
    titles = [h["title"] for h in hits if all(w in h["title"].lower() for w in words)]
    time.sleep(1)
    rows = commons_rows(titles)
    # Copies of Geograph photos are fine, but prefer Commons' own (often Wiki Loves Monuments)
    rows.sort(key=lambda r: ("geograph" in r[1].lower(), len(r[1])))
    return rows[0] if rows else None
