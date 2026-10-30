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


from html import escape as h

INK, MUTED, RULE, PAPER, STONE, GREEN, OXBLOOD = "#1B1D1C", "#5E625F", "#D3D1CA", "#F3F2EE", "#E2DFD6", "#1E4D3B", "#7B2D26"
SERIF = "Georgia,'Times New Roman',serif"
SANS = "'Helvetica Neue',Helvetica,Arial,sans-serif"

KINDS = [  # how the intro counts things up
    ("chapel", ("Chap", "Meeting Ho"), "chapel", "chapels"), ("church", ("Ch", "Priory", "Convent"), "church", "churches"),
    ("school", ("Sch", "S Sch"), "school", "schools"), ("mill", ("Mill", "Windmill"), "mill", "mills"),
    ("pub", ("PH", "Inn"), "pub or inn", "pubs and inns"), ("oast", ("Oast",), "oast house", "oast houses"),
    ("coach", ("Coach Ho",), "coach house", "coach houses"),
]
NUM = "no one two three four five six seven eight nine ten eleven twelve".split()


def words(n):
    return NUM[n] if n < len(NUM) else str(n)


def slug(s):
    import re
    return re.sub(r"[^a-z0-9]+", "-", s.lower())


def summary(items):
    parts, used = [], 0
    for _, labels, one, many in KINDS:
        c = sum(1 for x in items if x.get("os") in labels)
        if c:
            parts.append(f"{words(c)} {one if c == 1 else many}")
            used += c
    rest = len(items) - used
    if rest:
        parts.append(f"{words(rest)} {'other' if parts else ''} building{'s' if rest != 1 else ''}".replace("  ", " "))
    if len(parts) > 1:
        return ", ".join(parts[:-1]) + " and " + parts[-1]
    return parts[0] if parts else ""


def picture(x, w=270, hgt=203):
    if x.get("photo"):
        src, alt = f'{SITE}/{x["photo"]["src"]}', x["photo"]["title"]
    else:
        src, alt = f'{SITE}/email/labels/{slug(x.get("os") or "Bldg")}.png', x.get("label", "")
    return (f'<a href="{h(x["url"])}" style="text-decoration:none"><img src="{h(src)}" width="{w}" height="{hgt}" alt="{h(alt)}" '
            f'style="display:block;width:100%;max-width:{w}px;height:auto;border:0;background:{STONE}"></a>')


def details(x, place_size=19):
    bits = ([x["priceText"] or "Price on application"] + ([f'{x["beds"]} bed'] if x.get("beds") else [])
            + ([f'{x["sqft"]:,} sq ft'] if x.get("sqft") else []) + ([x["plot"]] if x.get("plot") else []) + [x["county"]])
    meta = f' <span style="color:{RULE}">&middot;</span> '.join(
        [f'<b style="color:{INK}">{h(bits[0])}</b>'] + [h(b) for b in bits[1:]])
    out = [
        f'<p style="margin:12px 0 4px;font:bold 11px/1.4 {SANS};letter-spacing:1.6px;text-transform:uppercase;color:{GREEN}">{h(x.get("label") or "Former " + x["was"])}</p>',
        f'<p style="margin:0 0 6px;font:{place_size}px/1.25 {SERIF}"><a href="{h(x["url"])}" style="color:{INK};text-decoration:none">{h(x.get("headline") or x["place"])}</a></p>',
        (f'<p style="margin:0 0 4px;font:14px/1.4 {SANS};color:{INK}">{h(x["place"])}</p>' if x.get("headline") else ""),
        f'<p style="margin:0;font:14px/1.5 {SANS};color:{MUTED}">{meta}</p>',
    ]
    if x.get("badges"):
        out.append(f'<p style="margin:6px 0 0;font:bold 10.5px {SANS};letter-spacing:1.5px;text-transform:uppercase;color:{OXBLOOD}">{h(" · ".join(x["badges"]))}</p>')
    if x.get("photo"):
        p = x["photo"]
        yr = f', {p["year"]}' if p.get("year") else ""
        out.append(f'<p style="margin:6px 0 0;font:11px/1.4 {SANS};color:{MUTED}">Photo: <a href="https://www.geograph.org.uk/photo/{h(p["id"])}" style="color:{MUTED}">{h(p["author"])}{h(yr)}</a>, '
                   f'<a href="https://creativecommons.org/licenses/by-sa/2.0/" style="color:{MUTED}">CC BY-SA 2.0</a></p>')
    return "".join(out)


def card(x):
    return f'<td class="col" width="270" valign="top" style="width:270px;padding:0 0 30px">{picture(x)}{details(x)}</td>'


