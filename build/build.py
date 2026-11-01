"""Build listings.json for the formerly. site from a judged export.

Input:  export/*.json   judged entries (later files override earlier ones)
        removed.json    ids to leave out, with a reason (flats, sold, misjudged)
        overrides.json  corrections to individual entries (w, n, g fields)
        coords.json     [lat, lng] for each listing, from its listing page
        photos.json     best Geograph match per listing; last field 1 = approved for the site, 0 = awaiting review
        status.json     availability from the weekly rolling check: {id: {"state": "live"|"offer"|"gone",
                        "since": date the state began, "checked": date last checked}}.
                        "gone" is left out; "offer" shows an "Under offer" flag for up to OFFER_DAYS, then is left out
Output: docs/data/listings.json, docs/feed.xml and docs/feeds/<region>.xml

Each export row:
  id   Zoopla listing id
  p    price text, e.g. "£450,000"
  b    bedrooms ("" when not stated)
  a    address line as shown on the listing card
  l    listed date text, e.g. "24th Oct 26"
  au   1 when the listing is an auction
  t    building type key (chapel, school, mill ...)
  w    what the building was, in our words
  n    optional short note, in our words
  g    optional badges, "|" separated (Project, Auction ...)
  h    optional headline in our own words, e.g. "Grade II village post office, needing modernisation"
  sq   optional floor area in square feet (number)
  ac   optional plot size as text, e.g. "0.4 acres"
  gr   optional listed grade, e.g. "II", "II*"
  bt   optional date built as text, e.g. "1872", "c.1840"
  ag   optional agent name (kept for photo-permission requests; not shown on the site)
  ll   optional [lat, lng] when coords.json has no entry
"""
import json, re, sys, glob, datetime, os
from xml.sax.saxutils import escape
from areas import AREAS, COUNTY_WORDS, DISTRICT_OVERRIDES, NON_ENGLAND_AREAS, ENGLISH_DISTRICTS
from areas import GB_AREAS, GB_COUNTY_WORDS, WELSH_DISTRICTS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

MONTHS = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}

TYPE_LABELS = {
    "chapel": "Chapels", "church": "Churches", "school": "Schools", "mill": "Mills",
    "windmill": "Windmills", "station": "Railway", "pub": "Pubs and inns", "police": "Police stations",
    "fire": "Fire stations", "bank": "Banks", "postoffice": "Post offices", "tower": "Water towers",
    "oast": "Oast houses", "dairy": "Dairies", "forge": "Forges", "coach": "Coach houses",
    "toll": "Toll houses", "granary": "Granaries", "malthouse": "Malthouses", "bakery": "Bakeries",
    "hall": "Halls", "works": "Industrial and civic", "other": "Other",
}

# grandly.uk (sister site): its own building types and map labels
GRAND_TYPES = {
    "castle": "Castles", "tower": "Tower houses", "manor": "Manor houses", "hall": "Halls and courts",
    "country": "Country houses", "mansion": "Mansions", "estate": "Estates", "townhouse": "Town houses",
    "other": "Other",
}
GRAND_OS = {"castle": "Castle", "tower": "Tower", "manor": "Manor", "hall": "Hall", "country": "House",
            "mansion": "Mansion", "estate": "Park", "townhouse": "House", "other": "House"}
GRANDLY_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "grandly", "site")

PC_RE = re.compile(r"\b([A-Z]{1,2})(\d[\dA-Z]?)\s*$")


def parse_date(s):
    if re.match(r"^\d{4}-\d{2}-\d{2}$", s or ""):
        return s
    m = re.match(r"(\d{1,2})\w*\s+([A-Za-z]{3})\w*\s+(\d{2,4})", s or "")
    if not m:
        return None
    d, mon, yy = int(m.group(1)), MONTHS.get(m.group(2)[:3].title()), int(m.group(3))
    if not mon:
        return None
    if yy < 100:
        yy += 2000
    return datetime.date(yy, mon, d).isoformat()


