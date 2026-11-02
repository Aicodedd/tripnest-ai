# TripNest AI

**Discover Smarter. Travel Better. Explore Beyond the Crowds.**

TripNest AI does two things:

1. **Tourist crowd prediction.** Pick a destination, a date and a time range, and see the predicted crowd level, the best time to visit and the next seven days.
2. **Smart destination recommendation.** Enter where you are starting, a date and an optional interest, and get ranked destinations that explain themselves, using the predicted crowd on your date.

It covers all 36 Indian states and union territories (84 destinations, 271 attractions). No registration, no API key and no paid service is needed.

> **Data honesty.** No verified public source of hourly visitor counts exists for Indian attractions. The crowd model is trained on a clearly labelled **demonstration** history, and every result says so ("ML prediction", "Demonstration data", "Not live"). Capacities are assumptions. The pipeline can be retrained on real counts (see [AI/ML documentation](docs/AI_ML_DOCUMENTATION.md)).

**Live demo:** https://tripnest-ai-1rug.onrender.com (free plan; first load can take about 30 seconds).

## Model result (demonstration data)

Chronological split: 336 days train, 14 validation, 14 test. On the test fortnight (41,902 hourly rows): **MAPE 9.38%** for the model, against 31.79% for "same hour last week" and 27.45% for a weekday-hour average. This shows the pipeline works, not real-world accuracy.

## Run it locally

Prerequisites: Python 3.12 or newer (developed on 3.14); Google Chrome for the browser tests and PDFs.

```bash
python3 -m venv .venv
```

```bash
.venv/bin/pip install -r requirements-dev.txt
```

```bash
cp .env.example .env
```

Edit `.env` (set `SECRET_KEY`; the other defaults work locally). Then start the app:

```bash
cd backend && ../.venv/bin/uvicorn app.main:app --reload
```

Open http://localhost:8000. API documentation is at http://localhost:8000/docs. On first start the app creates the SQLite database, seeds the catalogue and loads the pre-trained model from `backend/models/`.

### Tests

```bash
cd backend && ../.venv/bin/python -m pytest
```

```bash
sh e2e/run.sh
```

The backend suite covers the model, the recommender, the prediction API, locations and validation. The browser suite starts its own server on port 8020 and drives real Chrome through the five main journeys. Results: [TEST_RESULTS](docs/TEST_RESULTS.md).

### Retrain the model

```bash
cd backend && ../.venv/bin/python -m scripts.train_model --days 365
```

About 30 seconds and 1.3 GB of memory.

### Build the PDFs from the Markdown documents

```bash
.venv/bin/python docs/build_pdfs.py
```

This also checks that the MRD is one A4 page, the PRD two, and that every test cited in the documents exists.

## Deploy

See [DEPLOYMENT_GUIDE](docs/DEPLOYMENT_GUIDE.md). `Dockerfile` and `render.yaml` are ready for Render with PostgreSQL. **The application has not been deployed yet**; there is no public URL.

## Project layout

```
backend/app/        FastAPI app: routers/discover.py (core features), routers/catalog.py, services/ (prediction, recommender, forecast, crowd, runtime, photos), data/ (catalogue, cities)
backend/migrations/ Alembic migration
backend/models/     Trained crowd model and metrics.json
backend/tests/      pytest suite (tests/legacy: tests of unplugged modules, not run)
frontend/           Three-page web app (vanilla JS modules, Leaflet); frontend/legacy: the previous larger app, kept, not served
e2e/                Playwright browser tests
docs/               Product, technical and test documents (Markdown source, PDFs built by build_pdfs.py)
```

## Scope

Only the two features above are part of the product. Itinerary planning, community, reviews, weather, accounts, admin dashboards and local listings were removed from the product; their code is kept on disk, unmounted (see [SCOPE_CHANGE_AUDIT](docs/SCOPE_CHANGE_AUDIT.md)) and is listed as future scope only.

Map © OpenStreetMap contributors. Photos from Wikimedia Commons with credit shown on each page.
