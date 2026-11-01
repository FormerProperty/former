"""Build grandly.uk's pages from formerly.uk's (docs/index.html, docs/privacy.html).

The two sites share one design and one page script, so Grandly's page is formerly.'s with a
list of replacements: name, colours, wording, building types, regions, price bands and photo
credits. Run it after changing formerly.'s page so improvements carry over:

    python3 build/make_grandly_page.py

Every replacement must match exactly once; if formerly.'s page has changed so that one no
longer matches, the script stops and says which, rather than producing a half-converted page.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "docs")
OUT = os.path.join(ROOT, "grandly", "site")

GROUPS = """const GROUPS = [
  ['castle','Castles and towers',['castle','tower']],['manor','Manors and halls',['manor','hall']],
  ['country','Country houses and estates',['country','mansion','estate']],['town','Town houses',['townhouse']],
  ['other','Other',['other']],
];"""

OS_LABEL = """function osLabel(e){
  return e.os || ({castle:'Castle',tower:'Tower',manor:'Manor',hall:'Hall',country:'House',mansion:'Mansion',estate:'Park',townhouse:'House'})[e.type] || 'House';
}"""

CREDIT = ("const credit=e.photo?(e.photo.page"
          "?`<p class=\"credit\">Photo: <a href=\"${esc(e.photo.page)}\" target=\"_blank\" rel=\"noopener\">${esc(e.photo.author)}${e.photo.year?', '+esc(e.photo.year):''}</a>, "
          "${e.photo.licenceUrl?`<a href=\"${esc(e.photo.licenceUrl)}\" target=\"_blank\" rel=\"noopener\">${esc(e.photo.licence)}</a>`:esc(e.photo.licence||'')}, Wikimedia Commons</p>`"
          ":`<p class=\"credit\">Photo: <a href=\"https://www.geograph.org.uk/photo/${esc(e.photo.id)}\" target=\"_blank\" rel=\"noopener\">${esc(e.photo.author)}${e.photo.year?', '+esc(e.photo.year):''}</a>, "
          "<a href=\"https://creativecommons.org/licenses/by-sa/2.0/\" target=\"_blank\" rel=\"noopener\">CC BY-SA 2.0</a>, Geograph</p>`):'';")
OLD_CREDIT = re.compile(r"const credit=e\.photo\?`<p class=\"credit\">Photo: <a href=\"https://www\.geograph\.org\.uk/photo/\$\{esc\(e\.photo\.id\)\}\".*?CC BY-SA 2\.0</a></p>`:'';")

INDEX = [
    # Head: no GitHub Pages redirect; counting scripts listen on grandly.uk
    (r'<script>if\(location\.hostname\.endsWith\("github\.io"\)\)[^\n]*</script>\n', "", True),
    ('location.hostname==="formerly.uk"', 'location.hostname==="grandly.uk"', 1),
    ('location.hostname!=="formerly.uk"', 'location.hostname!=="grandly.uk"', 1),
    ("<title>formerly.</title>", "<title>grandly.</title>", 1),
    ('<link rel="canonical" href="https://formerly.uk/">', '<link rel="canonical" href="https://grandly.uk/">', 1),
    ('content="Buildings for sale in England that began life as something other than a home: chapels, mills, schools, pubs, stations and oast houses."',
     'content="Castles, manors, mansions and country estates for sale across Great Britain."', 1),
    ('<link rel="alternate" type="application/rss+xml" title="formerly." href="feed.xml">\n', "", 1),
    # Colours: oxblood leads; formerly.'s green becomes the sister-site colour
    ("--livery:#1E4D3B;     /* Brunswick green, railway and chapel railings */\n  --livery-soft:#DCE5DF;",
     "--livery:#7B2D26;     /* oxblood: grandly.'s colour */\n  --livery-soft:#EEDDD9;\n  --sister:#1E4D3B;     /* formerly.'s green, for cross-links */", 1),
    ("--livery:#86BFA4; --livery-soft:#1B2A23; --oxblood:#E1958B; --oxblood-soft:#2A1C1A; color-scheme:dark;",
     "--livery:#E1958B; --livery-soft:#2A1C1A; --sister:#86BFA4; --oxblood:#E1958B; --oxblood-soft:#2A1C1A; color-scheme:dark;", 2),
    ("/* Layout: a photo-led register. Each building carries the shorthand an old Ordnance Survey map would have printed beside it. */",
     "/* grandly. Built from formerly.'s page by build/make_grandly_page.py: edit formerly.'s page, then rerun that script. */", 1),
    # Masthead
    ('<h1 class="mark">formerly<span>.</span></h1>', '<h1 class="mark">grandly<span>.</span></h1>', 1),
    ("<p>Chapels, mills, schools, pubs, stations and oast houses for sale across England. Every one began life as something other than a home.</p>",
     "<p>Castles, manors, mansions and country estates for sale across Great Britain. Houses built to show who lived in them, and still showing it.</p>", 1),
    ('Photographs from <a href="https://www.geograph.org.uk/" target="_blank" rel="noopener">Geograph</a>.</p>',
     'Photographs from <a href="https://commons.wikimedia.org/" target="_blank" rel="noopener">Wikimedia Commons</a> and <a href="https://www.geograph.org.uk/" target="_blank" rel="noopener">Geograph</a>. A sister site to <a href="https://formerly.uk/?utm_source=grandly&amp;utm_medium=referral&amp;utm_campaign=header" class="sister">formerly.uk</a>.</p>', 1),
    # Filters
    ('<option value="">All of England</option>', '<option value="">All of Great Britain</option>', 1),
    ("""          <option value="0-300000">Under £300,000</option>
          <option value="300000-500000">£300,000 to £500,000</option>
          <option value="500000-750000">£500,000 to £750,000</option>
          <option value="750000-1000000">£750,000 to £1 million</option>
          <option value="1000000-">Over £1 million</option>""",
     """          <option value="0-1000000">Under £1 million</option>
          <option value="1000000-2000000">£1 million to £2 million</option>
          <option value="2000000-5000000">£2 million to £5 million</option>
          <option value="5000000-">Over £5 million</option>""", 1),
    ("""          <option value="">Converted and projects</option>
          <option value="done">Converted only</option>
          <option value="Project">Projects to take on</option>""",
     """          <option value="">All houses</option>
          <option value="done">Ready to live in</option>
          <option value="Project">Needing restoration</option>""", 1),
    ("Opening the register…", "Opening the register…", 1),
    # How it works
    ("""<li><span>i.</span><p>Listings that mention a former use are gathered from Zoopla each week.</p></li>""",
     """<li><span>i.</span><p>Castles, manors, country houses and estates are gathered from Zoopla each week, across England, Scotland and Wales.</p></li>""", 1),
    (r"<li><span>ii\.</span><p>Each is judged against one test:.*?</p></li>",
     "<li><span>ii.</span><p>Each is read and judged: a castle or tower house; a listed house that is unmistakably grand; or a manor or country house with real land. Flats in divided mansions, new builds and houses that are merely large are left out. Buildings that began as something else belong to our sister site, <a href=\"https://formerly.uk/?utm_source=grandly&amp;utm_medium=referral&amp;utm_campaign=how-it-works\">formerly.</a></p></li>", True),
    (r"<li><span>iv\.</span><p>Every building is checked again about once a month, a quarter of the list each week\.",
     "<li><span>iv.</span><p>Every house is checked again about once a month.", True),
    # The map-label key explains formerly.'s OS abbreviations; Grandly uses plain words, so drop it
    (r'\s*<div class="key" aria-label="Map labels used on this site">.*?</div>', "", True),
    # Weekly email
    ("<p>One email each week with the newest buildings across England. If you only want one region, its <a href=\"#feeds\">RSS feed</a> is free.</p>",
     "<p>One email each week with the newest castles, manors and country houses across Great Britain.</p>", 1),
    ("https://buttondown.com/api/emails/embed-subscribe/formerly", "https://buttondown.com/api/emails/embed-subscribe/grandly", 1),
    ("Get the week's new buildings by email", "Get the week's new grand houses by email", 1),
    ("New buildings like this every week, by email", "New houses like this every week, by email", 1),
    ("Get each week's new arrivals by email. One email a week, nothing else.", "Get each week's new grand houses by email. One email a week, nothing else.", 1),
    # Sources and footer
    (r'<div><dt><a href="https://www\.geograph\.org\.uk/".*?</dd></div>',
     '<div><dt><a href="https://commons.wikimedia.org/" target="_blank" rel="noopener">Wikimedia Commons</a></dt><dd>Many photographs come from Wikimedia Commons, including entries to Wiki Loves Monuments. Each is credited to its photographer with its licence, and links to the original.</dd></div>'
     '<div><dt><a href="https://www.geograph.org.uk/" target="_blank" rel="noopener">Geograph</a></dt><dd>Other photographs are from the Geograph project, which aims to photograph every square kilometre of Britain. Each is credited to its photographer and used under its Creative Commons licence.</dd></div>', True),
    (r"<p>formerly\. is a free, not-for-profit listing\.(.*?)<a href=\"mailto:hello@formerly\.uk\">hello@formerly\.uk</a></p>",
     r'<p>grandly. is a free, not-for-profit listing, and a sister site to <a href="https://formerly.uk/?utm_source=grandly&amp;utm_medium=referral&amp;utm_campaign=footer">formerly.uk</a>.\1<a href="mailto:hello@grandly.uk">hello@grandly.uk</a></p>', True),
    (r'\n    <p id="feeds">RSS feeds:.*?</p>', "", True),
    # Report dialog
    ("formerly. only lists buildings that were built for something other than living in. Tell us if this one does not belong,",
     "grandly. only lists castles, manors and country houses that are genuinely grand. Tell us if this one does not belong,", 1),
    ("""      <label><input type="radio" name="reason" value="Always a house" required> It was always a house</label>
      <label><input type="radio" name="reason" value="Flat in a larger building"> It is a flat within a larger building</label>
      <label><input type="radio" name="reason" value="Barn conversion"> It is a barn conversion</label>""",
     """      <label><input type="radio" name="reason" value="Other" required> It is not grand enough</label>
      <label><input type="radio" name="reason" value="Flat in a larger building"> It is a flat or part of a larger house</label>""", 1),
    ("// Reports go to formerly.'s own small database (see functions/api/report.js)", "// Reports go to the sites' shared database (see functions/api/report.js)", 1),
    # Script: building types, labels, credits, wording
    (r"const GROUPS = \[.*?\n\];", GROUPS, True),
    (r"function osLabel\(e\)\{.*?\n\}", OS_LABEL, True),
    (OLD_CREDIT, CREDIT, "credit"),
    ("<h3 class=\"place\"><a href=\"${esc(e.url)}\" target=\"_blank\" rel=\"noopener\">${esc(e.headline||e.place)}</a></h3>\n    ${e.headline?`<p class=\"where\">${esc(e.place)}</p>`:''}",
     "<h3 class=\"place\"><a href=\"${esc(e.url)}\" target=\"_blank\" rel=\"noopener\">${esc(e.headline||e.name||e.place)}</a></h3>\n    ${(e.headline||e.name)?`<p class=\"where\">${esc([e.headline?e.name:'',e.place].filter(Boolean).join(', '))}</p>`:''}", 1),
    ("(list.length===1?' building':' buildings')", "(list.length===1?' house':' houses')", 1),
    ("'<li class=\"empty\">Nothing on the register matches that yet. Try a wider area or another kind of building.</li>'",
     "'<li class=\"empty\">Nothing matches that yet. Try a wider area or another kind of house.</li>'", 1),
    ("// \"New\" for buildings added to formerly. in the last 7 days", "// \"New\" for houses added in the last 7 days", 1),
    ("[new Date(Date.now()-7*864e5).toISOString().slice(0,10),'2026-10-26'].sort()[1]", "new Date(Date.now()-7*864e5).toISOString().slice(0,10)", 1),
    ("`<span><b>${ALL.length}</b> buildings</span><span><b>${counties}</b> counties</span><span><b>${projects}</b> still to convert</span>",
     "`<span><b>${ALL.length}</b> houses</span><span><b>${counties}</b> counties</span><span><b>${ALL.filter(e=>e.type==='castle'||e.type==='tower').length}</b> castles and towers</span>", 1),
    ("That building has gone", "That house has gone", 1),
    ("Below are all ${ALL.length} buildings on formerly., newest first.", "Below are all ${ALL.length} houses on grandly., newest first.", 2),
    ("The building you came to see", "The house you came to see", 1),
    ("localStorage.getItem('former-view')", "localStorage.getItem('grandly-view')", 1),
    ("localStorage.setItem('former-view', v)", "localStorage.setItem('grandly-view', v)", 1),
    ("localStorage.getItem('__fly_sub')", "localStorage.getItem('__grandly_sub')", 1),
    ("localStorage.setItem('__fly_sub','1')", "localStorage.setItem('__grandly_sub','1')", 1),
    # The sister card wears formerly.'s green, so it reads as a visitor from the other site
    (".extracard{border-top:3px solid var(--oxblood);background:var(--oxblood-soft);padding:14px 16px 18px}\n.extracard .was{color:var(--oxblood)}",
     ".extracard{border-top:3px solid var(--sister);background:#DDE8E2;padding:14px 16px 18px}\n.extracard .was,.extracard .actions a{color:var(--sister)}\n"
     "@media (prefers-color-scheme:dark){:root:not([data-theme=\"light\"]) .extracard{background:#16231D}}\n:root[data-theme=\"dark\"] .extracard{background:#16231D}", 1),
    ("every building is advertised by its own agent", "every house is advertised by its own agent", 1),
    ('aria-label="Filter buildings"', 'aria-label="Filter houses"', 1),
]

PRIVACY = [
    ("<h1>formerly<span>.</span>", "<h1>grandly<span>.</span>", None),
    ("listing of buildings for sale in England that were originally built as something other than homes.",
     "listing of castles, manors, mansions and country estates for sale in Great Britain, and a sister site to FORMERLY_LINK.", None),
    ("so we can see which buildings interest people", "so we can see which houses interest people", None),
    ("Each building on formerly. links", "Each house on grandly. links", None),
    ("formerly.uk", "grandly.uk", None),
    ("formerly.", "grandly.", None),
    ("hello@grandly.uk", "hello@grandly.uk", None),
]


def apply(text, rules, name):
    for old, new, count in rules:
        if isinstance(old, re.Pattern) or count is True or count == "credit":
            pat = old if isinstance(old, re.Pattern) else re.compile(old, re.S)
            n = len(pat.findall(text))
            want = 1 if count == "credit" else None  # the card; extraCard handles Commons itself
            if n == 0 or (want and n != want):
                sys.exit(f"{name}: pattern not found as expected ({n}): {pat.pattern[:80]}")
            text = pat.sub(lambda m: m.expand(new) if "\\1" in new else new, text)
        elif count is None:
            text = text.replace(old, new)
        else:
            n = text.count(old)
            if n != count:
                sys.exit(f"{name}: expected {count} of {old[:80]!r}, found {n}")
            text = text.replace(old, new)
    return text


def main():  # (FORMERLY_LINK is filled in after the blanket formerly -> grandly swap)
    os.makedirs(OUT, exist_ok=True)
    page = apply(open(os.path.join(SRC, "index.html")).read(), INDEX, "index.html")
    open(os.path.join(OUT, "index.html"), "w").write(page)
    priv = apply(open(os.path.join(SRC, "privacy.html")).read(), PRIVACY, "privacy.html")
    priv = priv.replace("FORMERLY_LINK", '<a href="https://formerly.uk/">formerly.uk</a>')
    open(os.path.join(OUT, "privacy.html"), "w").write(priv)
    print("grandly/site/index.html and privacy.html written")


if __name__ == "__main__":
    main()
