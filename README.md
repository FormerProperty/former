# formerly.

Buildings for sale in England that started life as something other than a home:
chapels, mills, schools, pubs, stations, oast houses and more.

The site is a static page served by GitHub Pages from the `docs/` folder. It holds
no personal data. Email sign-ups are handled by the newsletter service, not here.

## How it fits together

```
export/*.json     judged listings (one file per batch; later files override earlier ones)
removed.json      ids to leave out, with the reason (flat, sold, misjudged)
build/build.py    turns the above into the site's data and feeds
docs/             the published site
  index.html        the page
  data/listings.json  every current building
  feed.xml          RSS feed of the newest 60 buildings (for the newsletter and social posts)
  feeds/<region>.xml  one RSS feed per region
  privacy.html      privacy notice
```

## Updating

1. Add a new batch of judged listings as `export/NN.json`, or add ids to `removed.json`.
2. Run `python3 build/build.py` (set `FORMER_SITE_URL` to the live address so feeds link correctly).
3. Commit and push. GitHub Pages republishes within a minute or two.

## The test every listing must pass

The building, or a whole or substantial part of it, was built for something other than living in.
Out: barn conversions, flats within larger conversions, houses that were always houses
(station masters' houses, miller's houses, school houses, coastguard cottages, almshouses),
and houses that are merely on Chapel Lane or Mill Road.

## Sources and rights

Listings link to their original advert. We don't copy agents' photos or descriptions; the
short notes are our own words. Building illustrations are original. Any photos come from
Geograph under Creative Commons, credited to the photographer.

## Review and reports (Cloudflare)

- The site is served by Cloudflare Pages from `docs/`, with small server functions in `functions/` (config in `wrangler.toml`).
- **Report button** → `POST /api/report` → `reports` table in the D1 database `formerly`. No personal data is stored.
- **Review page** at https://formerly.uk/review, behind Cloudflare Access (email code login, allowed address in `wrangler.toml`). The admin API also checks the Access signature itself.
- **New candidates** go in `pending/*.json` (judging format: id, p, b, a, l, t, w, n, g, au, plus optional `why`).
- **Hourly sync** (`.github/workflows/sync.yml`, `build/sync.py`) queues pending candidates for review, then applies approvals (to `export/90-approved.json`) and take-downs (to `removed.json`), rebuilds and pushes. It proves its identity with a GitHub OIDC token, so no secret is stored anywhere.
