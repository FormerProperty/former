# formerly. intake (Tuesdays and Fridays): new listings

The playbook for the scheduled session, run every **Tuesday and Friday** at 10:43, that finds new listings, judges them and
queues them for Tanya's review. Follow it step by step. Nothing goes live from this
session: everything lands in the review queue at https://formerly.uk/review.

## 0. Ground rules

- **Pace Zoopla gently: one page every 60 to 120 seconds, randomised, and at most 30 Zoopla
  pages in a sitting** (searches and listing pages together, both sites). Zoopla's bot protection
  refused pages after about 20 to 25 quick fetches on 1 November 2026, and the refusals land on
  Tanya's connection and Zoopla account, which formerly. depends on. Never run two loops at once.
  At the first 403 or challenge page, stop Zoopla for the day: queue what is already judged, and
  leave the rest for the next run. Never try to get round bot protection.
- **Open a page only when the alert card leaves a real chance it qualifies.** The card's price,
  bedrooms, type, address and summary are enough to rule out most noise without a fetch.
- **Start fresh, stop at the first refusal (agreed with Tanya, 5 Nov 2026).** At the start of the
  run open a new tab and load `https://www.zoopla.co.uk/` once, normally, like any browser visit;
  then fetch pages from that tab at the pace above. At the first 403 or challenge page, stop using
  Zoopla for the day. Never reload, open another tab, or load a page normally to clear a refusal
  and carry on: that would be working round the protection, which we do not do.
- **Use Tanya's Chrome** (Claude in Chrome), where she is signed in to Zoopla, and fetch pages from
  a zoopla.co.uk tab with in-page `fetch` + `DOMParser`. Keep progress in `localStorage`
  (`__formerlyWeek`) so a sleeping computer only pauses the run.
- If Chrome is not reachable, stop, and tell Tanya in one short message that this week's intake
  will run next week (or when she asks).
- **Copyright:** read agents' descriptions to judge and summarise, but never copy their wording
  or photos. Headlines and notes are always our own words.

## 0b. Card first, page only when asked (agreed with Tanya, 10 Nov 2026)

Zoopla refuses our page requests after a handful of pages, so pages are now opened only for
listings Tanya has asked about. Each run:

1. **Visit queue first.** Read `visit-queue.json` (Tanya's "Look closer" clicks on the review page,
   Grandly first, then oldest). Open those listing pages, **at most 8 Zoopla pages in the run in
   all** (the homepage visit at the start does not count), one every 60 to 120 seconds, stopping
   for the day at the first refusal. For each page read, judge it fully (section 3) and **replace
   that id's card in its `pending/` file** with the full record (section 4, or the Grandly fields):
   exact `ll` from the listing's map, our headline, the facts, and **no** `card` key and **no**
   `ph` key (the sync then looks for photos with the exact location and returns the card to
   Tanya's queue). If the page shows it does not qualify after all, keep it in the queue as a
   full card with a `why` saying so, so Tanya can reject it. Ids not reached stay in the queue
   for the next run.
2. **New listings from the alert emails: card only.** Do not open their pages. Rule out the clear
   noise from the card (new builds, flats in bigger buildings, street-name matches, barns,
   anything outside the remit) into `judged-out.json` as before. Everything plausible goes to
   `pending/<date>.json` as a card: the fields the card gives (`p`, `b`, `a`, `t`, `w`, a short
   headline in our own words), `ll` from the postcode via `https://api.postcodes.io` (say in `why`
   that the pin is the postcode or district centre), `"card": 1`, and `why` starting
   `EMAIL ONLY, page not read:`. Tanya then approves it as it is, rejects it, or clicks
   "Look closer".
3. **No sweep searches** for now: they used up the page allowance on noise.
4. If pages remain within the 8 after the visit queue, do not spend them on new cards; leave the
   choice to Tanya.

Sections 2 (collecting ids from the emails), 3 and 4 (how to judge and record) still apply; only
*when* a page is opened has changed. Section 2's Friday sweep is suspended.

## 1. Get the repository

Clone `FormerProperty/former` (add it to the session first if needed) and work on `main`.

## 2. Collect candidate listing ids

1. **Alert emails.** In Gmail search `from:zoopla newer_than:8d`. The emails are large, so
   fetch each thread in full (it is saved to a file) and parse the HTML with a script rather
   than reading it. Leave the emails as they are (do not mark them read or move them). What we learned about the format:
   - **Grandly alerts** ("grandly: …" in the subject or heading) belong to the Grandly section
     below, not to formerly.: judge their cards there, and record outs in
     `pending/grandly-judged-out.json`, never in formerly.'s `judged-out.json`.
   - Take only the listing links **before** the "Similar properties nearby" section, i.e.
     `/for-sale/details/<id>/?utm_campaign=...` links without `utm_content=similar_listing`.
     The "similar" ones are Zoopla's suggestions, not matches.
   - Each card gives price, bedrooms, property type and address, which is enough to sort
     the obvious noise before opening any page: developments of flats (Granary Square,
     Neptune Street, warehouse lofts), new builds named after old buildings ("The Henley" at
     Redwood Avenue) and street-name matches (Windmill Drive, Watermill Way, Signal Box Way).
     Do not skip a card only because Zoopla calls it a flat: whole buildings are sometimes
     mislabelled, so open it if the address or price suggests a whole building.
   - "Price reduced" emails list matching listings whose price has dropped. Treat their ids
     as candidates too (they can be older listings we have missed), and when one is already
     on the site, record the new price in `overrides.json` from the card (no page fetch needed).
   - The same email can arrive twice, and the first emails after an alert is created are a
     catch-up of the previous week or so. De-duplicate ids.
   In a test on 26 October the alerts caught about 85% of the qualifying buildings listed in the
   previous week; the misses were worded "coach house", "village chapel" and "Methodist church"
   without "former" or "converted". So the sweep below still matters.
2. **Newest-listing sweep (backstop): Fridays only, 5 searches.** The alerts catch most
   qualifying buildings; the test on 26 October found the misses were worded without "former" or
   "converted". So on Fridays fetch page 1 of
   `https://www.zoopla.co.uk/for-sale/property/england/?keywords="<phrase>"&q=England&results_sort=newest_listings`
   for these phrases only, and collect listing ids added in the last 8 days:
   coach house, village chapel, methodist church, chapel conversion, school conversion.
   (Add a phrase here only when a qualifying building is found to have slipped past the alerts.)
3. **Drop ids we have already seen:** anything in `docs/data/listings.json`, `removed.json`,
   `pending/*.json` or `pending/judged-out.json`.

## 2b. Comparison run: email-only judging (Friday 6 November 2026 only)

Tanya wants to compare the current method with an email-only method that never opens a Zoopla
page. On **Friday 6 November 2026 only**, do this **before** opening any listing page:

1. For every candidate id that came from an alert email (formerly. and, if the Grandly intake is
   on, grandly.), judge it using **only** what the email card shows (price, beds, type, address,
   summary line) plus a location from the postcode via the free API
   `https://api.postcodes.io/postcodes/<postcode>` (or `/outcodes/<outcode>` when only the district
   is given). Do not open Zoopla pages or follow links in the emails for this step.
2. For each, record `{"id", "decision": "in" | "out" | "unsure", "why", and for "in" or "unsure"
   the usual fields you can fill (p, b, a, t, w, h, ll...)}` in
   `compare/2026-11-06-email-only.json`. Write the headline from the card alone; leave out what the
   card does not say.
3. Commit that file first, before any page is opened, so the blind judgement is on record.
4. Then carry on with the normal run below (open pages, judge, queue). Only the normal run's
   results go into `pending/`; the email-only file is for comparison and is never queued.
5. At the end, write `compare/2026-11-06-report.md`: a table of every candidate with both
   decisions side by side (email-only vs full), where they differ and why, how headlines and
   notes compare, how far the postcode location was from the listing's map location, how many
   Zoopla pages the normal run opened, and which candidates came only from the Friday sweep
   (which the email-only method would never see). Finish with a short verdict. Send Tanya the
   main numbers in the run message and say the full report is in the repository.

## 3. Judge each new listing

Open `https://www.zoopla.co.uk/for-sale/details/<id>/` and read the page text (title,
key features, description, the "property details" facts, tenure, service charge).

**Include** only if the building, or a substantial part of it (a half is fine), was **built
for something other than living in**: chapels, churches, schools, mills, pubs and inns,
stations, oasts, water towers, banks, post offices, police and fire stations, coach houses,
toll houses, forges, granaries, malthouses, dairies, bakeries, engine and pumping houses,
libraries, court houses, telephone exchanges, warehouses, factories and the like.

**Exclude:**
- barn conversions;
- flats or apartments within a larger converted building (leasehold plus a service charge in
  a multi-unit conversion is the usual tell). Zoopla sometimes calls a whole building a "flat":
  read the description before deciding;
- houses that were always houses: station masters' houses, mill houses, school houses,
  coastguard cottages, almshouses, lodges, vicarages and rectories;
- houses that merely stand on Chapel Lane, Mill Road and so on;
- new builds in the grounds of an old building; sites where the building is to be demolished;
- anything outside England.

When unsure, include it with a clear `why` so Tanya can decide.

**"Not formerly., but…"** Occasionally a building fails the rules but is exceptional: a castle,
a tower house, a folly, a remarkable manor. Do not queue it. Instead, mention it in the run's
notes ("Possible Not formerly., but…: <address>, <Zoopla link>, <one line why>"). If Tanya wants
it, it goes in `extras.json` (same record format, with `n` as the short explanation). Extras
appear as one card on the site and a section in the weekly email; they are never counted,
posted to social media or put in the RSS feeds.

## 4. Record each included listing

One JSON object per building, in the judging format:

| key | meaning |
|---|---|
| `id` | Zoopla id (string) |
| `p` | price text as shown, e.g. `"£450,000"` (or `"POA"`) |
| `b` | bedrooms as a string, `""` if not stated |
| `a` | address line as shown on the listing |
| `l` | listed date, `YYYY-MM-DD` |
| `au` | `1` if sold by auction |
| `t` | type key: chapel, church, school, mill, windmill, pub, oast, station, toll, tower, coach, police, fire, bank, postoffice, dairy, forge, granary, malthouse, bakery, hall, works, other |
| `w` | what it was, in our words: `"Methodist chapel, 1872"`, `"watermill, Grade II"`; add `", unconverted"` when it has not been converted |
| `n` | optional short note in our words, no full stop: `"With about two acres beside the river"` |
| `g` | optional flags, `|` separated: `Project`, `Auction` |
| `h` | **headline**, in our own words (rules below) |
| `sq` | floor area in sq ft (number) if stated |
| `ac` | plot size as text, e.g. `"0.4 acres"`, if stated |
| `gr` | listed grade (`"II"`, `"II*"`, `"I"`) if stated |
| `bt` | date built as text (`"1872"`, `"c.1840"`, `"Victorian"`) if stated |
| `ag` | agent name as shown on Zoopla |
| `ll` | `[lat, lng]` from the static map image URL (`.../static/<lng>,<lat>,<zoom>/...`) |
| `why` | one line for Tanya: what in the listing shows it qualifies, and any doubt |

**Headline rules**
- 4 to 10 words, sentence case, no full stop. It should make someone want to click.
- Lead with what makes this building itself distinctive: its age, its feature, its setting,
  or its state. Good: "Victorian bank with its banking hall intact",
  "Riverside watermill with working wheel and two acres",
  "Unconverted 1870s chapel with planning for a home".
- Do not repeat the place name or the price (the card already shows them).
- No estate-agent language: no "stunning", "rare opportunity", "must see", "deceptively".
- Facts only. Never invent a feature that the listing does not state.

## 5. Queue for review

1. Write the week's buildings to `pending/<YYYY-MM-DD>.json` (a JSON array).
2. Append every id judged **out** to `pending/judged-out.json` (an object of id to one-line
   reason), so it is not judged again next week.
3. Commit and push to `main`, with the session's usual attribution lines. The push starts the
   sync job, which puts the buildings in the review queue within a few minutes.

## 6. Availability checks: not in this run

Since 2 November 2026 the availability checks (gone, under offer, price changes) run in their
own small daily session, so that no single sitting asks Zoopla for too many pages. The playbook
is `build/CHECKS.md`. This run does not check availability. In the run record (step 7) leave
`availability` out.

## 7. Record the run on the review page

Add this run to the front of `docs/review/runs.json` (keep the 10 most recent) and include it
in the commit. The review page shows the newest one at the top. Format:

```json
{"runs": [{"date": "2026-10-27", "label": "Tuesday 27 October",
  "checked": 34, "queued": 12, "left_out": 22,
  "reasons": ["14 flats in larger conversions", "5 new builds named after old buildings", "3 always houses"],
  "availability": {"checked": 65, "gone": ["Former chapel, Partway Lane, Hazelbury Bryan"],
                   "offer": ["Former post office, Huntsham"], "expired": []},
  "health": "",
  "notes": ""}]}
```

Use `health` only for a warning (for example, a run that found fewer than 5 new buildings),
and `notes` for anything else Tanya should know (Chrome dropped out, Zoopla refused pages).

## 8. Tell Tanya

Send one short message with:
- new listings: how many were checked, how many queued for review, how many left out and the
  main reasons, and the link https://formerly.uk/review (Grandly's numbers separately).

**Health check:** about 100 qualifying buildings come to market each month, so a normal week
finds roughly 20 to 30 new ones, so each run (Tuesday or Friday) roughly 10 to 15. If a run finds
fewer than 5 (outside the Christmas and New Year lull), say so plainly and suggest checking that the alerts and the sweep are working.

Mention that the weekly email draft is built at 7pm on Friday from whatever has been approved by then. If something was taken down in error, Tanya can ask for it to be put back
(set its `status.json` state to `live`).

## Grandly (sister site, grandly.uk): Tuesdays and Fridays

**Only if `build/grandly.json` has `"intake": true`.** Until then, skip this section entirely
(and skip "grandly:" alert emails). It has been on since 10 November 2026.

**Promise:** a house built to show status, that still reads as one. Great Britain (England,
Scotland, Wales; not Northern Ireland, the Isle of Man or the Channel Islands).

**Include** a whole house that meets one of these:
1. **Castles and fortified houses:** castles, tower houses, pele towers, bastles, fortified and
   moated manor houses. Any price.
2. **Listed and clearly grand:** listed (Grade I, II* or II in England and Wales; Category A or B
   in Scotland) **and** at least one of: 7+ bedrooms; about 15+ acres; a named house with real
   recorded history (a family seat, a known architect). In a large city, a Grade I or II*
   townhouse of 5+ bedrooms counts (Regent's Park terraces, Bath crescents).
3. **Country houses with land:** manor houses, halls, granges, mansions and country houses with
   about 20 acres. Use judgement: 12 acres with an important house can count; 25 acres with a
   modern house does not.

**Exclude:** flats, apartments, wings or "part of" any house; new builds, however grand; lodges,
cottages or barns on an estate sold separately; development plots; buildings built for
something else (those are formerly.'s: an abbey, a rectory, a castle that became a school stays
on formerly. if it was built as something other than a home).

**Zoopla searches cannot do this alone:** "castle" matches Castle Road and Castle Douglas;
Grade II* cannot be searched (the asterisk is ignored); acreage cannot be filtered. Read every
listing. The same house is often listed twice by different agents: keep one (the fuller
listing) and note the other id in `why`.

**Where candidates come from:** Zoopla alert emails named "grandly: …" (13 alerts, Great Britain),
handled card first exactly as in section 0b: rule out the clear noise from the card (new builds,
flats, street-name matches, estates' lodges and plots) into `pending/grandly-judged-out.json`;
queue the plausible ones as cards (`"card": 1`, `why` starting `EMAIL ONLY, page not read:`,
`ll` from the postcode, `s`, and `nm` if the card names the house). No sweep searches. Grandly
houses Tanya marks "Look closer" go to the front of the visit queue.

**Record** each included house in the judging format (section 4), plus:

| key | meaning |
|---|---|
| `s` | always `"grandly"` |
| `nm` | the house's proper name if it has one: `"Law Castle"`, `"Wadworth Hall"`; `""` if none |
| `t` | castle, tower, manor, hall, country, mansion, estate, townhouse, other |
| `w` | what it is, in our words: `"15th-century tower house, Category A listed"` |
| `gr` | `"I"`, `"II*"`, `"II"`, `"A"`, `"B"`, if stated |

Headline rules as for formerly. (our words, facts only, no estate-agent language).

**Queue** them in `pending/<YYYY-MM-DD>-grandly.json`; record ids judged out in
`pending/grandly-judged-out.json` (not formerly.'s file). Mention the Grandly numbers separately
in the run summary.