def parse_price(s):
    m = re.search(r"£([\d,]+)", s or "")
    return int(m.group(1).replace(",", "")) if m else None


def locate(addr, gb=False):
    """Return (place, district, county, region) or None if outside England.
    With gb=True (grandly.uk), Scotland and Wales are accepted too."""
    a = (addr or "").strip().rstrip(".")
    m = PC_RE.search(a)
    district = area = None
    if m:
        area, district = m.group(1), m.group(1) + m.group(2)
        a = a[: m.start()].rstrip(" ,")
    welsh = district in WELSH_DISTRICTS
    outside = (area in NON_ENGLAND_AREAS and district not in ENGLISH_DISTRICTS) or welsh
    if outside and (not gb or area == "BT"):
        return None
    county = region = None
    if outside:
        for word, (c, r) in sorted(GB_COUNTY_WORDS.items(), key=lambda kv: -len(kv[0])):
            if re.search(r"\b" + re.escape(word) + r"\b", addr or "", re.I):
                county, region = c, r
                break
        if not county:
            county, region = WELSH_DISTRICTS.get(district) or GB_AREAS.get(area, ("Unknown", "Unknown"))
    # An explicit county in the address wins
    for word, (c, r) in ([] if county else sorted(COUNTY_WORDS.items(), key=lambda kv: -len(kv[0]))):
        if re.search(r"\b" + re.escape(word) + r"\b", addr or "", re.I):
            county, region = c, r
            break
    if not county and district and district in DISTRICT_OVERRIDES:
        county, region = DISTRICT_OVERRIDES[district]
    if not county and area in AREAS:
        county, region = AREAS[area]
    # Tidy the place: drop a trailing county word and duplicate parts
    parts = [p.strip() for p in a.split(",") if p.strip()]
    if county and parts and parts[-1].lower() in (county.lower(), "isle of wight"):
        parts = parts[:-1] or parts
    seen, clean = set(), []
    for p in parts:
        if p.lower() not in seen:
            seen.add(p.lower())
            clean.append(p)
    place = ", ".join(clean[-3:]) if clean else a
    return place, district or "", county or "Unknown", region or "Unknown"


SITE_URL = os.environ.get("FORMER_SITE_URL", "https://formerly.uk/")


PROPER_END = re.compile(r"\b(Church|Chapel|Inn|Tavern|Mill)$")
COMMON_START = re.compile(r"^(Methodist|Primitive|Wesleyan|Baptist|Cornish|Sunday|United)\b")


def label(was):
    """'Formerly a Methodist chapel, Grade II' style wording for a building's former use."""
    head, _, tail = was.partition(",")
    tail = ("," + tail) if tail else ""
    m = re.match(r"^(.*?)\s*\((part|half|rear part)\)$", head.strip())
    if m:
        noun, part = m.group(1), m.group(2)
        lead = {"part": "Part of", "half": "Half of", "rear part": "The rear part of"}[part]
        return f"{lead} a former {noun}{tail}"
    noun = head.strip()
    if noun.startswith("The "):
        return f"Formerly the {noun[4:]}{tail}"
    if re.search(r"(Inn|Tavern)$", noun):
        return f"Formerly the {noun}{tail}"
    if PROPER_END.search(noun):
        return f"Formerly {noun}{tail}"
    if noun[:1].isupper() and not COMMON_START.match(noun):
        return f"Formerly the {noun}{tail}"
    if re.search(r"(buildings|premises)$", noun):
        return f"Formerly {noun}{tail}"
    art = "an" if re.match(r"[aeio]", noun, re.I) and not noun.startswith("United") else "a"
    return f"Formerly {art} {noun}{tail}"


