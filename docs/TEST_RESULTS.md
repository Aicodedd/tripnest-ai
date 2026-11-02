# TripNest AI: Test Results

Executed on **2 November 2026** (macOS, Python 3.14.7, pytest 9.2, Playwright 1.58 with Google Chrome, internet available). Everything below was actually run.

## Live deployment (checked 2 November 2026)
Render free plan, https://tripnest-ai-1rug.onrender.com. Health returned ok with the model loaded; the first request after idle took about 32 s (free plan wakes from sleep); home page 200; `/api/explore` for Coimbatore returned 6 popular places, 6 hidden gems and 27 map points with photographs; security headers present. All 24 browser tests passed against this URL (103 s). The container runs the app with a throw-away SQLite file seeded at start-up (no PostgreSQL), so **PostgreSQL remains untested**.

## Summary
| Suite | Command | Passed | Failed | Skipped | Not run |
|---|---|---|---|---|---|
| Backend (unit, ML, explore, API) | `cd backend && python -m pytest` | **101** | 0 | 0 | 0 |
| Browser end to end (real Chrome) | `sh e2e/run.sh` | **24** | 0 | 0 | 0 |
| Documents | `python docs/build_pdfs.py` | see the build output | | | |
| Browser suite against the live site | `E2E_BASE=https://tripnest-ai-1rug.onrender.com python -m pytest e2e` | **24** | 0 | 0 | 0 |
| Live API checks | health, home page, `/api/explore`, security headers | pass | 0 | 0 | 0 |

Backend per file: `test_catalog_crowd.py` 13, `test_core_features.py` 35, `test_crowd_engine.py` 16, `test_explore.py` 28, `test_map_photos.py` 8, `test_schema_upgrade.py` 1. The browser suite checks console errors, page errors and failing API calls in each test.

## The nine-step scenario (browser)
| Step | Result |
|---|---|
| Open the app; hero, navigation, search panel, no sign-in | Pass |
| Location: denied permission falls back to a typed city (alias "Bangalore" gives Bengaluru); no permission request on load; granted permission is used at once and the greeting reads "around Coimbatore" ("near Coimbatore" between cities) | Pass |
| Popular places with photo, crowd chip (green, yellow, red), distance, best time, description, View Details | Pass |
| Date, interest and time of day refresh predictions (Goa on Saturday "High crowd", on Tuesday "Moderate crowd") | Pass |
| Best time to visit: four-slot timeline, calmest slot, hour window, hourly chart; switching destinations updates it | Pass |
| Hidden gems: lesser-known, Low or Moderate, with reasons and "calmer alternative to" | Pass |
| Map: your position, different markers for popular places and gems, filters, popup (photo, level, best time, View Details) fully inside the map | Pass |
| Destination page: prediction, timeline, best time, chart, 7-day tiles, places inside, map, explanation only for the search that produced it | Pass |
| Phone, tablet, laptop and desktop: the flow completes and the page never scrolls sideways | Pass (Chrome emulation) |

## Model evaluation (from `backend/models/metrics.json`, retrained 2 November 2026 on all 271 attractions)
Chronological split; test fortnight 19 October to 1 November 2026 (41,902 hourly rows). Model MAPE **9.38%**, WAPE 8.64%, MAE 54.8 people, R² 0.986; baseline "same hour last week" MAPE 31.79%; baseline "weekday-hour average" MAPE 27.45%. **Measured on simulated demonstration data only.**

## Design inspector and lint (final pages)
App-screen rules at 1440, 768 and 390 px on the home, explore and destination pages. Reviewed and accepted on purpose, because they come from your reference: soft shadows (lint "shadow", 12 places), the Inter typeface ("font-not-dealt", "default-font"), and the cream or blue palette. Remaining notes: icons in tinted circles, large hero headline, uneven card heights beside a sticky side panel, text of a peeking swipe card near the phone edge. No overflow, contrast, headline-line or tiny-text failure remains.

## Production-mode checks (run by hand on 2 November 2026, earlier build)
Startup refused with empty or short `SECRET_KEY` and with no `DATABASE_URL`; `alembic upgrade head` created the schema; the server started, `/api/health` was ok and security headers were sent. **Not re-run after the photo-column migration was added**; the migration was generated and applied to an empty database during development.

## Defects found and fixed in this redesign
| Found by | Defect | Fix |
|---|---|---|
| Looking at all 84 photographs | Wrong images: a railway-ministry logo (Darjeeling), a locator map (Daman), a satellite image (Kutch), a night stage (Kohima), a resort signboard (Sohra), a wrong article (Mount Abu) | Better search terms, re-fetched and re-checked |
| Reading real output | Weak "calmer alternative to" pairings (hill station to a temple 330 km away); gems 700 km away | Specific shared categories only, 200 km limit; gems within 500 km |
| Looking at the map | A busy lesser-known place drawn as a hidden gem | Only recommended gems get the gem marker; test added |
| Browser test | Map popup 477 px tall and cut off by the map edge | Compact popup, opened after the map finishes moving |
| Browser tests at 390 px | Page scrolled sideways (grid sections and timeline columns would not shrink) | Shrinkable grid columns |
| Phone screenshot | Hero text pushed to the screen edge by the photo credit; header link cut off | Column layout on phones, wrapping header |
| Phone screenshot | "Why we showed you this" showed reasons from an earlier search | Shown only for the same search and date; test added |
| Inspector | Hero headline wrapped to four lines on a phone | Sized to fit two |
| Test authoring | Several of my tests were wrong (CSP-blocked string wait, impossible filter combination, timing races, a no-op assertion) | Corrected; the no-op assertion replaced by a real one |

## Not tested
Load and performance under many users (single measurements only); PostgreSQL; the Docker image build; browsers other than Chrome; real phones; an accessibility audit with assistive technology; a dependency vulnerability scan; offline use; accuracy on real crowd data.
