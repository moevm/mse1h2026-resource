from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.ingest import router as ingest_router
from app.api.graph import router as graph_router
from app.api.agents import router as agents_router
from app.api.export import router as export_router
from app.api.traversal import router as traversal_router
from app.repositories.neo4j_connection import neo4j_driver
from app.repositories import agent_repo


@asynccontextmanager
async def lifespan(application: FastAPI):
    neo4j_driver.verify_connectivity()
    neo4j_driver.ensure_indexes()
    agent_repo.ensure_agent_indexes()
    yield
    neo4j_driver.close()


app = FastAPI(
    title=settings.app_title,
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agents_router, prefix="/api/v1/agents", tags=["Agents"])
app.include_router(ingest_router, prefix="/api/v1/ingest", tags=["Ingest"])
app.include_router(graph_router, prefix="/api/v1/graph", tags=["Graph"])
app.include_router(export_router, prefix="/api/v1/export", tags=["Export"])
app.include_router(traversal_router, prefix="/api/v1/traversal", tags=["Traversal"])


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok"}
