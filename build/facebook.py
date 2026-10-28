"""Post a building to the formerly. Facebook Page.

Called by bluesky.py straight after each Bluesky post, so both accounts show the same
building at 8am, 12pm and 6pm. The post is our own image (the Geograph photo or the
label tile) with a caption; the link goes to that building on formerly.uk.

Secrets: FB_PAGE_ID and FB_PAGE_TOKEN (a Page access token that does not expire).
Posted ids are kept in social/facebook-posted.json.
"""
import json
import os
import urllib.error
import urllib.request
import uuid

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GRAPH = "https://graph.facebook.com/v26.0"
POSTED = os.path.join(ROOT, "social", "facebook-posted.json")


def caption_for(x, total):
    bits = [x["place"], x.get("priceText") or "Price on application"]
    if x.get("beds"):
        bits.append(f'{x["beds"]} bed')
    lines = [x.get("label") or "Former " + x["was"]]
    if x.get("headline"):
        lines.append(x["headline"])
    lines.append(" · ".join(bits))
    if x.get("badges"):
        lines.append(" · ".join(x["badges"]))
    # Short link; Facebook adds its own fbclid to it, which tells formerly.uk the visit came from here
    lines += ["", f"See it on formerly.uk, with all {total} buildings that began life as something else:",
              f"https://formerly.uk/b/{x['id']}"]
    if x.get("photo"):
        p = x["photo"]
        lines += ["", f'Photo: {p["author"]}{", " + str(p["year"]) if p.get("year") else ""} (CC BY-SA 2.0, Geograph)']
    return "\n".join(lines)


def _multipart(fields, file_field, path):
    boundary = uuid.uuid4().hex
    out = []
    for k, v in fields.items():
        out.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    ctype = "image/png" if path.endswith(".png") else "image/jpeg"
    with open(path, "rb") as fh:
        data = fh.read()
    out.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{file_field}"; filename="{os.path.basename(path)}"\r\n'
               f"Content-Type: {ctype}\r\n\r\n".encode() + data + b"\r\n")
    out.append(f"--{boundary}--\r\n".encode())
    return b"".join(out), f"multipart/form-data; boundary={boundary}"


def post(x, total, img_path, dry=False):
    """Publish one photo post to the Page. Returns the post id, or None on a dry run."""
    caption = caption_for(x, total)
    print("Facebook:\n" + caption)
    if dry:
        return None
    page, token = os.environ["FB_PAGE_ID"], os.environ["FB_PAGE_TOKEN"]
    body, ctype = _multipart({"caption": caption, "published": "true", "access_token": token}, "source", img_path)
    req = urllib.request.Request(f"{GRAPH}/{page}/photos", data=body, method="POST",
                                 headers={"Content-Type": ctype, "User-Agent": "formerly-social"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            res = json.load(r)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Facebook post failed: {e.code} {e.read().decode()[:300]}")
    posted = []
    if os.path.exists(POSTED):
        with open(POSTED) as fh:
            posted = json.load(fh)
    posted.append({"id": x["id"], "post": res.get("post_id") or res.get("id")})
    with open(POSTED, "w") as fh:
        json.dump(posted[-1000:], fh, indent=0)
    print("posted to Facebook", res.get("post_id") or res.get("id"))
    return res.get("post_id") or res.get("id")


def configured():
    return bool(os.environ.get("FB_PAGE_ID") and os.environ.get("FB_PAGE_TOKEN"))
