"""Post one building to Bluesky, newest listings first.

Runs a few times a day from .github/workflows/bluesky.yml. Only buildings already
on the site are posted, so the review approval covers social posts too.
Order: listings added to the site in the last 7 days (newest first), then the
backlog (buildings with a photo first). Posted ids are kept in social/bluesky-posted.json.

Secrets: BLUESKY_HANDLE, BLUESKY_APP_PASSWORD (an app password, never the main password).
"""
import datetime
import json
import os
import sys
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDS = os.environ.get("BLUESKY_PDS", "https://bsky.social")
POSTED = os.path.join(ROOT, "social", "bluesky-posted.json")


def xrpc(method, token=None, body=None, raw=None, content_type="application/json"):
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    headers = {"Content-Type": content_type, "User-Agent": "formerly-social"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(f"{PDS}/xrpc/{method}", data=data, headers=headers, method="POST" if data else "GET")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise SystemExit(f"Bluesky {method} failed: {e.code} {e.read().decode()[:300]}")


def choose(listings, posted, today):
    """Newest additions first; then the backlog, photographed and most recently listed first."""
    live = [x for x in listings if x["id"] not in posted and "Under offer" not in (x.get("badges") or [])]
    since = (today - datetime.timedelta(days=7)).isoformat()
    fresh = [x for x in live if (x.get("added") or "") > since]
    fresh.sort(key=lambda x: (x.get("added") or "", x.get("listed") or ""), reverse=True)
    backlog = [x for x in live if (x.get("added") or "") <= since]
    backlog.sort(key=lambda x: (bool(x.get("photo")), x.get("listed") or ""), reverse=True)
    return (fresh + backlog)[:1]


SITE_LABEL = "formerly.uk"


def text_for(x, total):
    """Post text plus a link facet so 'formerly.uk' is clickable."""
    bits = [x["place"], x["priceText"] or "Price on application"]
    if x.get("beds"):
        bits.append(f'{x["beds"]} bed')
    head = [x.get("label") or "Former " + x["was"]] + ([x["headline"]] if x.get("headline") else []) + [" · ".join(bits)]
    if x.get("badges"):
        head.append(" · ".join(x["badges"]))
    link_line = f"View all {total} buildings on {SITE_LABEL}"
    credit = ""
    if x.get("photo"):
        p = x["photo"]
        credit = f'Photo: {p["author"]}{", " + str(p["year"]) if p.get("year") else ""} (CC BY-SA 2.0, Geograph)'
    lines = head + ["", link_line] + ([credit] if credit else [])
    text = "\n".join(lines)
    if len(text) > 295:  # keep within Bluesky's 300-character limit, dropping the flags line first
        lines = [l for l in head if l not in (" · ".join(x.get("badges") or []),)] + ["", link_line] + ([credit] if credit else [])
        text = "\n".join(lines)[:295]
    raw = text.encode("utf-8")
    start = raw.find(f"on {SITE_LABEL}".encode()) + 3
    facets = [{"index": {"byteStart": start, "byteEnd": start + len(SITE_LABEL.encode())},
               "features": [{"$type": "app.bsky.richtext.facet#link", "uri": "https://formerly.uk/?utm_source=bluesky&utm_medium=social&utm_campaign=listing-post"}]}]
    return text, facets


POST_HOURS = (8, 12, 18)  # UK time
SLOTS = os.path.join(ROOT, "social", "bluesky-slot.json")


def uk_now():
    """Current UK time, without relying on the system time-zone database."""
    now = datetime.datetime.now(datetime.timezone.utc)
    try:
        from zoneinfo import ZoneInfo
        return now.astimezone(ZoneInfo("Europe/London"))
    except Exception:
        def last_sunday(year, month):
            d = datetime.date(year, month, 31)
            return d - datetime.timedelta(days=(d.weekday() + 1) % 7)
        y = now.year
        start = datetime.datetime.combine(last_sunday(y, 3), datetime.time(1), datetime.timezone.utc)
        end = datetime.datetime.combine(last_sunday(y, 10), datetime.time(1), datetime.timezone.utc)
        return now + (datetime.timedelta(hours=1) if start <= now < end else datetime.timedelta())


def due_slot():
    """The latest posting slot (e.g. '2026-10-26 18') if under 3 hours old and not yet used.
    GitHub often starts scheduled runs late, so a slot is honoured for a while, not only in its own hour."""
    now = uk_now()
    slots = [now.replace(hour=h, minute=0, second=0, microsecond=0) for h in POST_HOURS]
    slots += [x - datetime.timedelta(days=1) for x in slots]
    early = datetime.timedelta(minutes=25)  # a run shortly before the hour counts for that slot
    latest = max(x for x in slots if x - early <= now)
    if now - latest > datetime.timedelta(hours=3):
        return None
    key = latest.strftime("%Y-%m-%d %H")
    try:
        with open(SLOTS) as fh:
            if json.load(fh).get("last") == key:
                return None
    except FileNotFoundError:
        pass
    return key


def main():
    dry = "--dry-run" in sys.argv
    slot = due_slot()
    if "--now" not in sys.argv and not slot:
        print(f"No posting slot due at {uk_now():%H:%M} UK time; posts go out at 8am, 12pm and 6pm.")
        return 0
    with open(os.path.join(ROOT, "docs", "data", "listings.json")) as fh:
        data = json.load(fh)
    try:
        with open(POSTED) as fh:
            posted = set(json.load(fh))
    except FileNotFoundError:
        posted = set()
    pick = choose(data["listings"], posted, datetime.date.today())
    if not pick:
        print("Nothing left to post.")
        return 0
    x = pick[0]
    text, facets = text_for(x, len(data["listings"]))
    img_path = os.path.join(ROOT, "docs", x["photo"]["src"]) if x.get("photo") else \
        os.path.join(ROOT, "docs", "email", "labels", __import__("re").sub(r"[^a-z0-9]+", "-", (x.get("os") or "bldg").lower()) + ".png")
    print(text, "\n->", x["url"], "\nimage:", os.path.relpath(img_path, ROOT))
    if dry:
        return 0

    s = xrpc("com.atproto.server.createSession", body={
        "identifier": os.environ["BLUESKY_HANDLE"], "password": os.environ["BLUESKY_APP_PASSWORD"]})
    token, did = s["accessJwt"], s["did"]
    embed = {"$type": "app.bsky.embed.external", "external": {
        "uri": x["url"], "title": x.get("headline") or f'{x.get("label") or "Former " + x["was"]}: {x["place"]}',
        "description": "Full listing on Zoopla. Found by formerly.uk, buildings that began life as something else."}}
    if os.path.exists(img_path):
        with open(img_path, "rb") as fh:
            blob = xrpc("com.atproto.repo.uploadBlob", token, raw=fh.read(),
                        content_type="image/png" if img_path.endswith(".png") else "image/jpeg")["blob"]
        embed["external"]["thumb"] = blob
    record = {"$type": "app.bsky.feed.post", "text": text, "facets": facets, "langs": ["en-GB"], "embed": embed,
              "createdAt": datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")}
    res = xrpc("com.atproto.repo.createRecord", token, body={"repo": did, "collection": "app.bsky.feed.post", "record": record})
    print("posted", res.get("uri"))

    posted.add(x["id"])
    os.makedirs(os.path.dirname(POSTED), exist_ok=True)
    with open(POSTED, "w") as fh:
        json.dump(sorted(posted), fh, indent=0)
    with open(SLOTS, "w") as fh:
        json.dump({"last": slot or uk_now().strftime("%Y-%m-%d %H")}, fh)
    return 0


if __name__ == "__main__":
    sys.exit(main())
