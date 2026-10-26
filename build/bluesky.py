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


def main():
    dry = "--dry-run" in sys.argv
    from zoneinfo import ZoneInfo
    hour = datetime.datetime.now(ZoneInfo("Europe/London")).hour
    if "--now" not in sys.argv and hour not in POST_HOURS:
        print(f"It is {hour}:00 in London; posts go out at 8am, 12pm and 6pm. Skipping.")
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
