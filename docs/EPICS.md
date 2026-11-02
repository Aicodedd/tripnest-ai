# TripNest AI: Epics

Version 2.0 · 2 November 2026 (location-first redesign). Active scope: **tourist crowd prediction** and **smart destination recommendation**. Removed modules are listed under Future scope and have no epics.

| Epic | Title | Goal | Business requirements | Stories | Status |
|---|---|---|---|---|---|
| EPIC-001 | Tourist Crowd Prediction | A traveller can see how crowded a place will be on a chosen date and time of day, with a four-part timeline, the calmest hour, uncertainty and clear data provenance, from a model evaluated against baselines | BR-001, BR-004 | STORY-001 to STORY-007 | Done, verified by tests |
| EPIC-002 | Smart Destination Recommendation | From their location, a traveller sees popular places nearby and calm, lesser-known hidden gems, chosen with the predicted crowd on their date and their interest, on an interactive map | BR-002, BR-004 | STORY-008 to STORY-015 | Done, except the compare screen (API only) |
| EPIC-003 | Essential Platform Infrastructure and User Experience | A simple, photo-led, responsive product (home, results, details) on a clean catalogue with stored, credited photographs, and clear loading, error and empty states | BR-003 | STORY-016 to STORY-021 | Done, verified by tests |
| EPIC-004 | Testing and Deployment | Automated tests, secure configuration, public deployment and a complete document set | BR-004, BR-005 | STORY-022 to STORY-025 | Partly done: deployment not yet performed |

## Business requirements

| ID | Requirement |
|---|---|
| BR-001 | Help travellers avoid overcrowded destinations by predicting crowd level for a date and time. |
| BR-002 | Recommend destinations that suit the traveller and the predicted crowd, not just popular ones. |
| BR-003 | Be simple to use, with no registration needed for discovery or prediction. |
| BR-004 | Be honest: label demonstration data, show freshness, uncertainty and limitations; never invent live data. |
| BR-005 | Be publicly accessible and reproducible for demonstration. |

## Future scope (not active requirements, not implemented)

Itinerary planner · community, posts and comments · reviews and sentiment analysis · weather dashboard · accounts, profiles and favourites · authority and admin dashboards · local business listings and marketplace · bookings and payments · real-time sensor or ticketing feeds. The code for several of these is kept on disk, unmounted, and is not part of the product.
