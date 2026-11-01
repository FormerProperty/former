"""Post a building to the formerly. (or grandly.) Facebook Page.

Called by bluesky.py straight after each Bluesky post, so both accounts show the same
building at 8am, 12pm and 6pm. The post is our own image (the Geograph photo or the
label tile) with a caption; the link goes to that building on formerly.uk.

Secrets: FB_PAGE_ID and FB_PAGE_TOKEN (a Page access token that does not expire).
Posted ids are kept in social/facebook-posted.json (Grandly: GRANDLY_FB_* secrets, social/grandly/).
"""
import json
import os
import urllib.error
import urllib.parse
import urllib.request
import uuid

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GRAPH = "https://graph.facebook.com/v26.0"
DEFAULT = {"domain": "formerly.uk", "records": "social", "env": "",
           "fb_line": "with all {n} buildings that began life as something else"}


def caption_for(x, total, site=DEFAULT):
    from bluesky import credit_for, where
    bits = [where(x), x.get("priceText") or "Price on application"]
    if x.get("beds"):
        bits.append(f'{x["beds"]} bed')
    lines = [x.get("label") or "Former " + x["was"]]
    if x.get("headline"):
        lines.append(x["headline"])
    lines.append(" · ".join(bits))
    if x.get("badges"):
        lines.append(" · ".join(x["badges"]))
    if x.get("extra") and x.get("note"):
        lines += ["", x["note"] + "."]
    # Short link; Facebook adds its own fbclid to it, which tells the site the visit came from here
    lines += ["", f'See it on {site["domain"]}, ' + site["fb_line"].format(n=total) + ":",
              f'https://{site["domain"]}/b/{x["id"]}']
    if x.get("photo"):
        lines += ["", credit_for(x["photo"])]
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


def page_token(page, token, domain):
    """Posting needs the Page's own token. If the secret holds Tanya's user token instead (one
    user token can manage both Pages), swap it for the Page token via me/accounts. The Page is
    found by its id, or failing that by its name (the Pages are called formerly.uk and grandly.uk)."""
    try:
        q = urllib.parse.urlencode({"fields": "id,name,access_token", "access_token": token})
        with urllib.request.urlopen(f"{GRAPH}/me/accounts?{q}", timeout=60) as r:
            pages = json.load(r).get("data", [])
    except Exception:
        return page, token  # a Page token cannot list accounts: use it as it is
    hit = next((p for p in pages if p.get("id") == page), None) or \
          next((p for p in pages if (p.get("name") or "").lower() == domain), None)
    if hit and hit.get("access_token"):
        return hit["id"], hit["access_token"]
    return page, token


def post(x, total, img_path, dry=False, site=DEFAULT):
    """Publish one photo post to the Page. Returns the post id, or None on a dry run."""
    caption = caption_for(x, total, site)
    print("Facebook:\n" + caption)
    if dry:
        return None
    page, token = page_token(os.environ[site["env"] + "FB_PAGE_ID"], os.environ[site["env"] + "FB_PAGE_TOKEN"], site["domain"])
    body, ctype = _multipart({"caption": caption, "published": "true", "access_token": token}, "source", img_path)
    req = urllib.request.Request(f"{GRAPH}/{page}/photos", data=body, method="POST",
                                 headers={"Content-Type": ctype, "User-Agent": "formerly-social"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            res = json.load(r)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Facebook post failed: {e.code} {e.read().decode()[:300]}")
    POSTED = os.path.join(ROOT, site["records"], "facebook-posted.json")
    posted = []
    if os.path.exists(POSTED):
        with open(POSTED) as fh:
            posted = json.load(fh)
    posted.append({"id": x["id"], "post": res.get("post_id") or res.get("id")})
    with open(POSTED, "w") as fh:
        json.dump(posted[-1000:], fh, indent=0)
    print("posted to Facebook", res.get("post_id") or res.get("id"))
    return res.get("post_id") or res.get("id")


def configured(site=DEFAULT):
    return bool(os.environ.get(site["env"] + "FB_PAGE_ID") and os.environ.get(site["env"] + "FB_PAGE_TOKEN"))
