# TripNest AI: External Services and API Keys

Version 2.0 · 2 November 2026 (replaces the earlier proposal, which assumed a larger product). **TripNest AI needs no API key and no paid service.**

| Service | Used for | Key? | Cost | Limits and rules | Fallback if unavailable |
|---|---|---|---|---|---|
| OpenStreetMap tiles (via Leaflet from cdnjs) | Base map on all three pages | No | Free | Tile usage policy: low traffic, attribution shown, no bulk download. Heavy use needs another tile provider | The pages still work; the map area shows an empty background and the cards and lists carry the same information |
| Wikimedia Commons and Wikipedia API | Place photos with credit and licence | No | Free | Clients must identify themselves with a contact URL or email in the User-Agent (`WIKIMEDIA_CONTACT`); requests are cached for 24 hours per place | A flat grey tile; `PHOTO_PROVIDER=off` disables it |
| PostgreSQL (production only) | Catalogue tables | Connection string | Depends on host; verify current free-tier terms | Free tiers may limit storage or expire | SQLite is used locally |
| Hosting (for example Render, Docker) | Public URL | Account | Depends; verify | Free services sleep when idle | Run locally |

**Not used, on purpose:** any AI or language-model API (the two features need none), a geocoding or routing service (cities come from a built-in list of 77; distance is straight-line), a weather service (removed from scope), Google Maps (would need a billing account).

## Secrets and configuration

Only `SECRET_KEY` and `DATABASE_URL` are secret, and only in production. They live in environment variables (see `.env.example`), are never in the source, and the app refuses to start in production without them. The browser receives no key. `.env` is git-ignored.

## If a paid or keyed service is ever added

Explain why, check current pricing and limits, offer a free alternative, and get approval first. Possible future additions (each needs that review): road-distance routing, weather and events as model inputs, real gate or sensor feeds.
