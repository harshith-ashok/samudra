# SAMUDRA — Component Reference

What each piece of the codebase is responsible for. Organized by layer, not by
build phase — see `todo.md` for the phase-by-phase history and `CLAUDE.md` for
the architecture rationale.

## Frontend

### Shell & routing

| Component | Role |
|---|---|
| `main.ts` | Vue app bootstrap — mounts the router. |
| `router/index.ts` | Single route (`/` → `MapView`). SAMUDRA is a one-screen app; there's nothing else to route to. |
| `App.vue` | Just a `<router-view>`. No shared chrome lives here — `MapShell` owns the whole screen. |
| `views/MapView.vue` | Thin wrapper around `MapShell`. Exists so the router has a component to point at. |
| `components/MapShell.vue` | The app. Owns the Leaflet map instance, all map layers/markers, the side panel, the search bar, and wires every other component together. Everything else in this table is either rendered inside it or passed data by it. |

### Map-surface UI (always visible)

| Component | Role |
|---|---|
| `ModuleRail.vue` | Left-rail stack of module buttons (AI Assistant, Movement Trends, Predictive Analytics, Analytics, Data Glossary). Purely presentational — takes a list of `{key, label, iconPaths}` and emits `open`. |
| `LayerPanel.vue` | Bottom-right card: map layer toggles (buoys, eDNA, advisories, coral, range-shift, vessels, pollution) plus a few live KPI numbers. Presentational; `MapShell` owns the actual layer state. |
| `ImpactCard.vue` | Top-right "coverage snapshot" card (coastline km, stations tracked, states/UTs, species indexed) — the judge-facing scale pitch. Collapsible. |
| `TimelineScrubber.vue` | Bottom-center horizontal scrubber over the last ~20 recorded days + ~10 forecast days of SST or chlorophyll. Fetches `/api/timeline/{metric}`, emits per-day values so `MapShell` can recolor markers and (for reef stations) resize/darken the stress-zone circle. Has a play button that auto-advances over ~10s. |
| `GuidedIntro.vue` | One-time (per browser, via `localStorage`) GSAP spotlight tour over four map elements. Skippable; degrades gracefully if a target element isn't mounted yet. |
| `InfoTip.vue` | The "ⓘ" icon used everywhere (layer rows, KPIs, chart headers). Looks up its copy from `useGlossary()` by key — never hardcodes explanation text itself. |

### Side-panel content (one per module / selection)

| Component | Role |
|---|---|
| `StationDetail.vue` | Shown when a map marker is clicked. Station reading + history sparkline + "ask AI about this site" handoff into `AIChat`. |
| `VesselDetail.vue` | Shown when a vessel marker is clicked. Speed/heading/type, and a violation banner if the vessel is currently inside an MPA polygon. |
| `AIChat.vue` | The RAG chat panel. Posts to `/api/chat` with the current station context (if any) attached, renders the answer plus cited sources (both tool calls and retrieved doc chunks). |
| `SpeciesExplorer.vue` | **"Movement Trends."** Species table (sci name / region / conservation status) doubles as a picker — clicking a row fetches `/api/species/{id}/trajectory` and renders a conclusion sentence, a drift stat line, a lat-over-time chart (solid observed, dashed forecast), and emits the path up to `MapShell` to draw on the map. |
| `Predictive.vue` | Three model views, each leading with a gpt-oss conclusion sentence: sardine stock forecast (regression + 80% CI band), coral bleaching buildup (weekly DHW accumulation chart + weighted factor-breakdown bar), and range-shift (two-species latitude trend). |
| `Analytics.vue` | Cross-cutting charts that don't fit the predictive/movement framing: SST-vs-catch correlation scatter (with Pearson's r), regional biodiversity-index bar chart, pollution-compliance trend line, and vessel activity per MPA zone. |
| `GlossaryPanel.vue` | Standalone scrollable version of every `InfoTip` entry, for a judge who wants to skim definitions instead of hunting for ⓘ icons. |

### Shared infra

| File | Role |
|---|---|
| `api/index.ts` | Every backend call in one place — one small function per endpoint, all going through a shared `getJSON`/`postJSON` that unwraps the `{data: ...}` envelope. Components never call `fetch` directly. |
| `api/types.ts` | TypeScript shapes mirroring each backend response. Kept in sync by hand with the FastAPI response shapes (no codegen). |
| `composables/useGlossary.ts` | Module-level singleton: fetches `/api/glossary` once, shares the cached list across every `InfoTip` and `GlossaryPanel` instance. |
| `utils/colorScale.ts` | Maps a raw SST/chlorophyll value to a marker fill color (cool→pale→hot gradient). Used by both the timeline scrubber and the reef stress-circle darkening. |
| `utils/speciesId.ts` | `speciesSlug()` — mirrors the backend's `species_id()` slug function so the frontend can build a trajectory URL from a scientific name without a round trip. |

## Backend