def pick(x):
    note = f'<p style="margin:10px 0 0;font:italic 16px/1.5 {SERIF};color:{INK}">{h(x["note"])}.</p>' if x.get("note") else ""
    return (f'<tr><td class="pad" style="padding:8px 30px 0"><p style="margin:0 0 10px;font:bold 11px {SANS};letter-spacing:2px;text-transform:uppercase;color:{OXBLOOD}">Pick of the week</p>'
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>'
            f'<td class="col" width="270" valign="top" style="width:270px">{picture(x)}</td><td class="gap" width="20" style="width:20px"></td>'
            f'<td class="col" valign="top">{details(x, 24).replace("margin:12px 0 4px", "margin:0 0 6px")}{note}</td>'
            f'</tr></table></td></tr>')


def extra_block(x):
    """'Not formerly., but…': a building that was always a home, too good to leave out."""
    body = details(x, 22).replace("margin:12px 0 4px", "margin:0 0 6px")
    body = body.replace(h(x.get("label") or "Former " + x["was"]), "Not formerly., but…", 1).replace(f"color:{GREEN}\">Not formerly", f"color:{OXBLOOD}\">Not formerly", 1)
    note = f'<p style="margin:10px 0 0;font:italic 16px/1.5 {SERIF};color:{INK}">{h(x["note"])}.</p>' if x.get("note") else ""
    return (f'<tr><td class="pad" style="padding:6px 30px 18px"><table role="presentation" width="100%" cellpadding="0" cellspacing="0">'
            f'<tr><td colspan="3" style="border-top:3px solid {OXBLOOD};padding:18px 0 0"></td></tr><tr>'
            f'<td class="col" width="270" valign="top" style="width:270px">{picture(x)}</td><td class="gap" width="20" style="width:20px"></td>'
            f'<td class="col" valign="top">{body}{note}</td></tr></table></td></tr>')


def region_block(name, items):
    rows = []
    for i in range(0, len(items), 2):
        a, b = items[i], items[i + 1] if i + 1 < len(items) else None
        rows.append(f'<tr>{card(a)}<td class="gap" width="20" style="width:20px"></td>'
                    + (card(b) if b else '<td class="col" width="270" style="width:270px"></td>') + '</tr>')
    n = len(items)
    return (f'<tr><td class="pad" style="padding:26px 30px 0"><table role="presentation" width="100%" cellpadding="0" cellspacing="0">'
            f'<tr><td colspan="3" style="border-top:1px solid {INK};padding:14px 0 18px">'
            f'<span style="font:24px {SERIF};color:{INK}">{h(name)}</span>'
            f'<span style="font:13px {SANS};color:{MUTED}">&nbsp;&nbsp;{n} building{"s" if n != 1 else ""}</span></td></tr>'
            + "".join(rows) + '</table></td></tr>')


