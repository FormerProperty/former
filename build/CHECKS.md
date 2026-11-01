# Daily availability check (formerly. and grandly.)

The playbook for the small scheduled session that keeps both sites honest: it rechecks listings
that are already live, a few each day, so that no single sitting asks Zoopla for many pages.
It runs every day except Tuesday and Friday (the intake days).

## Ground rules

- **At most 18 Zoopla listing pages per run, one every 2 to 3 minutes, randomised.** At the first
  403 or challenge page, stop for the day and save what was checked. Never try to get round bot
  protection. (Zoopla refused pages after about 20 to 25 quick fetches on 1 November 2026, and
  refusals land on Tanya's connection and Zoopla account.)
- Use Tanya's Chrome (Claude in Chrome), from a zoopla.co.uk tab, with in-page `fetch`.
  If Chrome is not reachable, stop quietly: tomorrow's run picks up the slack. Tell Tanya only if
  three runs in a row could not reach Chrome.
- Clone `FormerProperty/former` and work on `main`.

## 1. Choose today's listings

Read `status.json` (`{id: {"state", "since", "checked"}}`) and the ids in both
`docs/data/listings.json` and `grandly/site/data/listings.json`. A listing is **due** when:
- it has never been checked; or
- it is under offer and was last checked 7 or more days ago; or
- it was added to the site less than 90 days ago and last checked 21 or more days ago; or
- it was last checked 42 or more days ago.

Take up to 18 due listings, most overdue first (never-checked first). If none are due, stop.

## 2. Check each one

Fetch `https://www.zoopla.co.uk/for-sale/details/<id>/` and decide its state:
- **gone:** 404 or 410, a redirect away from `/for-sale/details/<id>/`, or the page says it is no
  longer on the market / has been removed;
- **offer:** the page shows "Sold STC", "Under offer" or "Sale agreed";
- **live:** otherwise.
Any other failure (timeout, 5xx): leave that id unchanged.

If the price shown differs from the site's, record the new price text in `overrides.json` as
`{"<id>": {"p": "£425,000"}}` (merge with any existing entry).

## 3. Save

Update `status.json` for each id checked: always set `checked` to today; set `since` to today only
when the state changed (an under-offer listing keeps its old `since`, so the 31-day clock runs).
Run `FORMER_SITE_URL=https://formerly.uk/ python3 build/build.py`, then commit `status.json`,
`overrides.json`, `docs/` and `grandly/site/` together and push to `main`, with the usual
attribution lines.

## 4. Tell Tanya only when something changed

If anything went gone or under offer, send one short message naming each (name or what it was,
and the place, and which site). If nothing changed, say nothing.
