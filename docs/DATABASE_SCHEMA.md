# TripNest AI: Database Schema

Generated from the SQLAlchemy models (`backend/app/models.py`) on 2 November 2026; migration `70951402a50a_initial_schema`.
SQLite is used for local development and PostgreSQL in production; the same models and Alembic migration serve both.

## Separation of data

| Kind of data | Where it lives | Notes |
|---|---|---|
| Destination and attraction information | Tables `states`, `destinations`, `attractions` | Seeded from `app/data/catalog.py` (public knowledge; indicative hours and fees; **assumed** carrying capacities) |
| Crowd observations (history) | **Not stored in the database.** Generated on demand by `services/crowd_sim.py` (demonstration data) | A real loader returning the same columns (`key, date, hour, count, rain`) replaces it |
| Model and predictions | Trained model file `backend/models/crowd_model.joblib` and `metrics.json`; predictions are computed per request and cached in memory | Keeps predictions reproducible from the model version |

## Tables used by the product

### `states`

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER | primary key |
| `code` | VARCHAR(4) | unique, required |
| `name` | VARCHAR(80) | unique, required |
| `kind` | VARCHAR(10) | required |
| `region` | VARCHAR(20) | required |

### `destinations`

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER | primary key |
| `slug` | VARCHAR(80) | unique, indexed, required |
| `name` | VARCHAR(120) | required |
| `state_id` | INTEGER | FK to `states.id`, required |
| `lat` | FLOAT | required |
| `lon` | FLOAT | required |
| `categories` | JSON | required |
| `budget` | VARCHAR(10) | required |
| `daily_cost` | INTEGER | required |
| `min_days` | INTEGER | required |
| `best_months` | JSON | required |
| `climate` | VARCHAR(20) | required |
| `description` | TEXT | required |
| `how_to_reach` | TEXT | required |
| `facilities` | JSON | required |
| `featured` | BOOLEAN | required |
| `popularity` | FLOAT | required |
| `source` | VARCHAR(40) | required |
| `image_url` | VARCHAR(500) | nullable; Wikimedia photo URL (no file is stored) |
| `image_title` | VARCHAR(200) | nullable |
| `image_credit` | VARCHAR(300) | nullable; photographer or author |
| `image_licence` | VARCHAR(80) | nullable |
| `image_source_page` | VARCHAR(500) | nullable; Commons page |
| `updated_at` | DATETIME | required |

### `attractions`

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER | primary key |
| `slug` | VARCHAR(100) | unique, indexed, required |
| `destination_id` | INTEGER | FK to `destinations.id`, required |
| `name` | VARCHAR(140) | required |
| `category` | VARCHAR(30) | required |
| `lat` | FLOAT | required |
| `lon` | FLOAT | required |
| `capacity` | INTEGER | required |
| `popularity` | FLOAT | required |
| `open_hour` | INTEGER | required |
| `close_hour` | INTEGER | required |
| `fee` | INTEGER | required |
| `sensitive` | BOOLEAN | required |
| `family_friendly` | BOOLEAN | required |
| `elder_friendly` | BOOLEAN | required |
| `covered` | BOOLEAN | required |
| `visit_min` | INTEGER | required |
| `tags` | JSON | required |
| `description` | TEXT | required |
| `source` | VARCHAR(40) | required |

Relationships: a state has many destinations; a destination has many attractions (deleting a destination deletes its attractions).

## Dormant tables (created, not used by the two core features)

These tables belong to modules that were unplugged in the scope change. They are kept so the modules can be restored; no rows are read by the product and none were dropped.

| Table | Belonged to |
|---|---|
| `users` | accounts |
| `favourites` | accounts |
| `itineraries` | itinerary planner |
| `reviews` | reviews |
| `crowd_reports` | traveller reports |
| `listings` | local listings |
| `posts` | community |
| `comments` | community |
| `content_reports` | community moderation |
| `data_sources` | admin console |

## Current development-database contents

| Table | Rows |
|---|---|
| `states` | 36 |
| `destinations` | 84 |
| `attractions` | 271 |

Dormant tables hold only seeded demo rows (for example demonstration reviews); the product does not display them.

The `image_*` columns were added by Alembic migration `8a2f26c2f8b6_destination_photos`; for an older local SQLite file the app adds them at start-up (`db.add_missing_columns`).
