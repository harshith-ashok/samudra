# Running SAMUDRA

Two processes: a FastAPI backend (port 8000) and a Vite/Vue frontend (port 5173). Both need to be running at once.

## Prerequisites

- **Python** managed via [`uv`](https://docs.astral.sh/uv/) (backend)
- **Node.js** + npm (frontend)
- **[Ollama](https://ollama.com)**, running locally, with two models pulled:

  ```bash
  ollama pull gpt-oss:120b-cloud
  ollama pull nomic-embed-text
  ```

  `gpt-oss:120b-cloud` is used for every chat/NLQ/summarization call; `nomic-embed-text` powers the RAG vector store. The backend will fail to answer chat/NLQ questions (and `/api/health`'s `rag_index_ready` will stay `false`) if Ollama isn't running or these models aren't pulled.

## 1. Backend

```bash
cd backend
uv sync
uv run python main.py
```

Runs at `http://localhost:8000`. Check `http://localhost:8000/api/health` — `rag_index_ready: true` means the embedding index built successfully against Ollama.

Optional env vars (both features work fine without them, using labeled simulated data instead):

- `DATA_GOV_IN_API_KEY` — real CPCB treatment-plant data (data.gov.in)
- `GFW_API_KEY` — real Global Fishing Watch vessel tracking

## 2. Frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Runs at `http://localhost:5173`. It talks to the backend at `http://localhost:8000` by default — override with a `VITE_API_BASE` env var if the backend is running elsewhere.

## Notes

- First backend startup downloads the `faster-whisper` speech-to-text model on first use of the mic/voice-search feature — needs internet access once.
- Live translation (`/api/translate`, used for Hindi/Tamil/Malayalam UI and STT round-tripping) calls the free Google Translate endpoint via `deep-translator` — needs internet access, no API key.
- To stop everything: `Ctrl+C` in both terminals, or kill the `uvicorn`/`vite` processes directly.

## Rebuilding regional-language UI strings

Only needed if you edit `frontend/src/i18n/en.json`'s UI-chrome strings — regenerates `hi.json`/`ta.json`/`ml.json` from it via Google Translate:

```bash
cd backend
uv run python data/generate_i18n.py
```