def build(listings, today, test=False, extras=()):
    # The first 518 buildings all went up together at launch on 25 October 2026; they are not "new"
    since = max((today - datetime.timedelta(days=7)).isoformat(), "2026-10-25")
    extra = next((x for x in extras if (x.get("added") or "") > since), None)
    new = [x for x in listings if (x.get("added") or "") > since and "Under offer" not in (x.get("badges") or [])]
    if not new:
        return None
    new.sort(key=lambda x: (x.get("added") or "", x.get("listed") or ""), reverse=True)
    shown = new[:MAX_ITEMS]
    n = len(new)
    featured = next((x for x in shown if x.get("photo") and x.get("note")), None) or next((x for x in shown if x.get("photo")), None)
    rest = [x for x in shown if x is not featured]
    rest.sort(key=lambda x: (x["region"], -(x.get("price") or 0)))
    # Drafted on Friday evening for Saturday morning, so the email carries Saturday's date
    send_day = today + datetime.timedelta(days=(5 - today.weekday()) % 7)
    date = send_day.strftime("%-d %B %Y")
    subject = f"{'[TEST] ' if test else ''}formerly. · {n} new building{'s' if n != 1 else ''} this week"
    total = len(listings)
    lead = summary(new)
    lead = lead[0].upper() + lead[1:]

    blocks, region, group = [], None, []
    for x in rest + [None]:
        if x is None or x["region"] != region:
            if group:
                blocks.append(region_block(region, group))
            if x is None:
                break
            region, group = x["region"], []
        group.append(x)

    more = (f'<tr><td class="pad" style="padding:4px 30px 0"><p style="margin:0;font:16px/1.5 {SERIF}">And {n - len(shown)} more on '
            f'<a href="{SITE}" style="color:{GREEN}">formerly.uk</a>.</p></td></tr>') if n > len(shown) else ""

    html = f"""<!-- formerly. weekly -->
<div style="background:{PAPER};margin:0;padding:0">
<style>@media (max-width:620px){{.wrap{{width:100% !important}}.pad{{padding-left:18px !important;padding-right:18px !important}}.col{{display:block !important;width:100% !important;max-width:100% !important}}.gap{{display:none !important}}.col img{{max-width:100% !important}}}}</style>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" bgcolor="{PAPER}" style="background:{PAPER}"><tr><td align="center">
<table role="presentation" class="wrap" width="600" cellpadding="0" cellspacing="0" style="width:600px;max-width:100%;background:{PAPER}">
<tr><td><a href="{SITE}"><img src="{SITE}/email/wordmark.png" width="600" height="150" alt="formerly." style="display:block;width:100%;max-width:600px;height:auto;border:0"></a></td></tr>
<tr><td class="pad" style="padding:4px 30px 0"><p style="margin:0;font:bold 11px {SANS};letter-spacing:2px;text-transform:uppercase;color:{MUTED}">The weekly list &middot; {h(date)}</p></td></tr>
<tr><td class="pad" style="padding:14px 30px 22px"><p style="margin:0;font:22px/1.4 {SERIF};color:{INK}">{h(lead)} came up for sale in England this week, every one built for something other than living in.</p>
<p style="margin:12px 0 0;font:15px/1.5 {SANS};color:{MUTED}">Each links to the full listing on Zoopla. Enquiries go to the agent.</p>
<table role="presentation" cellpadding="0" cellspacing="0" style="margin-top:18px"><tr><td bgcolor="{GREEN}" style="background:{GREEN}">
<a href="{SITE}" style="display:inline-block;padding:11px 20px;font:bold 15px {SANS};color:#ffffff;text-decoration:none">See all {total} buildings on formerly.uk &rarr;</a>
</td></tr></table></td></tr>
{extra_block(extra) if extra else ""}
{pick(featured) if featured else ""}
{"".join(blocks)}
{more}
<tr><td class="pad" style="padding:10px 30px 0"><table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr><td style="border-top:6px solid {INK};padding:18px 0 0">
<p style="margin:0 0 10px;font:15px/1.5 {SANS};color:{INK}">Spotted one that doesn't belong? Press <i>Report</i> on the listing at <a href="{SITE}" style="color:{GREEN}">formerly.uk</a>, or just reply to this email.</p>
<p style="margin:0 0 6px;font:12px/1.5 {SANS};color:{MUTED}">formerly. is free and not-for-profit. We are not an estate agent. Listings found on Zoopla; photographs from Geograph, credited to their photographers; labels after the old Ordnance Survey maps.</p>
<p style="margin:0 0 24px;font:12px/1.5 {SANS};color:{MUTED}"><a href="{SITE}" style="color:{MUTED}">formerly.uk</a> &middot; <a href="{SITE}/privacy.html" style="color:{MUTED}">Privacy</a> &middot; <a href="{SITE}/#feeds" style="color:{MUTED}">Regional RSS feeds</a></p>
</td></tr></table></td></tr>
</table></td></tr></table></div>"""
    # Keep every line flush-left so Buttondown's Markdown pass leaves the HTML alone
    html = "\n".join(line.strip() for line in html.splitlines() if line.strip())
    # Tag links back to the site so visits from the email can be counted (images are left alone)
    tag = f"utm_source=newsletter&utm_medium=email&utm_campaign=weekly-{send_day.isoformat()}"
    html = html.replace(f'href="{SITE}/#feeds"', f'href="{SITE}/?{tag}#feeds"')
    html = html.replace(f'href="{SITE}/privacy.html"', f'href="{SITE}/privacy.html?{tag}"')
    html = html.replace(f'href="{SITE}"', f'href="{SITE}/?{tag}"')
    return subject, html


def main():
    test = "--test" in sys.argv
    with open(os.path.join(ROOT, "docs", "data", "listings.json")) as fh:
        data = json.load(fh)
    listings = data["listings"]
    out = build(listings, datetime.date.today(), test, data.get("extras", []))
    if not out:
        print("No new listings this week; no draft created.")
        return 0
    subject, body = out
    if "--dry-run" in sys.argv:
        print(subject)
        out_path = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--out=")), None)
        if out_path:
            with open(out_path, "w") as fh:
                fh.write(f"<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width'><body style='margin:0'>{body}")
        else:
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
