"""Build listings.json for the former. site from a judged export.

Input:  export/*.json   judged entries (later files override earlier ones)
        removed.json    ids to leave out, with a reason (flats, sold, misjudged)
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
"""
import json, re, sys, glob, datetime, os
from xml.sax.saxutils import escape
from areas import AREAS, COUNTY_WORDS, DISTRICT_OVERRIDES, NON_ENGLAND_AREAS, ENGLISH_DISTRICTS

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

PC_RE = re.compile(r"\b([A-Z]{1,2})(\d[\dA-Z]?)\s*$")


def parse_date(s):
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


def locate(addr):
    """Return (place, district, county, region) or None if outside England."""
    a = (addr or "").strip().rstrip(".")
    m = PC_RE.search(a)
    district = area = None
    if m:
        area, district = m.group(1), m.group(1) + m.group(2)
        a = a[: m.start()].rstrip(" ,")
    if area in NON_ENGLAND_AREAS and district not in ENGLISH_DISTRICTS:
        return None
    county = region = None
    # An explicit county in the address wins
    for word, (c, r) in sorted(COUNTY_WORDS.items(), key=lambda kv: -len(kv[0])):
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


SITE_URL = os.environ.get("FORMER_SITE_URL", "https://example.github.io/former/")


def rss(title, items):
    def item(x):
        bits = [x["priceText"] or "Price on application"]
        if x["beds"]:
            bits.append(f'{x["beds"]} bed')
        bits.append(x["county"])
        desc = f'Former {x["was"]}. ' + ", ".join(bits) + "." + (f' {x["note"]}.' if x["note"] else "")
        when = datetime.datetime.fromisoformat(x["added"]).strftime("%a, %d %b %Y 08:00:00 +0000")
        return (f"<item><title>{escape('former. ' + x['was'] + ', ' + x['place'])}</title>"
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
        fh.write(rss("former. - all of England", newest[:60]))
    os.makedirs(os.path.join(docs, "feeds"), exist_ok=True)
    for region in sorted({x["region"] for x in out}):
        slug = re.sub(r"[^a-z]+", "-", region.lower()).strip("-")
        with open(os.path.join(docs, "feeds", slug + ".xml"), "w") as fh:
            fh.write(rss(f"former. - {region}", [x for x in newest if x["region"] == region][:40]))


def main():
    rows = {}
    for f in sorted(glob.glob(os.path.join(ROOT, "export", "*.json"))):
        with open(f) as fh:
            for r in json.load(fh):
                rows[str(r["id"])] = r  # later files win
    removed = {}
    rp = os.path.join(ROOT, "removed.json")
    if os.path.exists(rp):
        with open(rp) as fh:
            removed = json.load(fh)
    # keep the date each building was first published
    prev = {}
    lp = os.path.join(ROOT, "docs", "data", "listings.json")
    if os.path.exists(lp):
        with open(lp) as fh:
            prev = {x["id"]: x.get("added") for x in json.load(fh)["listings"]}
    out, dropped = [], []
    for r in rows.values():
        if str(r["id"]) in removed:
            continue
        loc = locate(r["a"])
        if loc is None:
            dropped.append((r["id"], r["a"], "outside England"))
            continue
        place, district, county, region = loc
        badges = [b for b in (r.get("g") or "").split("|") if b]
        if r.get("au") and "Auction" not in badges:
            badges.append("Auction")
        t = r["t"] if r["t"] in TYPE_LABELS else "other"
        out.append({
            "id": str(r["id"]),
            "url": f"https://www.zoopla.co.uk/for-sale/details/{r['id']}/",
            "source": "Zoopla",
            "type": t,
            "was": r["w"],
            "note": r.get("n") or "",
            "place": place,
            "postcode": district,
            "county": county,
            "region": region,
            "price": parse_price(r["p"]),
            "priceText": r["p"],
            "beds": int(r["b"]) if str(r.get("b") or "").isdigit() else None,
            "listed": parse_date(r["l"]),
            "badges": badges,
            "added": prev.get(str(r["id"])) or datetime.date.today().isoformat(),
        })
    out.sort(key=lambda x: x["listed"] or "", reverse=True)
    data = {
        "updated": datetime.date.today().isoformat(),
        "types": TYPE_LABELS,
        "count": len(out),
        "listings": out,
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
