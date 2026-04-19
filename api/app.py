from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.index import router as index_router
from api.runtime import get_runtime
from api.search import router as search_router

app = FastAPI(
    title="Flamki Vector Search API",
    version="1.0.0",
    description="Hackathon API for hybrid multimodal search powered by VectorAI + BM25.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(search_router)
app.include_router(index_router)


@app.get("/health")
async def health():
    runtime = get_runtime()
    return {"ok": True, "vectorai_available": runtime.vector_store.available()}

