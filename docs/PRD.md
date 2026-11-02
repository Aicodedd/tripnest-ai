# TripNest AI: Product Requirements Document

Version 2.0 · 2 November 2026 · Scope: crowd prediction and destination recommendation, location-first flow

## 1. Vision and objectives
**Vision:** help every traveller in India answer: *Which popular places are near me? How crowded will they be? When should I visit? Where can I go to escape the crowds?* **Objectives:** O1 predict crowd by date and time of day; O2 recommend nearby popular places and calm hidden gems from those predictions; O3 stay simple, honest about data, and fully working end to end.

## 2. Users and personas
**Asha, family planner (primary):** in Coimbatore, free on a Saturday, wants a calm hill station and the best hour. **Ravi, flexible traveller:** wants the quietest option within a day's travel. Neither wants to register. Authorities and businesses are future users.

## 3. Core user journey
Open the app → allow browser location (asked only after a click, or used at once if already allowed) **or** type a city → see "Discover amazing places around *your city*" → choose a date, interest and time of day → **Popular places near you** with predicted crowds → **Best time to visit** (four-part timeline) → **Escape the Crowds** (hidden gems) → explore the **crowd map** and filter it → open a destination for its prediction, chart and visitor information.

## 4. Functional requirements
| ID | Requirement |
|---|---|
| FR-001 | Home page with branding, search panel (location, date, optional interest) and Explore Destinations; navigation limited to Explore, Crowd Prediction, Hidden Gems and a location indicator. |
| FR-002 | Browser location only on the visitor's click (or when already allowed); denied or unavailable falls back to a typed city; 77 cities with suggestions and aliases. |
| FR-003 | A greeting built from the resolved location (for example "around Coimbatore", or "near X" when between cities); positions outside India get a clear message. |
| FR-004 | Date from today to about 18 months ahead; changing location, date, interest or time of day refreshes all results from the backend. |
| FR-005 | Popular places near the location, nearest first: photo, state, distance, predicted crowd (green, yellow, red), best time, description, View Details. |
| FR-006 | Time-of-day timeline (early morning, morning, afternoon, evening) with the calmest period highlighted. |
| FR-007 | Best time to visit as an hour window, only when the data supports it; otherwise a clear message ("crowds stay high, try another date"). |
| FR-008 | Hidden gems: lesser-known places (catalogue score 0.8 or less) predicted Low or Moderate, with reasons and, where one exists, the busier popular place they are an alternative to. |
| FR-009 | Interactive map (OpenStreetMap): user position, popular and hidden-gem markers (different shapes), crowd colours, popup with photo, level, best time, description and View Details; filters All, Popular, Hidden gems, Low, Moderate, High. |
| FR-010 | Destination page: photo, state, description, prediction for a date and time range, timeline, best time, hourly chart with likely range, 7-day trend, places inside, map, visitor information. |
| FR-011 | Photos stored per destination with credit and licence; a placeholder if a photo fails. |
| FR-012 | Every prediction states type, source, freshness, uncertainty and limitations. |

## 5. Non-functional requirements
**NFR-001** Responsive from phone to desktop with no sideways page scrolling (phone cards swipe). **NFR-002** Results in well under a second once warm (explore API measured about 0.2 s). **NFR-003** Labelled inputs, visible focus, reduced motion respected; no full accessibility audit. **NFR-004** Loading, empty and error states. **NFR-005** Setup reproducible from the README.

## 6. Major modules
Search and location · Explore (popular, best time, hidden gems, map) · Destination page · Crowd prediction service (ML model, batching, cache) · Explore and recommendation service · Location service (static city list) · Catalogue and photo data · Map (OpenStreetMap, Leaflet).

## 7. AI/ML requirements
**AI-001** Supervised regression predicts utilisation per attraction and hour (271 attractions), aggregated per destination. **AI-002** Chronological train / validation / test split, two baselines, results reported as measured: test MAPE **9.38%** against **31.79%** (same hour last week) and **27.45%** (weekday-hour average), on demonstration data. **AI-003** Hidden gems and recommendations consume the predictions; score = 0.40 crowd + 0.25 interest + 0.20 distance + 0.15 season (re-normalised when a factor is missing); popularity is not a factor. **AI-004** No live counts, ticketing or sensor data are invented. **AI-005** Retraining on real counts is one command.

## 8. Security and privacy
**SEC-001** Secrets only in environment variables; production refuses to start without `SECRET_KEY` and `DATABASE_URL`. **SEC-002** Server-side validation of all parameters. **SEC-003** Security headers and a content-security policy. **SEC-004** No accounts or stored personal data; location rounded to about 1 km, kept only for the browser tab session. **SEC-005** External requests limited to OpenStreetMap tiles, the Leaflet library and Wikimedia photos; no key needed.

## 9. Success metrics
Measured now: test MAPE 9.38% against baselines; 101 backend and 24 browser tests pass. **Targets for a pilot (not yet measured):** share of visitors who open a hidden gem; share who choose a calmer time; accuracy once real counts replace the demonstration data.

## 10. Constraints and assumptions
24-hour hackathon, two builders. Crowd history is **simulated**; capacities, hours, fees and the popularity score are assumptions. "Hidden gem" means a lesser-known catalogue score plus a calm prediction, not a verified claim about visitor numbers. Distance is straight-line. Photos and maps need internet.

## 11. Acceptance expectations
The nine-step flow passes in a real browser on desktop, laptop, tablet and phone, including denied location, manual city, date and time changes, map filters and popups. A public URL is verified before deployment is called complete (**not yet deployed**).

## 12. Future scope (not implemented)
Itinerary planning · community and reviews · weather · accounts · authority dashboard · real-time feeds · bookings.
