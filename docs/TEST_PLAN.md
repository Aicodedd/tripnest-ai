# TripNest AI: Test Plan

Version 2.0 · 2 November 2026. Approach: tests are written first for each behaviour, then the code; real browser tests cover the user flow; failures are traced to their cause before fixing.

## 1. Scope
In: location handling, popular places, hidden gems, time-of-day timeline, best-time rules, crowd prediction, recommendation scoring, map data, stored photographs, security headers, configuration, responsive behaviour. Out (not part of the product): itineraries, community, reviews, weather, accounts, admin. Their old tests are kept in `backend/tests/legacy/` and are **not run**.

## 2. Levels and tools
| Level | Tool | Location | What it proves |
|---|---|---|---|
| Unit and service | pytest | `test_crowd_engine.py`, `test_explore.py` (timeline, best window) | levels, simulator, chronological split, model beats baselines, timeline and best-time rules |
| API and integration | pytest + FastAPI test client | `test_core_features.py`, `test_explore.py`, `test_catalog_crowd.py`, `test_map_photos.py`, `test_schema_upgrade.py` | locations, explore, prediction, recommendations, map data, validation, removed modules not exposed, headers, health, schema upgrade |
| Browser end to end | Playwright in real Chrome, own server and database | `e2e/test_journeys.py` | the nine-step flow, denied and allowed location, date and time changes, map filters and popups, stale-explanation rule, photo failure, four screen sizes |
| Design checks | design-taste inspector and lint | reports not committed | layout measurements at 1440, 768 and 390 px |
| Documents | `docs/build_pdfs.py` | `docs/` | MRD is one A4 page, PRD two, PDFs open and have text, every cited test exists |

## 3. Required scenario (nine steps)
| Step | Test |
|---|---|
| 1 Open the app | `test_step1_homepage_explains_the_product_and_offers_a_location_first_search` |
| 2-3 Location permission or manual city, dynamic greeting | `test_denied_location_falls_back_to_a_typed_city`, `test_granted_location_is_used_with_a_dynamic_greeting`, `test_a_location_between_cities_is_described_as_near_one`, `test_steps2to4_typed_city_gives_a_dynamic_greeting_and_popular_places_with_predicted_crowds` |
| 4 Popular places and predicted crowds for the date | `test_steps2to4_typed_city_gives_a_dynamic_greeting_and_popular_places_with_predicted_crowds`, `test_changing_date_time_and_interest_refreshes_the_predictions` |
| 5 Best time to visit | `test_step5_best_time_panel_shows_the_calmest_period_and_updates_per_destination` |
| 6 Hidden gems | `test_step6_hidden_gems_are_lesser_known_calm_and_explained` |
| 7 Interactive map | `test_step7_interactive_map_markers_popup_and_filters`, `test_view_on_map_scrolls_to_the_map_and_opens_that_place` |
| 8-9 Open a destination and its prediction | `test_steps8and9_open_a_destination_and_see_its_prediction`, `test_destination_time_range_and_day_controls_update_the_prediction` |
| Screen sizes | `test_every_screen_size_supports_the_whole_flow` (1440, 1280, 768, 390 px) |

## 4. Entry and exit criteria
Entry: dependencies installed from the pinned files; Chrome present; internet access for the browser tests (Leaflet, map tiles and photographs come from external hosts). Exit: all tests pass with no browser console or server errors; design inspector shows no unexplained failure; documents build with correct page counts; the deployment checklist passes on the live URL (**pending**).

## 5. Not covered (stated honestly)
Load testing; PostgreSQL; the Docker image build; the live deployment; browsers other than Chrome and real phones (phone testing is emulation); an accessibility audit with assistive technology; a dependency vulnerability scan; accuracy on real crowd data; the correctness of every hour, fee and coordinate in the catalogue (indicative public knowledge, positions approximate).
