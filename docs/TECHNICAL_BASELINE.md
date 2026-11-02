# Technical Baseline (CrowdWise prototype)

> **Historical document.** Written before the scope change of 2 November 2026 (it describes the earlier, larger plan). The current scope is in `PRD.md` and `SCOPE_CHANGE_AUDIT.md`. Kept unchanged below.


Measured on 1 November 2026, macOS (Darwin 27), on the code in `~/Documents/crowdwise`.

## Stack

| Layer | Technology | Notes |
|---|---|---|
| Language | Python 3.14.7 | Installs and runs on 3.14 (verified) |
| Web framework | Starlette 1.10 + uvicorn 0.54 | Lifespan uses a deprecated async-generator form (warning at startup) |
| ML | scikit-learn 1.9 `HistGradientBoostingRegressor`; XGBoost optional via `CROWDWISE_MODEL=xgboost` | Target `log(util + 0.02)`; 13 features |
| Data | pandas 3.1, NumPy 2.5 | |
| Database | SQLite (`crowdwise.db`, raw `sqlite3`, schema created at startup, no migrations) | Path from `CROWDWISE_DB` |
| Front end | Vanilla JS (`static/app.js`, 508 lines), CSS (137 lines), no build step | Charts and map are hand-made SVG |
| Tests | None | |
| Packaging / deploy | `requirements.txt` (unpinned). No Docker, no Procfile. | |
| VCS | None (not a git repo) | |

## Source size

| File | Lines | Responsibility |
|---|---|---|
| `app.py` | 330 | Routes, error mapping, admin PIN guard, static serving |
| `engine.py` | 776 | Crowd levels, recommender, itinerary, tokens, alerts, simulation |
| `sim.py` | 215 | Synthetic attractions, weather, holidays, demand, feature frame |
| `model.py` | 172 | Training, evaluation vs baseline, persistence |
| `sentiment.py` | 174 | Lexicon + aspect sentiment, seed reviews |
| `db.py` | 124 | SQLite store |
| `static/` | 682 | UI |

## Database (current contents of `crowdwise.db`)

| Table | Columns | Rows |
|---|---|---|
| `reports` | id, attraction_id, at, crowd, issue, text | 0 |
| `reviews` | id, attraction_id, at, text, rating, label, score, aspects (JSON), source | 192 (all `seed`) |
| `tokens` | code (PK), attraction_id, slot_start, party, name, status, created_at, redeemed_at | 0 |
| `events` | id, type, attraction_id, alt_id, at | 0 |

There are no foreign keys, no user table and no indexes beyond the primary keys. Attractions live in Python code (`sim.ATTRACTIONS`), not in the database.

**There is no real user data in the database. It holds only seeded reviews.** It will still be left untouched, and TripNest AI will use its own database.

## API (20 routes)

Public: `GET /api/config`, `GET /api/state`, `GET /api/attractions/{aid}`, `POST /api/recommend`, `POST /api/itinerary`, `GET /api/tokens/slots`, `POST /api/tokens`, `GET /api/tokens/{code}`, `POST /api/tokens/{code}/cancel`, `POST /api/reports`, `POST /api/reviews`, `POST /api/events`, `GET /api/model`.
Admin (`x-admin-pin` header): `POST /api/admin/login`, `GET /api/admin/overview`, `/themes`, `/tokens`, `/simulate`, `POST /api/admin/redeem/{code}`.
All routes accept `?at=YYYY-MM-DDTHH:MM` to set the demo clock.

## ML baseline (simulated data, `models/metrics.json`)

| Metric (14-day chronological holdout, 1,792 rows) | Model | Baseline (mean by attraction × weekday × hour) |
|---|---|---|
| MAPE (hours with ≥10 visitors) | 8.32% | 21.33% |
| WAPE | 9.11% | 20.93% |
| MAE (visitors) | 16.7 | 38.4 |
| R² | 0.971 | 0.797 |

Training: 180 days × 12 attractions, 21,248 rows, 2.7 s. There is no separate validation split (train → holdout only), and hyper-parameters are hand-set. Top features: attraction, hour, open fraction, weekday, rain, holiday.

## Environment variables in use

| Variable | Default | Secret? |
|---|---|---|
| `CROWDWISE_ADMIN_PIN` | `admin123` (**insecure default, printed in logs**) | Yes |
| `CROWDWISE_TZ` | `Asia/Kolkata` | No |
| `CROWDWISE_DB` | `./crowdwise.db` | No |
| `CROWDWISE_MODEL` | (sklearn) | No |
| `HOST`, `PORT` | `0.0.0.0`, `8000` | No |

## External services in use

None. Everything (weather, counts, map) is simulated or drawn locally, so the app works offline.

## Local tooling available for the build

| Tool | Available | Use |
|---|---|---|
| Python 3.14, pip, venv | Yes | Backend |
| Node 26 / npm | Yes | Playwright E2E, optional front-end tooling |
| Google Chrome | Yes | Headless Markdown→PDF rendering, browser tests |
| git | Yes | Version control |
| Homebrew | Yes | Optional installs |
| pandoc, weasyprint, wkhtmltopdf | No | Not needed (Chrome prints PDFs) |
| Docker | No | Dockerfile can still be written and is built by the host (Render) |
| psql / local Postgres | No | SQLite locally; Postgres only in production |
| gh (GitHub CLI) | No | Push via plain git + HTTPS, or the team pushes |
