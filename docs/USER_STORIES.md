# TripNest AI: User Stories

Version 2.0 · 2 November 2026 (location-first redesign; **supersedes the story numbering of version 1.0**). Priority: P1 must have, P2 should have. **Definition of Done (all stories):** acceptance criteria met; tests written and passing (`pytest`, `sh e2e/run.sh`); no console or server errors in the browser tests; API and database documents updated if affected; traceability and status updated. Status reflects what was actually run.

## EPIC-001: Tourist Crowd Prediction

### STORY-001: Open a place's prediction
**As a** traveller **I want to** open any place from a card, a map marker or a link **so that** I see its predicted crowd for my date. P1. FR-010.
- *Given* a place card or map popup, *when* I press View Details, *then* I reach that place's page with my date carried over. *Given* an unknown place, *then* I see "Destination not found".

**Frontend:** `destination.js`, `explore.js`. **Backend:** `GET /api/destinations/{slug}/prediction`. **Tests:** `test_steps8and9_open_a_destination_and_see_its_prediction`, `test_unknown_destination_page_is_a_clear_empty_state`, `test_prediction_for_a_date_and_time_range`. **Status:** Done. *Not in this flow:* a typed destination search box (see future scope).

### STORY-002: Predicted crowd for a date and time range
P1. FR-004, FR-010. *Given* Goa on Saturday 26 December 9 AM to 5 PM, *then* I see a green, yellow or red level for the busiest hour, the hour and the number of people. *Given* a start later than the end, *then* "The start time must not be after the end time." *Given* a range when it is closed, *then* "Closed in this time range".
**Frontend:** `destination.js`. **Backend:** `services/prediction.py`. **Tests:** `test_prediction_for_a_date_and_time_range`, `test_weekend_is_busier_than_a_weekday_for_the_same_hours`, `test_a_range_outside_opening_hours_gives_a_clear_answer_not_a_crash`, `test_destination_time_range_and_day_controls_update_the_prediction`, `test_prediction_defaults_and_validation`. **Status:** Done.

### STORY-003: Estimated visitors and a likely range
P2. *Then* each prediction shows about how many people with an 80% likely range, labelled demonstration data. **Tests:** `test_prediction_for_a_date_and_time_range`. **Status:** Done.

### STORY-004: Time-of-day timeline and best time to visit
P1. FR-006, FR-007.
- *Given* a place and date, *then* four slots (early morning 5–8, morning 8–12, afternoon 12–4, evening 4–8) each show a level, and the calmest slot is highlighted.
- *Then* the best time is an hour window ("7:00 AM – 8:00 AM") with "Lower crowd levels are predicted during this period."
- *Given* crowds stay High all day, *then* no time is recommended and the message says to try another date. *Given* fewer than three open hours, *then* "Not enough opening hours".

**Frontend:** timeline on cards, best-time panel, destination page. **Backend:** `prediction.timeline`, `prediction.best_window`. **Tests:** `test_timeline_has_four_slots_and_flags_the_calmest_available_one`, `test_slots_with_no_open_hours_are_unavailable_and_never_best`, `test_best_window_is_the_calmest_hour_with_a_plain_message`, `test_no_time_is_recommended_when_crowds_stay_high_all_day`, `test_no_time_is_recommended_without_enough_opening_hours`, `test_step5_best_time_panel_shows_the_calmest_period_and_updates_per_destination`. **Status:** Done.

### STORY-005: The next seven days
P2. *Then* seven day tiles show each day's busiest level and quietest hour; selecting a day reloads that date. **Tests:** `test_prediction_for_a_date_and_time_range`, `test_destination_time_range_and_day_controls_update_the_prediction`. **Status:** Done.

### STORY-006: Provenance, freshness, uncertainty and limitations
P1. FR-012, AI-004. *Then* every prediction says ML prediction, demonstration data, not live; when made; model training date; how uncertainty is measured; at least three limitations. **Tests:** `test_prediction_states_what_it_is_and_what_it_cannot_do`, `test_steps8and9_open_a_destination_and_see_its_prediction`. **Status:** Done.

