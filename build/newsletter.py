"""Create the weekly formerly. email as a DRAFT in Buttondown.

Nothing is sent: Tanya reviews the draft in Buttondown and presses Send.
Runs from .github/workflows/newsletter.yml with BUTTONDOWN_API_KEY as a secret.
Listings count as new if they were added to the site in the last 7 days.
"""
import datetime
import json
import os
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://formerly.uk"
MAX_ITEMS = 30


def md_escape(s):
    return str(s).replace("[", "\\[").replace("]", "\\]").replace("*", "\\*").replace("_", "\\_")


def item_md(x):
    lines = []
    if x.get("photo"):
        p = x["photo"]
        lines.append(f'[![{md_escape(p["title"])}]({SITE}/{p["src"]})]({x["url"]})')
    lines.append(f'**{md_escape(x.get("label") or "Former " + x["was"])}**  ')
    bits = [x["priceText"] or "Price on application"]
    if x.get("beds"):
        bits.append(f'{x["beds"]} bed')
    bits.append(x["county"])
    lines.append(f'[{md_escape(x["place"])}]({x["url"]}) · ' + " · ".join(md_escape(b) for b in bits) + "  ")
    if x.get("note"):
        lines.append(f'*{md_escape(x["note"])}.*  ')
    if x.get("badges"):
        lines.append(" · ".join(x["badges"]).upper() + "  ")
    if x.get("photo"):
        p = x["photo"]
        yr = f', {p["year"]}' if p.get("year") else ""
        lines.append(f'<small>Photo: [{md_escape(p["author"])}{yr}](https://www.geograph.org.uk/photo/{p["id"]}), '
                     f'[CC BY-SA 2.0](https://creativecommons.org/licenses/by-sa/2.0/)</small>')
    return "\n".join(lines)


def build(listings, today, test=False):
    since = (today - datetime.timedelta(days=7)).isoformat()
    new = [x for x in listings if (x.get("added") or "") > since]
    if not new:
        return None
    # Newest first when there are too many, then grouped by region for reading
    new.sort(key=lambda x: (x.get("added") or "", x.get("listed") or ""), reverse=True)
    shown = sorted(new[:MAX_ITEMS], key=lambda x: (x["region"], -(x.get("price") or 0)))
    n = len(new)
    date = today.strftime("%-d %B %Y")
    subject = f"{'[TEST] ' if test else ''}formerly. {date}: {n} new building{'s' if n != 1 else ''}"
    parts = [f"{n} building{'s' if n != 1 else ''} came up for sale this week that began life as something other than a home."
             f" Every link goes to the full listing on Zoopla.", ""]
    region = None
    for x in shown:
        if x["region"] != region:
            region = x["region"]
            parts += ["", f"## {region}", ""]
        parts += [item_md(x), ""]
    if n > len(shown):
        parts += ["", f"…and {n - len(shown)} more on [formerly.uk]({SITE})."]
    parts += ["", "---", "",
              f"Spotted one that doesn't belong? Use *Report* on the listing at [formerly.uk]({SITE}), or reply to this email.",
              "",
              "<small>formerly. is free and not-for-profit. We are not an estate agent; enquiries go to the agent on Zoopla. "
              "Photographs from Geograph, credited to their photographers.</small>"]
    return subject, "\n".join(parts)


def main():
    test = "--test" in sys.argv
    with open(os.path.join(ROOT, "docs", "data", "listings.json")) as fh:
        listings = json.load(fh)["listings"]
    out = build(listings, datetime.date.today(), test)
    if not out:
        print("No new listings this week; no draft created.")
        return 0
    subject, body = out
    if "--dry-run" in sys.argv:
        print(subject)
        print(body)
        return 0
    key = os.environ["BUTTONDOWN_API_KEY"]
    req = urllib.request.Request(
        "https://api.buttondown.com/v1/emails",
        data=json.dumps({"subject": subject, "body": body, "status": "draft"}).encode(),
        method="POST",
        headers={"Authorization": f"Token {key}", "Content-Type": "application/json", "User-Agent": "formerly-newsletter"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            res = json.load(r)
    except urllib.error.HTTPError as e:
        print("Buttondown refused the draft:", e.code, e.read().decode()[:500])
        return 1
    print(f"Draft created: {subject} (id {res.get('id')}, status {res.get('status')})")
    return 0


if __name__ == "__main__":
    import urllib.error  # noqa: F401
    sys.exit(main())
