# TripNest AI — Project Audit

> **Historical document.** Written before the scope change of 2 November 2026 (it describes the earlier, larger plan). The current scope is in `PRD.md` and `SCOPE_CHANGE_AUDIT.md`. Kept unchanged below.


| | |
|---|---|
| Audit date | 1 November 2026 |
| Scope | Phase 1 of the TripNest AI master instruction (existing-project audit) |
| Auditor | Claude (Claude Code), with the project team |
| Status | **Awaiting team approval before any code is changed** |

Companion documents: [EXISTING_FEATURES.md](EXISTING_FEATURES.md), [TECHNICAL_BASELINE.md](TECHNICAL_BASELINE.md), [API_REQUIREMENTS.md](API_REQUIREMENTS.md).

---

## 1. Headline finding: there is no TripNest repository on this machine

The master instruction says to transform "my existing TripNest project". We searched for it and did not find it:

| Search | Result |
|---|---|
| Working folder `~/Documents/hackathon 2.0` | Only `claude-skill-uploads/` (7 skill zips). Not a git repository. |
| File/folder names containing `tripnest`, `trip-nest`, `trip_nest` under the home folder (depth 6, excluding Library) | None |
| Text search for "tripnest" in `~/Documents`, `~/Desktop`, `~/Downloads` | None |
| GitHub CLI (`gh repo list`) | `gh` is not installed, so remote repositories could not be checked |

The only codebase related to the problem statement (PS 12, tourist crowd prediction) is **`~/Documents/crowdwise`**, a working CrowdWise prototype built on 31 October 2026. Other folders (`~/Documents/project`, `~/Documents/sample`) hold ParkLot AI documents for a different hackathon and contain no TripNest code.

**Consequence:** This audit describes `crowdwise`. Unless the team supplies the TripNest source (for example a GitHub URL or a zip), TripNest AI has to be built on top of `crowdwise`. Features the master instruction assumes already exist (accounts, destination discovery, itineraries, community) have to be built new.

## 2. What exists today (summary)

`crowdwise` is a single-service Python web app. It has about 2,470 lines of source code across 6 Python modules and a dependency-free HTML/JS front end. Full detail is in [TECHNICAL_BASELINE.md](TECHNICAL_BASELINE.md).

```
Browser (vanilla JS SPA, SVG charts and map)
        │  JSON over HTTP, same origin
        ▼
Starlette + uvicorn (app.py) ── 20 routes; admin routes require the x-admin-pin header
        │
        ├── engine.py     crowd levels, recommender, itinerary, tokens, alerts, what-if simulation
        ├── model.py      gradient-boosted crowd forecaster (scikit-learn; XGBoost optional)
        ├── sentiment.py  lexicon + aspect sentiment analysis
        ├── sim.py        SIMULATED world: 12 fictional attractions, weather, holidays, visitor counts
        └── db.py         SQLite: reports, reviews, tokens, events
```

### Verified in this audit (actually executed)

We installed the dependencies into a throwaway virtualenv and ran the app against a **copy** of `crowdwise.db`, on port 8765:

| Check | Result |
|---|---|
| Server start, cached model load | OK (model trained 2026-10-31 loaded from `models/`) |
| `GET /api/config`, `/api/state`, `/api/attractions/silver-falls`, `/api/model` | All HTTP 200 |
| `POST /api/recommend` (waterfall, kids, Silver Cascade Falls, Sat 7 Nov 4 PM) | Predicts 110% full, P(exceed) 0.975, offers a 6 PM slot and quieter alternatives |
| `GET /api/admin/overview` without the PIN | HTTP 401 (correctly refused) |
| Home page in a real browser | Renders: weather card, interest chips, recommendations, live crowd list, tab bar |
| Model holdout accuracy (from `models/metrics.json`) | MAPE 8.3% vs 21.3% for a weekday-hour mean baseline, **on simulated data** |

### Not verified

- Every front-end flow beyond the home page (map, plan, tokens, report, admin) was not clicked through in this audit.
- XGBoost backend (optional, not installed).
- Behaviour under concurrent users or after a redeploy.

## 3. Gap analysis against the TripNest AI master instruction

Legend: ✅ exists and works · 🟡 partly exists / needs rework · ❌ missing