### STORY-007: Train and evaluate the model against baselines
P1. AI-001, AI-002, AI-005. *Then* chronological train / validation / test split, hyper-parameters chosen on validation, test scored once, two baselines, the model beats both, metrics shown unchanged in the app; retraining is one command. **Backend:** `services/forecast.py`, `scripts/train_model.py`. **Tests:** `test_training_uses_chronological_train_validation_test_split`, `test_model_beats_both_baselines_on_held_out_test_period`, `test_model_round_trips_through_disk`, `test_model_card_reports_test_metrics_and_baselines`. **Status:** Done (demonstration data only).

## EPIC-002: Smart Destination Recommendation

### STORY-008: Choose a starting city
P1. FR-002. *Given* "Bangalore", *then* Bengaluru is used. *Given* "Atlantis", *then* a message asks for a nearby major city. *Given* nothing typed, *then* "Enter your city, or use your current location." **Frontend:** `landing.js`, `search.js`. **Backend:** `/api/locations/*`, `data/cities.py` (77 cities). **Tests:** `test_manual_location_text_resolves_with_aliases`, `test_unknown_manual_location_gets_a_helpful_error`, `test_city_search_finds_chennai_first_with_state_and_coordinates`, `test_empty_unknown_and_foreign_locations_are_explained`. **Status:** Done.

### STORY-009: Use my location only with permission, and a dynamic greeting
P1. FR-002, FR-003, SEC-004.
- *Given* no permission, *then* the browser is never asked on load; pressing "Use my location" asks, and a refusal shows "type your city instead".
- *Given* permission already granted, *then* the location is used at once and the greeting reads "Discover amazing places around Coimbatore."; between cities it reads "near Coimbatore"; outside India a clear message is shown.
- Position is rounded to about 1 km.

**Backend:** `GET /api/locations/nearest`. **Tests:** `test_denied_location_falls_back_to_a_typed_city`, `test_granted_location_is_used_with_a_dynamic_greeting`, `test_a_location_between_cities_is_described_as_near_one`, `test_nearest_city_names_the_resolved_location`, `test_a_position_between_cities_is_described_as_near_one`, `test_a_position_outside_india_is_not_covered`, `test_nearest_city_validates_coordinates`. **Status:** Done.

### STORY-010: Popular places near me
P1. FR-005. *Then* the nearest well-known places (catalogue score 0.9 or more), nearest first, each with photo, state, distance, predicted crowd, best time, description and View Details; fewer than three within 800 km says "nearest in our catalogue". **Backend:** `services/explore.py`, `GET /api/explore`. **Tests:** `test_explore_returns_popular_places_and_hidden_gems_around_a_location`, `test_every_card_has_photo_crowd_colour_timeline_and_best_time`, `test_remote_origin_expands_to_the_nearest_places_and_says_so`, `test_origin_outside_india_returns_a_clear_message_not_results`, `test_explore_validation`, `test_steps2to4_typed_city_gives_a_dynamic_greeting_and_popular_places_with_predicted_crowds`. **Status:** Done.

### STORY-011: Hidden gems ("Escape the Crowds")
P1. FR-008. *Then* only lesser-known places (score 0.8 or less) within 500 km that are predicted Low or Moderate; each says why it was recommended and shows the lesser-known reasoning; where one exists, "A calmer alternative to X". Busy lesser-known places are never labelled hidden gems. **Tests:** `test_hidden_gems_are_justified_calmer_and_explained`, `test_a_busy_lesser_known_place_is_never_drawn_as_a_hidden_gem_on_the_map`, `test_step6_hidden_gems_are_lesser_known_calm_and_explained`. **Status:** Done. *Caveat:* "lesser-known" is a catalogue assumption, not a visitor count.

### STORY-012: Date, interest and time of day refresh the results
P1. FR-004. *When* I change any of them, *then* the backend recomputes and the page updates; popular places matching the interest come first. **Tests:** `test_time_slot_changes_the_crowd_reading`, `test_changing_the_date_changes_the_predictions`, `test_interest_puts_matching_places_first`, `test_changing_date_time_and_interest_refreshes_the_predictions`, `test_a_busy_date_changes_what_the_best_time_panel_recommends`. **Status:** Done.

