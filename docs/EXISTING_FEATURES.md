# Existing Features (CrowdWise prototype, `~/Documents/crowdwise`)

> **Historical document.** Written before the scope change of 2 November 2026 (it describes the earlier, larger plan). The current scope is in `PRD.md` and `SCOPE_CHANGE_AUDIT.md`. Kept unchanged below.


Inventory taken on 1 November 2026. "Verified" means it was executed during the audit. "Code-read" means the feature was confirmed by reading the source but not exercised.

## Tourist features

| Feature | Where | Evidence | Reuse in TripNest AI |
|---|---|---|---|
| Live crowd level per attraction (Low / Moderate / High / At Capacity, stricter thresholds for ecologically sensitive sites) | `engine.level_of`, `engine.thresholds`, `engine.live` | Verified (`/api/state` 200) | Reuse; extend to all destinations |
| Hourly crowd forecast for a day, with chart | `engine.hourly`, `app.js chartSVG` | Verified (`/api/attractions/{id}`) | Reuse; re-render with chart library |
| Best visiting times for the next 7 days | `engine.best_times` | Verified (same endpoint) | Reuse |
| Probability of exceeding carrying capacity | `engine.p_exceed` (log-normal residual σ per attraction) | Verified (`p_exceed: 0.975`) | Reuse |
| Personalised recommendations with redirect advice and a "why" explanation | `engine.recommend`, `engine._score` (weights `engine.W`) | Verified (`/api/recommend`) | Reuse; add budget, duration, distance, travel period |
| Single-day itinerary with must-visit anchors and alternatives | `engine.itinerary` | Code-read | Extend to multi-day, multi-destination, saved |
| Digital queue tokens (slot capacity = 20% of hourly capacity, book / view / cancel) | `engine.book_token`, `token_status`, `db.tokens` | Code-read | Keep as differentiator (Tier 4) |
| Crowd reports from visitors, which adjust the live level | `app.r_report`, `engine.live` | Code-read | Reuse, tied to user accounts |
| Reviews with sentiment and aspect themes | `sentiment.analyze`, `db.add_review` | Code-read; 192 seeded reviews in DB | Reuse; label seeds as demo |
| Demo clock and "play time" | `app.js clockPop/startPlay`, `?at=` param | Code-read | Keep for the judge demo only |
| SVG map of attractions | `app.js mapSVG` | Code-read | Replace with Leaflet + OSM |
| Mobile-first single-page UI (Explore, Map, Plan, Tokens, Report) | `static/*` | Verified (home renders) | Restyle and extend |

## Administrator features (shared PIN)

| Feature | Where | Evidence |
|---|---|---|
| PIN check on admin routes | `app.api(admin=True)` | Verified (401 without PIN) |
| Capacity alerts with lead time | `engine.alerts` | Code-read |
| Overview KPIs and forecast heatmap | `engine.overview` | Code-read |
| Complaint themes from reviews | `engine.themes` | Code-read |
| Token list and gate redemption | `r_admin_tokens`, `engine.redeem` | Code-read |
| "What if tourists follow the app" redistribution simulation | `engine.simulate` | Code-read |
| Model accuracy vs baseline, feature importance | `model.CrowdModel.info`, `/api/model` | Verified |

## Not present

User accounts, profiles, favourites, a landing page, the India destination catalogue, search and filters, real weather, a real map, community, local businesses, admin CRUD, automated tests, API docs (OpenAPI), deployment configuration and version control.
