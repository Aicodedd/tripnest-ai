# TripNest AI: Market Requirements Document

Version 2.0 · 2 November 2026 · Scope: two core features, location-first flow · *Discover Smarter. Travel Better. Explore Beyond the Crowds.*

## 1. Project overview
TripNest AI is a simple web application for travellers in India. From the traveller's location and travel date it shows **popular places nearby with their predicted crowd**, **the best time to visit each**, and **lesser-known "hidden gems" that are predicted to be calm**, all on an interactive map. It covers all 36 states and union territories (84 destinations, 271 attractions).

## 2. Market problem
Visitors cluster at the same famous places on weekends, holidays and in peak seasons, without reliable information about how crowded a place will be or which comparable place would be calmer. The result is queues, congestion, pressure on fragile sites and a poorer visit, while nearby lesser-known destinations stay under-used. *No formal market study was run; the problem comes from the hackathon brief (PS 12).*

## 3. Target users and needs
| User | Need |
|---|---|
| Domestic tourists, families and groups (primary) | Know the crowd before travelling; pick a calmer hour, date or alternative, with a plain explanation |
| Flexible weekend and holiday travellers | Places near them, with when to go and a quieter option |
| Tourism authorities and local businesses (secondary) | Spread visitors more evenly. They benefit indirectly and are **not** served by this release |

## 4. Market opportunity
Domestic travel in India is large and seasonal, with crowd pressure concentrated in time and place. Moving some visitors to a quieter hour or a comparable destination helps visitors, strained sites and quieter locations. This is **qualitative**: no market size, revenue or adoption figure is claimed.

## 5. Proposed solution
1. **Tourist crowd prediction.** For a place, date and time of day: the predicted level (green Low, yellow Moderate, red High), a four-part timeline from early morning to evening, the calmest hour, and a 7-day trend.
2. **Smart destination recommendation.** From a typed city or the browser's location (only with permission): popular places nearby, then hidden gems, meaning lesser-known places that are predicted to be calm, each with a photo, reason, distance and best time, plus an interactive map with filters.

Every result is labelled an ML prediction trained on **demonstration data** (no verified visitor counts exist), with its freshness, uncertainty and limitations.

## 6. Unique value proposition
*Discover popular places, know the best time to visit and find hidden gems beyond the crowds.* Hidden gems are justified (a lesser-known catalogue score **and** a calm predicted crowd on the traveller's date), never just "less popular", and every place is shown with an honest, labelled prediction.

## 7. Business and user benefits
**Travellers:** fewer queues and better-timed visits, with no registration. **Project:** a tested end-to-end product with a reproducible ML pipeline, measured against baselines (9.4% average error versus 31.8% for repeating last week, on demonstration data).

## 8. Project objectives
1. Predict crowd levels by date and time of day for every catalogued destination, with uncertainty and provenance.
2. Recommend nearby popular places and calm hidden gems using those predictions, with clear reasons.
3. Keep the journey simple: one search, one results page, one details page, usable on phone, tablet and desktop.
4. Be honest about data (never show demonstration data as live) and ship a deployable, tested, documented product.

**Future scope only:** itineraries, community, reviews, weather, accounts, bookings.