| Master-instruction area | Status | Notes |
|---|---|---|
| A. Landing page | ❌ | The app opens straight into the tourist tool. There is no marketing or landing page and no TripNest identity. |
| B. Auth & user profiles | ❌ | No user accounts. Admin uses a single shared PIN (default `admin123`). No password hashing, sessions, profiles, preferences or favourites. |
| C. Destination discovery (all India) | ❌ | One fictional zone ("Hill Valley Pilot Zone") with 12 fictional attractions hard-coded in `sim.py`. No states, destinations, search or filters. |
| D. Crowd intelligence | ✅ / 🟡 | Strong: hourly forecast, levels, peak and best times, P(exceed capacity), baseline comparison, provenance note. Needs a Destination→Attraction hierarchy, a chronological train/**validation**/test split (today it is train/holdout only), and a per-response data-provenance label. |
| E. Personalised recommendations | 🟡 | A weighted scorer with explanations exists for attractions within one zone. It needs budget, trip duration, distance and travel-period inputs, and should work across destinations. |
| F. Itinerary planner | 🟡 | A single-day, single-zone timed plan exists. It is missing multi-day plans, multiple destinations, save/edit/regenerate, and per-user storage. |
| G. Interactive map | 🟡 | Hand-drawn SVG from coordinates. Needs Leaflet + OpenStreetMap. |
| H. Weather | 🟡 | **Simulated** weather only. Needs a real provider (Open-Meteo, no key) with an "unavailable" state. |
| I. Reviews & sentiment | ✅ / 🟡 | Review submission, lexicon sentiment and aspect themes work. All 192 stored reviews are `source=seed` (synthetic) and must be labelled as demo data. Reviews are not tied to users. |
| J. Local travel info | ❌ | Only food-street and market entries inside the simulation. |
| K. Community | ❌ | None. |
| L. Admin dashboard | 🟡 | Rich crowd-operations console (alerts, heatmap, what-if, gate scanner, themes, model accuracy). Missing CRUD for destinations, attractions, users, reviews and reported content, plus role-based access. |
| Digital queue tokens (from PS 12) | ✅ | Slot capacity, booking, cancel and admin redeem all exist. Not in the master list, but worth keeping as a differentiator. |
| Tests | ❌ | No test files and no test framework. |
| API docs | 🟡 | README table only. No OpenAPI / Swagger. |
| Logging & error handling | 🟡 | Structured JSON errors per route. Logging is `print` statements. |
| Security | ❌ | Default admin PIN printed to the console at startup. No CORS policy (not needed while served from one origin). No rate limiting. No `.env.example`. |
| Deployment | ❌ | No Dockerfile, Procfile, `render.yaml`, or `.env.example`. SQLite file on local disk. |
| Version control | ❌ | Not a git repository. `.DS_Store`, `__pycache__`, two virtualenvs (`venv/`, `source/`), the database and the 1.7 MB model file sit alongside the code. |
| Reproducibility | 🟡 | `requirements.txt` exists but is unpinned, and no environment on this machine currently has the packages installed. Installs cleanly on Python 3.14 (verified). |

## 4. Technical risks

| # | Risk | Impact | Mitigation |
|---|---|---|---|
| R1 | **24 hours, 2 active builders** against a scope of 12 feature areas, about 20 documents with PDFs, testing and deployment | Unfinished features or unverified claims at judging | Tiered plan (section 6). Every tier ends with a working, deployed app. |
| R2 | TripNest source missing | Rework if it turns up mid-build | Decide the base now. If TripNest appears later, port its unique features as stories. |
| R3 | Judges include a cybersecurity director | Shared PIN, default secrets and no tests will be noticed | Real auth (hashed passwords, JWT, roles), a secrets checklist, input validation, rate-limited login, security section in docs |
| R4 | No verified crowd data exists for Indian attractions | Fabrication if mislabelled | Every crowd number carries `provenance: "demonstration-model"`. The pipeline accepts a CSV of real counts later. |
| R5 | Synthetic data makes the model look better than it is | Credibility with the AI-strategy judge | Report the baseline beside the model, use a chronological validation split, and state the limitation plainly in the UI and docs |
| R6 | SQLite on free hosting is wiped on redeploy | Data loss during judging | Managed Postgres in production; SQLite for local development only |
| R7 | Free tiers sleep or change terms | First request slow (≈30–60 s) during the demo | Warm the URL before demoing; document it; costs to be checked at sign-up |
| R8 | Paid LLM API | Cost, and hallucinated facts in itineraries | Itinerary built by the deterministic engine; LLM only as optional narrative behind a key, with output validated against the catalogue. **Needs approval.** |
| R9 | OpenStreetMap tile and Nominatim usage policies | Blocking or policy breach | Attribution, low traffic, pre-geocoded seed data (no live geocoding at runtime) |
| R10 | Python 3.14 / pandas 3 / scikit-learn 1.9 are very new | Library incompatibilities on the host | Pin versions; deploy with Docker on a known Python image |
| R11 | Starlette lifespan deprecation warning | Breaks on a future Starlette | Fixed by the FastAPI migration (`asynccontextmanager`) |