OS_BY_WAS = [
    (r"signal box", "SB"), (r"sunday school", "S Sch"), (r"convent", "Convent"), (r"priory", "Priory"),
    (r"library", "Liby"), (r"court ?house", "Court Ho"), (r"pumping", "Pumping Sta"), (r"telephone", "Tel Exch"),
    (r"engine house", "Engine Ho"), (r"watermill|corn mill", "Mill"), (r"smock|tower mill|windmill", "Windmill"),
    (r"\binn\b", "Inn"), (r"meeting house", "Meeting Ho"), (r"\bhall\b", "Hall"), (r"warehouse|factory|works|commercial", "Wks"),
]
OS_BY_TYPE = {"chapel": "Chap", "church": "Ch", "school": "Sch", "mill": "Mill", "windmill": "Windmill", "station": "Sta",
              "pub": "PH", "oast": "Oast", "tower": "Water Tower", "coach": "Coach Ho", "toll": "Toll Ho", "police": "Police Sta",
              "fire": "Fire Sta", "bank": "Bank", "postoffice": "PO", "dairy": "Dairy", "forge": "Smy", "granary": "Granary",
              "malthouse": "Malt Ho", "bakery": "Bakehouse", "hall": "Hall", "works": "Wks"}


def os_label(was, typ):
    """Old Ordnance Survey map shorthand for the building (mirrors osLabel() in docs/index.html)."""
    w = (was or "").lower()
    for pat, lab in OS_BY_WAS:
        if re.search(pat, w):
            return lab
    return OS_BY_TYPE.get(typ, "Bldg")


def rss(title, items):
    def item(x):
        bits = [x["priceText"] or "Price on application"]
        if x["beds"]:
            bits.append(f'{x["beds"]} bed')
        bits.append(x["county"])
        desc = f'{x["label"]}. ' + ", ".join(bits) + "." + (f' {x["note"]}.' if x["note"] else "")
        when = datetime.datetime.fromisoformat(x["added"]).strftime("%a, %d %b %Y 08:00:00 +0000")
        return (f"<item><title>{escape(x['label'] + ': ' + x['place'])}</title>"
                f"<link>{escape(x['url'])}</link><guid isPermaLink=\"false\">former-{x['id']}</guid>"
                f"<pubDate>{when}</pubDate><category>{escape(x['region'])}</category>"
                f"<description>{escape(desc)}</description></item>")
    return ('<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel>'
            f"<title>{escape(title)}</title><link>{escape(SITE_URL)}</link>"
            "<description>Buildings for sale in England that started life as something other than a home.</description>"
            "<language>en-gb</language>" + "".join(item(x) for x in items) + "</channel></rss>")


def write_feeds(out):
    newest = sorted(out, key=lambda x: (x["added"], x["listed"] or ""), reverse=True)
    docs = os.path.join(ROOT, "docs")
    with open(os.path.join(docs, "feed.xml"), "w") as fh:
        fh.write(rss("formerly. - all of England", newest[:60]))
    os.makedirs(os.path.join(docs, "feeds"), exist_ok=True)
    for region in sorted({x["region"] for x in out}):
        slug = re.sub(r"[^a-z]+", "-", region.lower()).strip("-")
        with open(os.path.join(docs, "feeds", slug + ".xml"), "w") as fh:
            fh.write(rss(f"formerly. - {region}", [x for x in newest if x["region"] == region][:40]))


def photo_for(m):
    """photos.json rows, ok (index 6) = 1 means used on the site:
    Geograph:          [photo id, title, author, year, server, path, ok]
    Wikimedia Commons: ["c<page id>", title, author, year, "", image url (640 px), ok, licence, licence url, page url]
    """
    if not m or not m[6]:
        return None
    pid, title, author, year = str(m[0]), m[1], m[2], m[3]
    if pid.startswith("c"):
        return {"id": pid, "title": title.strip(), "author": author, "year": year, "src": f"photos/{pid}.jpg",
                "thumb": m[5], "large": m[5], "source": "Wikimedia Commons",
                "licence": m[7] if len(m) > 7 else "", "licenceUrl": m[8] if len(m) > 8 else "",
                "page": m[9] if len(m) > 9 else ""}
    base = f"https://s{m[4]}.geograph.org.uk/{m[5]}"
    return {"id": pid, "title": title.strip(), "author": author, "year": year,
            "src": f"photos/{pid}.jpg", "thumb": base + "_213x160.jpg"}