`main.py` is the FastAPI entrypoint — it just registers routers and runs the
RAG index build on startup. Routers are intentionally thin: parse the request,
call one service function, wrap the result in `{"data": ...}` (or a 404 on
`{"error": ...}`). All the actual logic lives in `services/`.

### Routers

| Router | Endpoints | Role |
|---|---|---|
| `stations.py` | `GET /api/stations`, `GET /api/stations/{id}` | Station list (summary, no history) and single-station detail (with history). |
| `species.py` | `GET /api/species`, `GET /api/species/{id}/trajectory` | Species table, and per-species movement trajectory. |
| `advisories.py` | `GET /api/advisories` | Fishing/conservation advisories, optional status filter. |
| `chat.py` | `POST /api/chat` | RAG chat endpoint — delegates entirely to `services/rag.py`. |
| `nlq.py` | `POST /api/nlq` | Natural-language query — delegates to `services/nlq.py`. |
| `predict.py` | `GET /api/predict/{stock,bleaching,range-shift}` | The three original single-number prediction endpoints. |
| `reefs.py` | `GET /api/reefs/{id}/bleaching-trend` | The richer multi-factor bleaching model (supersedes the gauge in `predict.bleaching`). |
| `timeline.py` | `GET /api/timeline/{metric}` | Per-station recorded+forecast day arrays for the scrubber. |
| `vessels.py` | `GET /api/vessels` | Vessel positions + MPA violation flags. |
| `pollution.py` | `GET /api/pollution` | Treatment-plant locations + compliance status. |
| `analytics.py` | `GET /api/analytics/*` | The four Analytics-panel aggregate views. |
| `glossary.py` | `GET /api/glossary` | Plain-language term definitions. |

### Services

| Service | Role |
|---|---|
| `data.py` | Loads every seed JSON file once (`lru_cache`) and exposes typed accessors. The only place that touches `backend/data/*.json` directly. |
| `llm.py` | The single choke point for every Ollama call (chat + embeddings). Model names (`gpt-oss:120b-cloud`, `nomic-embed-text`) live here and nowhere else. |
| `embed.py` | Builds the in-memory numpy embedding index for the RAG text corpus at startup; cosine-similarity search over it. |
| `rag.py` | Orchestrates one gpt-oss chat call fed by two retrieval paths — structured tool calls (`tools.py`) and unstructured vector search (`embed.py`) — plus optional "what's on screen" station context. |
| `tools.py` | The structured tool functions the model can call mid-conversation (`get_catch_trend`, `get_sensor_readings`, `get_active_advisories`, `get_species_info`) — deterministic lookups against the seed data, no hallucination risk on numbers. |
| `nlq.py` | Translates free text into a structured filter via one gpt-oss call, then runs that filter against the seed data directly — the model decides *what* to look up, never fabricates the results. |
| `predict.py` | The three original trend-extrapolation models (stock, bleaching, range-shift), each honestly labeled with its methodology and now each ending in a `conclusions.conclude()` sentence. |
| `reefs.py` | Multi-factor bleaching composite: 60% DHW + 25% chlorophyll drift + 15% illustrative historical-frequency, with documented weights and a full weekly accumulation series (not just a final number). |
| `trajectory.py` | Species movement trajectory: per-year occurrence centroid → exponential smoothing → forward extrapolation from the recent velocity vector. Binned by year (not month) because the source records are year-precision only. |
| `conclusions.py` | The shared "turn a model's numeric output into one plain-language sentence with a confidence caveat" gpt-oss helper — reused by `predict.py`, `reefs.py`, and `trajectory.py` so every model view reads as a conclusion, not just a computed number. |
| `vessels.py` | Simulated AIS-like fleet (real position computed from wall-clock time, no persisted state) plus the point-in-polygon MPA-violation check. Pluggable via `GFW_API_KEY` for a real Global Fishing Watch feed later. |
| `pollution.py` | Treatment-plant compliance data. Pluggable via `DATA_GOV_IN_API_KEY` for a real CPCB/data.gov.in feed later; falls back to simulated figures for real coastal cities. |
| `analytics.py` | The four cross-cutting Analytics-panel views (SST-vs-catch correlation, biodiversity index, compliance trend, vessel activity per MPA) — each a different cut of data already served elsewhere, not a new source. |
| `timeline.py` | Per-station recorded-history + short trend-extrapolated forecast tail for the scrubber, tagged `"recorded"` / `"forecast"` per point. |

### Data (`backend/data/`)

Seed JSON the app runs on, plus the scripts that built it. Real sources
(OBIS/GBIF occurrences, INCOIS-shaped SST/salinity) are mixed with clearly
labeled simulated data (catch records, vessel tracks, MPA polygons, pollution
figures) where a real API key wasn't available in this build window — see each
service's docstring for which is which. `build_seed_data.py` / `fetch_seed_data.py`
/ `build_static_seed.py` are the one-off generation scripts, not runtime code.