## 5. Data availability and limitations

| Data | Real source available? | Plan |
|---|---|---|
| Indian states / UTs (36) | Yes, public knowledge | Seeded |
| Destinations and attractions (names, coordinates, categories, typical hours, fees) | Public information, but no single verified open dataset | Seed about 50 well-known destinations, each with several attractions, from public knowledge. Mark as "catalogue data, verify before travel". Fees and hours shown as indicative. |
| Hourly visitor counts | **No** verified public source | Simulated with the existing `sim.py` approach, generalised to every attraction. Labelled "Demonstration data — model-predicted". |
| Weather | Yes: Open-Meteo forecast API, no key | Live, with "unavailable" fallback |
| Holidays | Approximate | National holiday list. State festivals marked approximate. |
| Reviews | No real reviews yet | Seed reviews labelled "demo". Users' reviews labelled "traveller review". |
| Routing / travel time | No free production-grade router without a key | Straight-line distance with a speed assumption, labelled "estimate". OSRM/ORS optional later. |

## 6. Proposed implementation plan (for approval)

**Base:** build TripNest AI in a new git repository `~/Documents/hackathon 2.0/tripnest-ai/`, starting from a copy of `crowdwise`. The original `crowdwise` folder and its database stay untouched as a backup.

| Tier | Contents | Approx. effort |
|---|---|---|
| **T0 Foundation** | git init, `.gitignore`, pinned requirements, `.env.example`, config module with required-variable checks, Starlette→**FastAPI** (OpenAPI at `/docs`), SQLAlchemy models + Alembic migrations (SQLite locally, Postgres in prod), pytest harness, Dockerfile | 3 h |
| **T1 Core journey** (judging-critical) | Auth (register/login/logout, bcrypt, JWT, roles); India catalogue (state → destination → attraction) with search and filters; crowd intelligence generalised to all attractions with provenance labels; recommendations (budget, duration, group, interests, distance, crowd); multi-day itinerary save/edit/regenerate; Leaflet map; Open-Meteo weather; reviews + sentiment; admin CRUD + crowd console; landing page | 11 h |
| **T2 Deploy + verify** | Render (Docker web service) + managed Postgres; health check; seed; live smoke test; browser E2E (Playwright) on the five mandatory journeys | 3 h |
| **T3 Documents** | MRD (1 page), PRD (2 pages), epics, stories, traceability, architecture, schema, API, AI/ML, test plan/results, deployment, user guide, judge demo guide, API setup guide; PDFs via headless Chrome with page-count checks | 4 h (in parallel with T1 by the second team member) |
| **T4 If time remains** | Community (posts, comments, reports, moderation), local businesses and homestays, queue tokens carried over, optional LLM narrative, submission folder, presentation PDF | remainder |

Skills per phase: `grilling` / `brainstorming` (decisions, now) → `frontend-design` + `design-taste-frontend` (landing page and app UI) → `test-driven-development` (each story) → `systematic-debugging` (failures) → `webapp-testing` (browser E2E, local and deployed).

### Major or irreversible decisions that need team approval

1. Use `crowdwise` as the base, since TripNest was not found.
2. Migrate Starlette → FastAPI, and add SQLAlchemy + Alembic + Postgres.
3. Keep the vanilla-JS front end (served by the same backend: one deploy, no CORS), not React/Flutter.
4. Hosting: Render (backend + static) and a managed Postgres. The team creates the accounts and enters the credentials.
5. LLM usage: none by default; Claude API only if the team approves the cost.
6. Community and local-business features are Tier 4 and may ship as "planned" in the docs.
