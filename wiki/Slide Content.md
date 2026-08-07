---
tags:
  - year-3
  - sih
---
# SIH25041 — Slide Contents (SAMUDRA)

Fill directly into the official 6-slide template. Team ID/Name left as placeholders — pull those from your SIH portal registration.

---

## Slide 1 — Title Page

- **Problem Statement ID –** SIH25041
- **Problem Statement Title –** AI-Driven Unified Data Platform for Oceanographic, Fisheries, and Molecular Biodiversity Insights
- **Theme –** Renewable / Sustainable Energy
- **PS Category –** Software
- **Team ID –** [fill in from portal]
- **Team Name (Registered on portal) –** [fill in]

---

## Slide 2 — Idea Title

### ❖ SAMUDRA — Unified Ocean Intelligence Platform

- AI-powered platform unifying oceanographic, fisheries, and molecular biodiversity data onto a single interactive map.
- Conversational AI assistant grounded in real sensor, catch, and species data — answers questions with cited sources instead of guessing.
- Predictive analytics: fish stock forecasts, coral bleaching risk (NOAA Degree Heating Weeks methodology), and species range-shift projections.
- Scrubbable seasonal timeline that replays a month of predictions and historical trends directly on the map.
- Live illegal fishing detection: cross-references vessel tracking data against marine protected area boundaries.
- Roadmap: pollution/treatment-plant correlation layer, voice interface in regional languages, proactive anomaly-insight engine.

### Innovation & Uniqueness

- Hybrid retrieval architecture: structured tool-calls for real numbers (catch trends, sensor readings) combined with vector search for contextual knowledge — not a single naive RAG pipeline.
- Map-centered UX: every data layer, prediction, and chat interaction is anchored to a real, clickable geographic point, not a disconnected dashboard tab.
- Proactive insight generation: the system is designed to surface correlated anomalies across domains (e.g. catch decline + SST anomaly + eDNA silence) rather than only answering questions it's asked.
- Enforcement-relevant, not just informational: live vessel tracking against protected-area boundaries gives the platform real operational value beyond research.
- Designed for a non-technical end user from day one — plain-language explainers throughout, not just a scientist's tool.

---

## Slide 3 — Technical Approach

### Technologies used

- **Frontend:** Vue 3, Vue Router, Tailwind CSS, GSAP (interaction/animation)
- **Mapping:** Leaflet with real coastal station coordinates
- **AI / LLM:** gpt-oss:120b-cloud served via Ollama — used for chat, NL-to-query translation, and insight generation
- **Embeddings:** Ollama-hosted embedding model (e.g. nomic-embed-text) for vector retrieval
- **Backend:** Python, FastAPI, managed with `uv`
- **Visualization:** Chart.js for time-series, forecast, and comparison charts
- **Data:** INCOIS / Copernicus Marine (ocean parameters), CMFRI (catch records), OBIS / GBIF (species occurrence), BOLD / NCBI (eDNA reference barcodes), Global Fishing Watch (vessel tracking), CPCB (coastal treatment plant compliance)

### Process flow

1. **Data ingestion** — pull from ocean, fisheries, biodiversity, vessel, and pollution sources
2. **Preprocessing** — cleaning, normalization, shared region/station schema across all domains
3. **Unified data layer** — structured DB (time-series), vector store (text/species knowledge), knowledge graph (entity relationships)
4. **AI orchestration** — RAG + tool-use via gpt-oss:120b-cloud; retrieves real data before answering
5. **Insights & prediction engine** — stock forecasting, bleaching risk, range-shift modeling, anomaly correlation across domains
6. **Dashboard & API** — interactive map, conversational assistant, natural-language query, scrubbable seasonal timeline

---

## Slide 4 — Feasibility and Viability

### Feasibility

- All core datasets are publicly available: OBIS/GBIF (free API, no auth), Global Fishing Watch (free API key), INCOIS/CMEMS ocean parameters, CMFRI published catch data.
- Core prototype (map + grounded AI chat + predictions) is achievable within the hackathon timeframe using this stack.
- Architecture is built to expand incrementally — pollution layer, seasonal timeline, and voice interface are additive, not redesigns.

### Challenges & Risks

- Heterogeneous data formats across agencies require careful schema normalization.
- Live external APIs (vessel tracking) introduce reliability risk during a live demo — mitigated with cached fallback data.
- Prediction models are intentionally simple (regression, thermal-stress accumulation) for this stage — production accuracy would need longer historical training windows and domain expert validation.
- eDNA data at this stage is simulated on top of real species lists, since raw wet-lab barcoding data isn't practically obtainable for a prototype.

---

## Slide 5 — Impact and Benefits

### Impact

- Directly supports the Ministry of Earth Sciences' ocean monitoring and Blue Economy objectives.
- Provides one data-driven decision layer for fisheries officers, marine researchers, conservation teams, and policymakers who currently work across disconnected systems.

### Benefits

- **Economic:** Earlier stock-decline warnings let fisheries departments issue advisories before a season is already lost, reducing losses for fishing communities.
- **Environmental:** Early coral bleaching and biodiversity-decline detection lets conservation teams prioritize limited field-verification resources.
- **Social:** Plain-language explainers and a planned voice interface make the platform usable by coastal communities, not only researchers with technical training.
- **Governance:** Live illegal fishing detection against protected-area boundaries gives enforcement teams an actionable, real-time signal.
- **Scalability:** The unified-schema architecture generalizes beyond India's coastline — the same pipeline design applies to any country's ocean, fisheries, and biodiversity data.

---

## Slide 6 — Research and References

- INCOIS (Indian National Centre for Ocean Information Services): https://incois.gov.in
- Copernicus Marine Service (CMEMS): https://marine.copernicus.eu
- CMFRI (Central Marine Fisheries Research Institute): https://www.cmfri.org.in
- OBIS (Ocean Biodiversity Information System): https://obis.org
- GBIF (Global Biodiversity Information Facility): https://www.gbif.org
- BOLD Systems (DNA barcode reference library): https://www.boldsystems.org
- Global Fishing Watch (vessel tracking data): https://globalfishingwatch.org
- NOAA Coral Reef Watch — Degree Heating Weeks methodology: https://coralreefwatch.noaa.gov
- CPCB / data.gov.in — coastal treatment plant compliance data
- Research on retrieval-augmented generation (RAG) and tool-use for domain-grounded LLM question answering