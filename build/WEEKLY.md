# formerly. intake (Tuesdays and Fridays)

The playbook for the scheduled session, run every **Tuesday and Friday** at 10:43, that finds new listings, judges them and
queues them for Tanya's review. Follow it step by step. Nothing goes live from this
session: everything lands in the review queue at https://formerly.uk/review.

## 0. Ground rules

- **Pace Zoopla gently.** At least 8 to 12 seconds between page fetches, randomised. Never run
  two loops at once. If Zoopla returns 403 or a challenge page, back off for a few minutes,
  and stop for the week if it keeps happening. Never try to get round bot protection.
- **Use Tanya's Chrome** (Claude in Chrome), where she is signed in to Zoopla, and fetch pages from
  a zoopla.co.uk tab with in-page `fetch` + `DOMParser`. Keep progress in `localStorage`
  (`__formerlyWeek`) so a sleeping computer only pauses the run.
- If Chrome is not reachable, stop, and tell Tanya in one short message that this week's intake
  will run next week (or when she asks).
- **Copyright:** read agents' descriptions to judge and summarise, but never copy their wording
  or photos. Headlines and notes are always our own words.

## 1. Get the repository

Clone `FormerProperty/former` (add it to the session first if needed) and work on `main`.

## 2. Collect candidate listing ids

1. **Alert emails.** In Gmail search `from:zoopla newer_than:8d`. The emails are large, so
   fetch each thread in full (it is saved to a file) and parse the HTML with a script rather
   than reading it. Leave the emails as they are (do not mark them read or move them). What we learned about the format:
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
     on the site, refresh its price during the availability check.
   - The same email can arrive twice, and the first emails after an alert is created are a
     catch-up of the previous week or so. De-duplicate ids.
   In a test on 26 October the alerts caught about 85% of the qualifying buildings listed in the
   previous week; the misses were worded "coach house", "village chapel" and "Methodist church"
   without "former" or "converted". So the sweep below still matters.
2. **Newest-listing sweep (backstop): Fridays only.** On Tuesdays the alert emails are enough;
   on Fridays, for each phrase below, fetch page 1 of
   `https://www.zoopla.co.uk/for-sale/property/england/?keywords="<phrase>"&q=England&results_sort=newest_listings`
   (quoted phrase, URL-encoded) and collect listing ids added in the last 8 days.
   Phrases: former chapel, converted chapel, former school, old school house conversion,
   converted school, former mill, converted mill, watermill, windmill, former church,
   converted church, former pub, former public house, former inn, oast house, former station,
   signal box, water tower, former bank, former post office, former police station,
   former fire station, coach house, toll house, former forge, smithy, granary, malthouse,
   former dairy, former bakery, engine house, pumping station, former library, court house,
   telephone exchange, sunday school, meeting house, former warehouse, former factory,
   chapel conversion, church conversion, school conversion, mill conversion, coach house,
   methodist church, village chapel.
3. **Drop ids we have already seen:** anything in `docs/data/listings.json`, `removed.json`,
   `pending/*.json` or `pending/judged-out.json`.

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

## 6. Rolling availability check

Every building on the site is rechecked about once a month: an eighth of them on each run (two runs a week).

1. Read `status.json` (`{id: {"state", "since", "checked"}}`) and the ids in
   `docs/data/listings.json`. Work out this week's batch size from the current list:
   **N = an eighth of the listings, rounded up, but at least 20 and at most 125.**
   (At 520 listings that is 65.) Pick the N listed ids with the oldest `checked` date
   (ids with no entry count as never checked, so they go first).
   The 250 cap protects Zoopla from heavy traffic: above about 1,000 listings the cycle
   stretches beyond a month, so say so in the summary to Tanya when the cap applies.
2. Fetch each listing page at the same gentle pace as above and decide its state:
   - **gone:** the page returns 404 or 410, redirects away from `/for-sale/details/<id>/`,
     or says the property is no longer on the market / has been removed;
   - **offer:** the page shows "Sold STC", "Under offer" or "Sale agreed";
   - **live:** otherwise.
   If a fetch fails for any other reason (403, timeout), skip that id this week and leave
   its entry unchanged.
3. If the price shown differs from the site's, record the new price text in
   `overrides.json` as `{"<id>": {"p": "£425,000"}}` (merge with any existing entry).
4. Update `status.json` for each id checked: always set `checked` to today. Set `since` to
   today only when the state has changed (keep the old `since` when an under-offer building is
   still under offer, so the 31-day clock keeps running).
5. The build does the rest: **gone** buildings leave the site; **offer** buildings show an
   "Under offer" flag for up to 31 days and then leave the site; a building that comes back on
   the market simply loses its flag. Under-offer buildings are never posted to Bluesky or put
   in the email.
6. Commit `status.json` (and `overrides.json`) together with the week's pending file (one commit is fine). Run
   `FORMER_SITE_URL=https://formerly.uk/ python3 build/build.py` before committing so the live
   site updates straight away, and include `docs/` in the commit.

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
  main reasons, and the link https://formerly.uk/review;
- availability: how many existing buildings were checked (and N, if the cap applied), which have gone (name and place),
  which are newly under offer, and which dropped off after a month under offer.

**Health check:** about 100 qualifying buildings come to market each month, so a normal week
finds roughly 20 to 30 new ones, so each run (Tuesday or Friday) roughly 10 to 15. If a run finds
fewer than 5 (outside the Christmas and New Year lull), say so plainly and suggest checking that the alerts and the sweep are working.

Mention that the weekly email draft is built at 7pm on Friday from whatever has been approved by then. If something was taken down in error, Tanya can ask for it to be put back
(set its `status.json` state to `live`).
