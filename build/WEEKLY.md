# formerly. weekly intake

The playbook for the weekly scheduled session that finds new listings, judges them and
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

1. **Alert emails.** In Gmail search `from:zoopla newer_than:8d` and pull every
   `/for-sale/details/<id>/` link from the alert emails.
2. **Newest-listing sweep (backstop).** For each phrase below, fetch page 1 of
   `https://www.zoopla.co.uk/for-sale/property/england/?keywords="<phrase>"&q=England&results_sort=newest_listings`
   (quoted phrase, URL-encoded) and collect listing ids added in the last 8 days.
   Phrases: former chapel, converted chapel, former school, old school house conversion,
   converted school, former mill, converted mill, watermill, windmill, former church,
   converted church, former pub, former public house, former inn, oast house, former station,
   signal box, water tower, former bank, former post office, former police station,
   former fire station, coach house, toll house, former forge, smithy, granary, malthouse,
   former dairy, former bakery, engine house, pumping station, former library, court house,
   telephone exchange, sunday school, meeting house, former warehouse, former factory.
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

## 6. Tell Tanya

Send one short message: how many listings were checked, how many were queued, how many were
left out and why (in a line), and the link https://formerly.uk/review. Mention that the
weekly email draft is built on Friday morning from whatever has been approved by then.