### STORY-013: Interactive crowd map
P1. FR-009. *Then* OpenStreetMap with my position, circles for popular places and diamonds for hidden gems, green, yellow and red by predicted crowd; popup with photo, level, best time, description and View Details; filters All, Popular, Hidden gems, Low, Moderate, High; "View on map" on a card opens that place. **Tests:** `test_map_points_cover_both_groups_with_colours_and_distances`, `test_crowd_map_returns_every_attraction_with_level_and_heat`, `test_step7_interactive_map_markers_popup_and_filters`, `test_view_on_map_scrolls_to_the_map_and_opens_that_place`. **Status:** Done.

### STORY-014: Explained scoring
P2. *Then* hidden gems and the recommendation API use crowd 0.40, interest 0.25, distance 0.20, season 0.15 (re-normalised when a factor is missing); popularity is not a factor; the card shows reasons. **Tests:** `test_score_is_the_weighted_sum_of_the_shown_factors`, `test_popularity_is_not_a_scoring_factor`. **Status:** Done for the API and reasons; the per-factor breakdown is not shown in the interface.

### STORY-015: Compare destinations
P2. **Status:** API only (`GET /api/crowd/compare`, `test_compare_two_to_four_destinations_with_levels`). The comparison screen was removed in the redesign.

## EPIC-003: Essential Platform Infrastructure and User Experience

### STORY-016: A simple, photo-led home page
P1. FR-001. *Then* hero photograph with credit, the headline, supporting text, a search panel (location, date, interest, Explore Destinations), a navigation of Explore, Crowd Prediction, Hidden Gems and a location indicator, and no sign-in. **Tests:** `test_step1_homepage_explains_the_product_and_offers_a_location_first_search`. **Status:** Done.

### STORY-017: Destination details page
P1. FR-010. *Then* photo, state, description, prediction, timeline, best time, chart, 7-day tiles, places inside, map, visitor information, "Why we showed you this" only for the search and date that produced it. **Tests:** `test_steps8and9_open_a_destination_and_see_its_prediction`, `test_the_explanation_belongs_to_the_search_that_produced_it`. **Status:** Done.

### STORY-018: Responsive on every screen
P1. NFR-001. *Then* the whole flow works at 1440, 1280, 768 and 390 px with no sideways page scrolling; on phones the card rows swipe. **Tests:** `test_every_screen_size_supports_the_whole_flow`. **Status:** Done (emulation, Chrome only).

### STORY-019: Loading, empty, error and photo-failure states
P1. NFR-004. **Tests:** `test_photos_that_fail_to_load_become_clean_placeholders`, `test_leaving_a_page_mid_load_causes_no_script_errors`, `test_typed_inputs_never_appear_in_the_address_bar`. **Status:** Done.

### STORY-020: Catalogue and stored photographs
P1. FR-011. *Then* all 36 states and union territories have destinations (84 in total, 271 attractions); each destination has one stored Wikimedia photograph with credit and licence. **Tests:** `test_all_36_states_and_uts_are_present`, `test_destination_card_carries_the_stored_photo_and_credit`, `test_catalogue_now_has_many_lesser_known_destinations`, `test_new_destinations_get_forecasts_without_retraining`, `test_missing_nullable_columns_are_added_and_rows_survive`. **Status:** Done.

### STORY-021: Header navigation to sections
P2. *Then* Explore, Crowd Prediction and Hidden Gems open the last search at that section; with no search they ask to choose a location first. **Tests:** `test_header_links_open_the_right_section_of_the_last_search`. **Status:** Done.

## EPIC-004: Testing and Deployment

### STORY-022: Automated tests
P1. **Evidence:** `TEST_RESULTS.md` (101 backend, 24 browser). **Status:** Done.

### STORY-023: Secure configuration and health
P1. SEC-001 to SEC-003. **Tests:** `test_health_reports_database_and_model`, `test_security_headers_present`, `test_removed_modules_are_not_exposed`, `test_recommendation_input_validation`. **Status:** Done.

### STORY-024: Public deployment
P1. **Status:** **Done.** Live on Render free plan at https://tripnest-ai-1rug.onrender.com, verified 2 November 2026 (health, API, 24 browser tests).

### STORY-025: Documentation
P1. **Status:** Done (see `IMPLEMENTATION_STATUS.md`).
