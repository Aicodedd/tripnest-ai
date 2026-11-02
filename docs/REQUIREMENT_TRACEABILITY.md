# TripNest AI: Requirement Traceability

Version 2.0 · 2 November 2026. Chain: business requirement → product requirement → epic → story → source files → API → database → tests. Test names are checked automatically against the test files by `docs/build_pdfs.py`.

## 1. Business requirement to epic

| BR | Product requirements | Epic | Stories |
|---|---|---|---|
| BR-001 Predict crowds for a date and time | FR-004, FR-006, FR-007, FR-010, FR-012, AI-001, AI-002 | EPIC-001 | STORY-001 to STORY-007, STORY-020 |
| BR-002 Recommend by predicted crowd and preference | FR-002, FR-003, FR-005, FR-008, FR-009, AI-003 | EPIC-002 | STORY-008 to STORY-015 |
| BR-003 Simple, no registration | FR-001, FR-010, FR-011, NFR-001, NFR-004 | EPIC-003 | STORY-016 to STORY-021 |
| BR-004 Honest about data | FR-012, AI-004, SEC-004 | EPIC-001, EPIC-002 | STORY-006, STORY-007, STORY-009, STORY-011 |
| BR-005 Public and reproducible | NFR-005, SEC-001 to SEC-003 | EPIC-004 | STORY-022 to STORY-025 |

## 2. Story to implementation and tests

Source paths are under `frontend/assets/js/` (front end) and `backend/app/` (back end). Test names are listed in `USER_STORIES.md` and checked by `docs/build_pdfs.py`.

| Story | Source files | API | Database / data | Test files |
|---|---|---|---|---|
| STORY-001 | `destination.js`, `explore.js` | `/api/destinations/{slug}/prediction` | `destinations`, `attractions` | `e2e/test_journeys.py`, `test_core_features.py` |
| STORY-002 | `destination.js`, `services/prediction.py` | same | same | `test_core_features.py`, `e2e` |
| STORY-003 | `destination.js`, `core.js` chart | same | same | `test_core_features.py` |
| STORY-004 | `ui.js` timeline, `explore.js`, `prediction.timeline/best_window` | `/api/explore`, prediction | same | `test_explore.py`, `e2e` |
| STORY-005 | `destination.js`, `prediction.py` | prediction | same | `test_core_features.py`, `e2e` |
| STORY-006 | `prediction.provenance` | prediction, explore | model file | `test_core_features.py`, `e2e` |
| STORY-007 | `services/forecast.py`, `crowd_sim.py`, `scripts/train_model.py` | `/api/model` | `backend/models` | `test_crowd_engine.py`, `test_core_features.py` |
| STORY-008 | `landing.js`, `search.js`, `data/cities.py` | `/api/locations/*` | static city list | `test_core_features.py`, `e2e` |
| STORY-009 | `search.js`, `landing.js` | `/api/locations/nearest` | static city list | `test_explore.py`, `e2e` |
| STORY-010 | `explore.js`, `services/explore.py` | `/api/explore` | `destinations`, `attractions` | `test_explore.py`, `e2e` |
| STORY-011 | `explore.js`, `services/explore.py` | `/api/explore` | same | `test_explore.py`, `e2e` |
| STORY-012 | `explore.js` (refine bar) | `/api/explore` | same | `test_explore.py`, `e2e` |
| STORY-013 | `explore.js`, `ui.js`, `routers/catalog.py` | `/api/explore` (`map`), `/api/crowd/map` | same | `test_explore.py`, `test_map_photos.py`, `e2e` |
| STORY-014 | `services/recommender.py` | `/api/recommendations` | same | `test_core_features.py` |
| STORY-015 | none in the UI | `/api/crowd/compare` | same | `test_core_features.py` |
| STORY-016 | `landing.js`, `main.js`, `styles.css` | none | none | `e2e` |
| STORY-017 | `destination.js`, `ui.js` | prediction | same | `e2e` |
| STORY-018 | `styles.css`, all pages | none | none | `e2e` |
| STORY-019 | `ui.js` (photo fallback), `main.js` | none | none | `e2e` |
| STORY-020 | `data/catalog*.py`, `scripts/fetch_images.py`, `models.py`, `services/seed.py`, migration `destination photos` | `/api/states`, `/api/destinations` | `states`, `destinations` (photo columns), `attractions` | `test_catalog_crowd.py`, `test_explore.py`, `test_schema_upgrade.py` |
| STORY-021 | `main.js` | none | none | `e2e` |
| STORY-022 | `backend/tests`, `e2e` | none | none | all (`TEST_RESULTS.md`) |
| STORY-023 | `config.py`, `main.py` | `/api/health` | none | `test_core_features.py` |
| STORY-024 | `Dockerfile`, `render.yaml` | `/api/health` | PostgreSQL (production) | live check 2 Nov 2026: health, API and 24 browser tests against https://tripnest-ai-1rug.onrender.com |
| STORY-025 | `docs/*` | none | none | `docs/build_pdfs.py` (page counts, text, test references) |

## 3. Non-functional, AI and security requirements

| ID | Requirement | Implemented in | Verified by |
|---|---|---|---|
| NFR-001 | Responsive, no sideways scroll | `styles.css` | `test_every_screen_size_supports_the_whole_flow` |
| NFR-002 | Fast results | batched forecasts, cache (`runtime.py`) | measured manually: recommendations 0.02–0.05 s warm (no automated performance test) |
| NFR-003 | Accessibility basics | labels, focus styles, reduced motion | design inspector; no assistive-technology audit |
| NFR-004 | Loading, empty, error states | all pages | STORY-017 tests |
| NFR-005 | Reproducible setup | `README.md`, pinned requirements | STORY-019 |
| AI-001, AI-002 | Chronological split; baselines | `forecast.py` | `test_training_uses_chronological_train_validation_test_split`, `test_model_beats_both_baselines_on_held_out_test_period` |
| AI-003 | Recommendation uses predictions | `recommender.py` | `test_busier_dates_lower_the_crowd_score_for_the_same_destination` |
| AI-004 | No invented live data | provenance labels | `test_prediction_states_what_it_is_and_what_it_cannot_do` |
| AI-005 | Real data can be loaded later | `crowd_sim.counts` contract, `train_model.py` | documented; not exercised with real data |
| SEC-001 | Secrets in environment | `config.py` | production start refuses without secrets (manually executed, see TEST_RESULTS) |
| SEC-002 | Input validation | `discover.py` | `test_recommendation_input_validation`, `test_prediction_defaults_and_validation` |
| SEC-003 | Security headers | `main.py` | `test_security_headers_present` |
| SEC-004 | Location privacy | `home.js` | `test_granted_location_is_used_with_a_dynamic_greeting` |
