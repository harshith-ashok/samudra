from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import advisories, analytics, chat, glossary, nlq, pollution, predict, reefs, species, stations, stt, timeline, vessels
from services import embed
from services import stt as stt_service  # module, not the router above

app = FastAPI(title="SAMUDRA API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stations.router)
app.include_router(species.router)
app.include_router(advisories.router)
app.include_router(chat.router)
app.include_router(nlq.router)
app.include_router(predict.router)
app.include_router(glossary.router)
app.include_router(timeline.router)
app.include_router(vessels.router)
app.include_router(pollution.router)
app.include_router(analytics.router)
app.include_router(reefs.router)
app.include_router(stt.router)


@app.on_event("startup")
def startup():
    embed.build_index()
    stt_service.warm()


@app.get("/api/health")
def health():
    return {"data": {"status": "ok", "rag_index_ready": embed.is_ready()}}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
