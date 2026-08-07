---
tags:
  - sih
  - year-3
---
# SAMUDRA — Master Project Document

### AI-Driven Unified Data Platform for Oceanographic, Fisheries, and Molecular Biodiversity Insights

**SIH25041 · Ministry of Earth Sciences · Theme: Renewable / Sustainable Energy · Category: Software**

This is the single reference document for the project — problem, architecture, technical implementation, current build status, and roadmap. Other project docs (`README.md`, `who-this-is-for.md`, `samudra-explainer-and-pitch.md`, `claude.md`, `todo.md`) go deeper on specific angles; this one ties everything together.

---

## Table of contents

1. [Problem statement](https://claude.ai/chat/824a742a-0f55-4975-9a84-564fae8ebc62#1-problem-statement)
2. [What the platform does](https://claude.ai/chat/824a742a-0f55-4975-9a84-564fae8ebc62#2-what-the-platform-does)
3. [Current state](https://claude.ai/chat/824a742a-0f55-4975-9a84-564fae8ebc62#3-current-state)
4. [System architecture](https://claude.ai/chat/824a742a-0f55-4975-9a84-564fae8ebc62#4-system-architecture)
5. [Tech stack](https://claude.ai/chat/824a742a-0f55-4975-9a84-564fae8ebc62#5-tech-stack)
6. [Data sources](https://claude.ai/chat/824a742a-0f55-4975-9a84-564fae8ebc62#6-data-sources)
7. [Backend reference](https://claude.ai/chat/824a742a-0f55-4975-9a84-564fae8ebc62#7-backend-reference)
8. [Frontend reference](https://claude.ai/chat/824a742a-0f55-4975-9a84-564fae8ebc62#8-frontend-reference)
9. [ML models — methodology](https://claude.ai/chat/824a742a-0f55-4975-9a84-564fae8ebc62#9-ml-models--methodology)
10. [RAG / AI assistant architecture](https://claude.ai/chat/824a742a-0f55-4975-9a84-564fae8ebc62#10-rag--ai-assistant-architecture)
11. [Folder structure](https://claude.ai/chat/824a742a-0f55-4975-9a84-564fae8ebc62#11-folder-structure)
12. [What's real vs. simulated](https://claude.ai/chat/824a742a-0f55-4975-9a84-564fae8ebc62#12-whats-real-vs-simulated)
13. [Roadmap](https://claude.ai/chat/824a742a-0f55-4975-9a84-564fae8ebc62#13-roadmap)
14. [Target audience summary](https://claude.ai/chat/824a742a-0f55-4975-9a84-564fae8ebc62#14-target-audience-summary)
15. [Running the project](https://claude.ai/chat/824a742a-0f55-4975-9a84-564fae8ebc62#15-running-the-project)

---

## 1. Problem statement

India's ocean, fisheries, and biodiversity data is collected well but lives in disconnected systems: ocean sensor data with INCOIS, catch records with CMFRI and state departments, species and biodiversity records in OBIS/GBIF, and molecular/eDNA data in academic pipelines. No system currently lets someone ask a question that spans all three — so patterns that would be obvious if the data were connected (a stock decline correlating with a temperature anomaly and a drop in biodiversity signals) go unnoticed until the damage is already visible in catch reports, weeks after the fact.

## 2. What the platform does

SAMUDRA is built around three layers, in order of priority:

1. **Prediction and conclusions first.** The platform's headline value is running real models on the unified data — species movement trajectories, coral bleaching risk buildup, seasonality-aware stock forecasts — and stating a plain-language conclusion, not just a chart.
2. **A grounded AI assistant.** Ask a question in plain English and get an answer built from real retrieved data, with sources shown, or an honest "I don't have data for that" instead of a guess.
3. **One unified map.** Ocean sensors, eDNA sites, fishing advisories, coral reefs, and (planned) vessel tracking and pollution sources all sit on one live map as the shared substrate everything else is built on.

A full plain-language walkthrough of every feature lives in `samudra-explainer-and-pitch.md`; this document covers how it's actually built.

## 3. Current state

|Area|Status|
|---|---|
|Interactive map (Leaflet), 9 stations, layer toggles|Built|
|Station detail panel with trend chart|Built|
|AI assistant — chat UI, preset + free-text queries|Built (backend RAG wiring in progress)|
|Natural language query — search bar, query trace|Built (backend wiring in progress)|
|Light-mode, minimal UI redesign|Built|
|Species movement trajectory model|In progress|
|Coral bleaching — multi-factor, time-series buildup|In progress|
|Fish stock forecast — STL seasonality decomposition|In progress|
|Timeline scrubber with real map effects (marker movement, reef intensity)|In progress|
|Conclusion layer (model output → plain-language sentence via gpt-oss)|In progress|
|Illegal fishing detection (vessel tracking + MPA boundaries)|Planned|
|Pollution / treatment plant data layer|Planned|
|Expanded map density (12-15 more stations)|Planned|
|Plain-language glossary / InfoTip component|Planned|
|Proactive insight engine (cross-domain anomaly detection)|Planned|
|Voice interface (regional languages)|Planned|

See `todo.md` for the phase-by-phase build checklist behind this table.

## 4. System architecture

![[samudra_data_rag_pipeline.png]]

The AI orchestration layer is the hub: it's called both by the chat interface (answering user questions) and by the ML/prediction engine (turning model output into plain-language conclusions). This is the same `services/llm.py` wrapper in both cases — one model, one place it's configured, two different jobs.

## 5. Tech stack

- **Frontend:** Vue 3, Vue Router, Tailwind CSS, GSAP for animation (panel transitions, timeline scrubbing, marker movement)
- **Map:** Leaflet with CartoDB Positron (light) tiles
- **Charts:** Chart.js
- **Backend:** Python, FastAPI, managed with `uv`
- **AI model:** `gpt-oss:120b-cloud` via Ollama — the single model used for chat, NL-to-query translation, and conclusion generation
- **Embeddings:** an Ollama-hosted embedding model (e.g. `nomic-embed-text`) for the vector store
- **Vector store:** in-memory numpy cosine similarity over seeded text chunks — deliberately simple, no hosted vector DB needed at this scale
- **ML libraries:** `pandas`/`numpy` for DHW accumulation and centroid trajectory smoothing, `statsmodels` for STL decomposition
- **Geospatial (planned, Phase 8):** `shapely`/`geopandas` for point-in-polygon vessel-zone checks

## 6. Data sources

| Domain                    | Source                             | What it provides                         | Status                                       |
| ------------------------- | ---------------------------------- | ---------------------------------------- | -------------------------------------------- |
| Ocean physical parameters | INCOIS, Copernicus Marine (CMEMS)  | SST, salinity, chlorophyll, currents     | Seeded/simulated pattern, real methodology   |
| Fisheries                 | CMFRI, state fisheries departments | Catch landing records by species/region  | Seeded/simulated pattern                     |
| Biodiversity              | OBIS, GBIF                         | Species occurrence, geo-tagged           | Real API, free, no auth                      |
| Molecular / eDNA          | BOLD Systems, NCBI GenBank         | Reference DNA barcodes                   | Referenced methodology, simulated detections |
| Vessel activity           | Global Fishing Watch               | Vessel position, apparent fishing effort | Planned (Phase 8)                            |
| Protected areas           | Protected Planet / WDPA            | MPA boundary polygons                    | Planned (Phase 8)                            |
| Pollution                 | CPCB, data.gov.in                  | Treatment plant location + compliance    | Planned (Phase 12)                           |

## 7. Backend reference

|Endpoint|Purpose|Status|
|---|---|---|
|`GET /api/stations`|List stations, coordinates, latest readings|Built|
|`GET /api/stations/{id}`|Station detail + trend history|Built|
|`GET /api/species`|Species table with conservation status|Built|
|`GET /api/advisories`|Active fishing advisories|Built|
|`POST /api/chat`|`{message, station_context?}` → RAG-grounded answer + sources|In progress|
|`POST /api/nlq`|Free text → structured query trace + matching records|In progress|
|`GET /api/species/{id}/trajectory`|Historical + forecast movement path for a species|Planned (Phase 15)|
|`GET /api/reefs/{id}/bleaching-trend`|Weekly DHW accumulation + factor breakdown|Planned (Phase 16)|
|`GET /api/predict/stock`|STL-decomposed catch forecast (trend/seasonal/residual)|Planned (Phase 17)|
|`GET /api/timeline?days=30`|Daily arrays for species position, reef risk, stock index|Planned (Phase 18)|
|`GET /api/vessels`|Live vessel positions + MPA violation flags|Planned (Phase 8)|
|`GET /api/pollution`|Treatment plant locations + compliance status|Planned (Phase 12)|
|`GET /api/insights`|Auto-detected cross-domain anomalies|Planned (roadmap)|

All Ollama calls route through one wrapper (`services/llm.py`) so the model name and prompt conventions live in a single place, not scattered per-endpoint.

## 8. Frontend reference

|Component|Purpose|Status|
|---|---|---|
|`MapShell.vue`|Full-screen Leaflet map, layer toggles, marker rendering|Built|
|`StationDetail.vue`|Slide-in panel for a clicked station, with trend chart|Built|
|`AIChat.vue`|Chat panel, preset prompts, cited responses|Built (frontend), wiring to real `/api/chat` in progress|
|`SpeciesExplorer.vue`|Species table|Built — being replaced by `MovementTrends.vue` (Phase 15)|
|`Predictive.vue`|Forecast/gauge/range charts|Built — being split into `BleachingTrend.vue` and `StockForecast.vue` (Phases 16-17)|
|`TimelineScrubber.vue`|Bottom scrubber driving map animation|Planned (Phase 18)|
|`InfoTip.vue`|Reusable glossary tooltip, attached to metrics/layers|Planned (Phase 11)|
|Vessel layer|Renders flagged vessels on the map|Planned (Phase 8)|
|Pollution layer|Renders treatment plants, colored by compliance|Planned (Phase 12)|
|Insights feed|Auto-generated anomaly cards|Planned (roadmap)|

## 9. ML models — methodology

**Species movement trajectory (Phase 15).** Bin OBIS/GBIF occurrence records by month, compute a weighted lat/lng centroid per bin, smooth the sequence with simple exponential smoothing, and extrapolate forward using the recent velocity vector. Output is a full point sequence (historical + forecast, clearly distinguished) rather than a single "shift" projection.

**Coral bleaching risk (Phase 16).** Core input is Degree Heating Weeks — the real NOAA methodology of accumulating SST anomalies above the bleaching threshold over a rolling 12-week window. Combined with chlorophyll trend (pollution/eutrophication proxy) and historical bleaching frequency at that reef into a composite score with documented, visible weights.

**Stock forecast (Phase 17).** STL decomposition (`statsmodels`) splits historical catch into trend, seasonal, and residual components. The trend component is forecast forward and recombined with the seasonal pattern — this is what distinguishes it from a naive regression, since catch data is strongly seasonal and a straight-line fit would be misleading.

**Conclusion generation (Phase 19).** Every model's numeric output is passed to one `gpt-oss:120b-cloud` call whose only job is to state the finding in a single grounded sentence, always including a confidence caveat. This is what turns a chart into a stated conclusion.

## 10. RAG / AI assistant architecture

Two retrieval paths feed the same model call, not one:

- **Structured retrieval** — the model calls backend tools (`get_catch_trend`, `get_sensor_readings`, `get_active_advisories`) that query real/seeded tabular data directly. This is how numeric questions get answered without hallucination risk.
- **Unstructured retrieval** — species descriptions, advisory notes, and background text are embedded and retrieved by cosine similarity, then passed as context for narrative/explanatory questions.

Both feed into one `gpt-oss:120b-cloud` call with a system prompt instructing it to answer only from provided context, cite sources, and explicitly say when it doesn't have relevant data rather than guessing. If a station is currently selected on the map, its data is passed in as additional context automatically.

## 11. Folder structure

```
backend/
  main.py
  services/
    llm.py          # Ollama client wrapper (chat + conclusion generation)
    embed.py         # embedding calls for the vector store
    rag.py            # retrieval logic (structured + vector)
    ml/
      trajectory.py   # species movement model
      bleaching.py    # DHW + composite bleaching score
      forecast.py     # STL stock forecast
  routers/            # stations, chat, nlq, predict, timeline, vessels, pollution
  data/                # seed data (JSON) pulled from OBIS/GBIF/etc.
frontend/
  src/
    components/       # MapShell, StationDetail, AIChat, MovementTrends,
                       # BleachingTrend, StockForecast, TimelineScrubber, InfoTip
    views/
    api/
    router/
ref.html               # design reference, not shipped
docs/
  README.md
  who-this-is-for.md
  samudra-explainer-and-pitch.md
  claude.md
  todo.md
  MASTER_DOCUMENT.md   # this file
```

## 12. What's real vs. simulated

Being upfront about this consistently is part of the project's credibility, not a weakness to hide:

- **Real:** UI/UX, data architecture, RAG retrieval mechanics, DHW bleaching methodology, STL decomposition approach, OBIS/GBIF species data (pulled live)
- **Simulated, built on realistic patterns:** ocean sensor readings, catch records, eDNA detections, vessel tracking (until Phase 8 wires in Global Fishing Watch), pollution compliance data (until Phase 12)
- **Not yet built:** illegal fishing detection, pollution layer, voice interface, proactive insight engine

## 13. Roadmap

Near-term (post-hackathon, natural next phases): production data pipelines direct from each agency's real feeds, proper historical training windows for the ML models, and a field-validation feedback loop where verified sightings improve model accuracy over time.

Feature roadmap, roughly in priority order: illegal fishing detection (Phase 8) → plain-language glossary (Phase 11) → pollution layer (Phase 12) → voice interface → proactive cross-domain insight engine.

## 14. Target audience summary

Fisheries department officers, marine researchers, MPA managers and conservation teams, blue economy policy makers, fishing communities (via the planned voice interface), and enforcement/patrol teams (via vessel tracking). Full persona-by-persona detail with real-life scenarios lives in `who-this-is-for.md`.

## 15. Running the project

```bash
# Backend
cd backend
uv run main.py                 # or: uv run uvicorn main:app --reload

# Confirm the model is available
ollama run gpt-oss:120b-cloud
ollama pull nomic-embed-text    # embedding model, separate from gpt-oss

# Frontend
cd frontend
npm run dev
```