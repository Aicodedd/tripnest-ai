# Changelog

## 2026-11-02 (later): Location-first redesign

**Changed**
- New interface following the supplied reference: hero photograph with a location-first search panel; popular places near you; best time to visit; "Escape the Crowds" hidden gems; interactive crowd map with filters and popups; destination page with timeline, chart and 7-day trend.
- Catalogue grown from 54 to 84 destinations (271 attractions) so hidden gems exist near most cities; every destination has a stored Wikimedia photograph with credit and licence (database columns plus an Alembic migration; `scripts/fetch_images.py`).
- Crowd model retrained on all 271 attractions: test MAPE 9.38% against baselines of 31.79% and 27.45%.
- Browser location is used at once if already allowed, otherwise only after a click; denied falls back to a typed city.

**Added**
- `GET /api/explore`, `GET /api/locations/nearest`, timeline and best-window logic (a best time is only recommended when the data supports it), schema-upgrade helper for local SQLite files, 24 browser tests and 29 new backend tests.

**Removed from the interface**
- Compare screen, typed destination search box, per-factor score breakdown (the APIs remain).

**Fixed**
- Wrong destination photographs; weak "alternative to" pairings; busy places shown as hidden gems; map popup cut off; sideways scrolling on phones; reasons from an earlier search shown for a new one.

## 2026-11-02: Scope change to two core features

**Changed**
- Product reduced to *tourist crowd prediction* and *smart destination recommendation*.
- New three-page web app (home, results with compare, destination) replacing the larger app; visual style follows the supplied reference.
- Recommender rewritten: four transparent factors (crowd 0.40, interest 0.25, distance 0.20, season 0.15), re-normalised when a factor is missing; popularity removed.
- Browser location is requested only on click and rounded to about 1 km.

**Added**
- `GET /api/locations/search|resolve|all` (77 cities, aliases, manual-entry errors).
- `GET /api/destinations/{slug}/prediction` (date, time range, level, likely range, best time, 7-day trend, provenance, limitations).
- `GET /api/recommendations` with start, date, interest, distance limit.
- Crowd heat map (yellow medium, orange high, red at capacity, plain when quiet), batched forecasts (map data 1.6–3 s down to about 0.05 s), Wikimedia photos with credit.
- Documents: MRD (1 page), PRD (2 pages), epics, stories, traceability, architecture, database, API, AI/ML, test plan and results, deployment, user and judge guides, scope-change audit; PDF build script with page-count and test-reference checks.

**Removed from the product (kept on disk, unmounted, tests moved to `tests/legacy`)**
- Accounts, itinerary planner, community, reviews and sentiment, weather, traveller reports, admin console, local listings. No data or table was deleted.

**Fixed**
- Back link on the destination page; accessible names of the location fields; phone layout of the week tiles and chart text; gradient placeholders; credentials could appear in the address bar on a fast native submit (earlier build); pages writing into the next page after a slow load (earlier build).

**Not done**
- Public deployment (needs a hosting account).

## 2026-11-01: First full build (superseded scope)

Catalogue for all states and union territories, crowd model with chronological split and baselines, accounts, itinerary planner, community, reviews, admin console, Discover screen with crowd heat map, Docker and Render files. Replaced by the two-feature scope above.

## 2026-10-31: CrowdWise prototype

Single-destination prototype with 12 simulated attractions (separate project, `~/Documents/crowdwise`, untouched).
