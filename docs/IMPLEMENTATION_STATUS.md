# TripNest AI: Implementation Status

Updated 2 November 2026. "Done" means implemented and verified by the tests listed in `USER_STORIES.md`.

| Stories | Title | Status |
|---|---|---|
| STORY-001 to STORY-007 | Crowd prediction: place page, level and time range, estimate, timeline and best time, 7 days, provenance, model | Done (demonstration data) |
| STORY-008, STORY-009 | Typed city; browser location with permission; dynamic greeting | Done |
| STORY-010 | Popular places near me | Done |
| STORY-011 | Hidden gems | Done |
| STORY-012 | Date, interest and time-of-day refresh | Done |
| STORY-013 | Interactive crowd map with filters and popups | Done |
| STORY-014 | Explained scoring | Done for API and reasons; breakdown not in the interface |
| STORY-015 | Compare destinations | **API only**; the comparison screen was removed in the redesign |
| STORY-016 to STORY-021 | Home page, details page, responsive, states, catalogue and photographs, header navigation | Done |
| STORY-022, STORY-023 | Tests; configuration and health | Done |
| STORY-024 | Public deployment | Done: live on Render free plan at https://tripnest-ai-1rug.onrender.com, checked 2 November 2026 (sleeps when idle; first load about 30 s) |
| STORY-025 | Documentation | Done |

## What exists
84 destinations (all 36 states and UTs), 271 attractions, 77 starting cities, one stored credited photograph per destination, a crowd model retrained on 2 November 2026, the explore, prediction and recommendation APIs, a three-page web app, 101 backend and 24 browser tests, Docker and Render files, 14 documents with PDFs.

## What does not exist or is not verified
PostgreSQL run (the live app uses seeded SQLite); Docker build; real crowd data; accuracy on real data; load testing; an accessibility audit; cross-browser and real-device testing; a typed destination search box (places are reached through cards and the map); the catalogue's new destinations' coordinates were entered from memory (approximate to a few kilometres) and should be reviewed.

## Removed from the product (code kept, unmounted)
Accounts, itinerary planner, community, reviews, weather, crowd reports, admin console, local listings; the previous front ends are in `frontend/legacy/`. Backup: `tripnest-ai-backup-before-scope-change.tar.gz` (next to the project folder; it predates the redesign).

## Open decisions for the team
1. Review the 30 added destinations' details and the stored photographs.
2. Approve deleting the unplugged code once it is certainly not wanted.