def sister_card(pool, pinned=None, other="formerly"):
    """One house or building from the other site for this site's "From our sister site" card.
    `other` is the site it comes from. sister.json can pin one ({"grandly": "<id>", "formerly": "<id>"});
    otherwise the newest photographed one, the dearest of that day's."""
    pool = [o for o in pool if o.get("photo")]
    pick = next((o for o in pool if o["id"] == str(pinned or "")), None)
    if not pick and pool:
        pick = max(pool, key=lambda o: (o["added"], o["price"] or 0))
    if not pick:
        return []
    home, here = f"https://{other}.uk", ("grandly" if other == "formerly" else "formerly")
    card = {**pick, "extra": True, "sister": other, "url": f"{home}/b/{pick['id']}?s={here}",
            "photo": {**pick["photo"], "src": f"{home}/" + pick["photo"]["src"]}}
    return [card]


OFFER_DAYS = 31  # how long an under-offer building stays listed with its flag


def main():
    rows = {}
    for f in sorted(glob.glob(os.path.join(ROOT, "export", "*.json"))):
        with open(f) as fh:
            for r in json.load(fh):
                rows[str(r["id"])] = r  # later files win
    # "Not formerly., but…": buildings that fail the remit (always homes) but are too good to
    # leave out. Built the same way, published separately, never counted, posted or put in feeds.
    extras_path = os.path.join(ROOT, "extras.json")
    extra_ids = set()
    if os.path.exists(extras_path):
        with open(extras_path) as fh:
            for r in json.load(fh):
                rows[str(r["id"])] = r
                extra_ids.add(str(r["id"]))
    removed = {}
    rp = os.path.join(ROOT, "removed.json")
    if os.path.exists(rp):
        with open(rp) as fh:
            removed = json.load(fh)
    def load(name):
        fp = os.path.join(ROOT, name)
        return json.load(open(fp)) if os.path.exists(fp) else {}
    overrides, coords, photos = load("overrides.json"), load("coords.json"), load("photos.json")
    status = load("status.json")
    today = datetime.date.today()
    # keep the date each building was first published
    prev = {}
    lp = os.path.join(ROOT, "docs", "data", "listings.json")
    if os.path.exists(lp):
        with open(lp) as fh:
            old = json.load(fh)
            prev = {x["id"]: x.get("added") for x in old["listings"] + old.get("extras", [])}
    gp = os.path.join(GRANDLY_DIR, "data", "listings.json")
    if os.path.exists(gp):
        with open(gp) as fh:
            prev.update({x["id"]: x.get("added") for x in json.load(fh)["listings"]})
    out, dropped = [], []
    for r in rows.values():
        if str(r["id"]) in removed:
            continue
        st = status.get(str(r["id"])) or {}
        under_offer = False
        if st.get("state") == "gone":
            dropped.append((r["id"], r["a"], "no longer on Zoopla"))
            continue
        if st.get("state") == "offer":
            since = datetime.date.fromisoformat(st.get("since") or today.isoformat())
            if (today - since).days > OFFER_DAYS:
                dropped.append((r["id"], r["a"], f"under offer since {since}"))
                continue
            under_offer = True
        r = {**r, **overrides.get(str(r["id"]), {})}
        site = r.get("s") or "formerly"
        loc = locate(r["a"], gb=(site == "grandly"))
        if loc is None:
            dropped.append((r["id"], r["a"], "outside England" if site == "formerly" else "outside Great Britain"))
            continue
        place, district, county, region = loc
        badges = [b for b in (r.get("g") or "").split("|") if b]
        if r.get("au") and "Auction" not in badges:
            badges.append("Auction")
        was = r["w"]
        if re.search(r",\s*unconverted\b", was):
            # Condition belongs in the flag, not the history line
            was = re.sub(r",\s*unconverted\b", "", was).strip()
            badges = ["Unconverted" if b == "Project" else b for b in badges]
            if "Unconverted" not in badges:
                badges.insert(0, "Unconverted")
        if under_offer:
            badges.insert(0, "Under offer")
        if site == "grandly":
            t = r["t"] if r["t"] in GRAND_TYPES else "other"
        else:
            t = r["t"] if r["t"] in TYPE_LABELS else "other"
        out.append({
            "site": site,
            "name": (r.get("nm") or "").strip(),
            "id": str(r["id"]),
            "url": f"https://www.zoopla.co.uk/for-sale/details/{r['id']}/",
            "source": "Zoopla",
            "type": t,
            "was": was,
            "label": (was[:1].upper() + was[1:]) if site == "grandly" else label(was),
            "os": GRAND_OS.get(t, "House") if site == "grandly" else os_label(was, t),
            "note": r.get("n") or "",
            "headline": (r.get("h") or "").strip(),
            "sqft": int(r["sq"]) if str(r.get("sq") or "").isdigit() else None,
            "plot": (r.get("ac") or "").strip(),
            "grade": (r.get("gr") or "").strip(),
            "built": (r.get("bt") or "").strip(),
            "place": place,
            "postcode": district,
            "county": county,
            "region": region,
            "price": parse_price(r["p"]),
            "priceText": r["p"],
            "beds": int(r["b"]) if str(r.get("b") or "").isdigit() else None,
            "listed": parse_date(r["l"]),
            "badges": badges,
            "photo": photo_for(photos.get(str(r["id"]))),
            "lat": (coords.get(str(r["id"])) or r.get("ll") or [None, None])[0],
            "lng": (coords.get(str(r["id"])) or r.get("ll") or [None, None])[1],
            "added": prev.get(str(r["id"])) or datetime.date.today().isoformat(),
        })
    extras = sorted((o for o in out if o["id"] in extra_ids), key=lambda x: x["added"], reverse=True)
    for o in extras:
        o["extra"] = True
        o["label"] = "Not formerly., but…"
        if "castle" in o["was"].lower():
            o["os"] = "Castle"
    out = [o for o in out if o["id"] not in extra_ids]
    # Grandly buildings go to the sister site's data, never into formerly.'s
    grand = sorted((o for o in out if o["site"] == "grandly"), key=lambda x: x["listed"] or "", reverse=True)
    out = [o for o in out if o["site"] != "grandly"]
    os.makedirs(os.path.join(GRANDLY_DIR, "data"), exist_ok=True)
    with open(gp, "w") as fh:
        json.dump({"updated": datetime.date.today().isoformat(), "types": GRAND_TYPES, "count": len(grand),
                   "listings": grand, "extras": sister_card(out, load("sister.json").get("grandly"), other="formerly")},
                  fh, ensure_ascii=False, indent=1)
    out.sort(key=lambda x: x["listed"] or "", reverse=True)
    # With no "Not formerly., but…" building, formerly.'s extra card shows a Grandly house instead
    if not extras:
        extras = sister_card(grand, load("sister.json").get("formerly"), other="grandly")
    data = {
        "updated": datetime.date.today().isoformat(),
        "types": TYPE_LABELS,
        "count": len(out),
        "listings": out,
        "extras": extras,
    }
    os.makedirs(os.path.join(ROOT, "docs", "data"), exist_ok=True)
    with open(lp, "w") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
    write_feeds(out)
    unknown = [o for o in out if o["county"] == "Unknown"]
    print(f"{len(out)} listings written, {len(dropped)} dropped, {len(unknown)} with unknown county")
    for d in dropped:
        print("  dropped:", d)
    for u in unknown[:20]:
        print("  unknown:", u["id"], u["place"], u["postcode"])


if __name__ == "__main__":
    main()
