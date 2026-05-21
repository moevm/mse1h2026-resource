import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.auth import router as auth_router
from app.api.ingest import router as ingest_router
from app.api.graph import router as graph_router
from app.api.agents import router as agents_router
from app.api.applications import router as applications_router
from app.api.export import router as export_router
from app.api.traversal import router as traversal_router
from app.api.receiver import router as receiver_router
from app.api.mapper_config import router as mapper_config_router
from app.api.mapper_preview import router as mapper_preview_router
from app.api.edge_presets import router as edge_presets_router
from app.api.timeline import router as timeline_router
from app.repositories.neo4j_connection import neo4j_driver
from app.repositories import agent_repo, application_repo, neo4j_repo, user_repo
from app.repositories.mapping_repo import mapping_repo


@asynccontextmanager
async def lifespan(application: FastAPI):
    neo4j_driver.verify_connectivity()
    neo4j_driver.ensure_indexes()
    agent_repo.ensure_agent_indexes()
    application_repo.ensure_application_indexes()
    mapping_repo.ensure_indexes()
    user_repo.ensure_user_indexes()
    user_repo.ensure_default_admin()
    neo4j_repo.ensure_activity_indexes()
<<<<<<< HEAD
=======
    try:
        cleanup = neo4j_repo.cleanup_deprecated_nodes()
        if cleanup.get("deleted_libraries") or cleanup.get("deleted_ip_nodes"):
            import logging
            logging.getLogger(__name__).info(
                "Deprecated node cleanup: %s", cleanup,
            )
    except Exception:
        pass
>>>>>>> f81199920d6f71cd1754b6eaad7dfc55c74955f8
    asyncio.create_task(_activity_cleanup_loop())
    yield
    neo4j_driver.close()


async def _activity_cleanup_loop() -> None:
    import logging
    import os
    log = logging.getLogger("activity-cleanup")
    ttl_hours = int(os.environ.get("ACTIVITY_TTL_HOURS", "24"))
    interval_seconds = int(os.environ.get("ACTIVITY_CLEANUP_INTERVAL_SECONDS", "3600"))
    while True:
        try:
            await asyncio.sleep(interval_seconds)
            cutoff_ms = int((__import__("time").time() - ttl_hours * 3600) * 1000)
            res = neo4j_repo.cleanup_activity_older_than(cutoff_ms)
            log.info("activity cleanup ttl=%dh: %s", ttl_hours, res)
        except Exception as e:
            log.warning("activity cleanup failed: %s", e)


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

app.include_router(auth_router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(agents_router, prefix="/api/v1/agents", tags=["Agents"])
app.include_router(applications_router, prefix="/api/v1/apps", tags=["Applications"])
app.include_router(ingest_router, prefix="/api/v1/ingest", tags=["Ingest"])
app.include_router(graph_router, prefix="/api/v1/graph", tags=["Graph"])
app.include_router(export_router, prefix="/api/v1/export", tags=["Export"])
app.include_router(traversal_router, prefix="/api/v1/traversal", tags=["Traversal"])
app.include_router(receiver_router, prefix="/api/v1/receiver", tags=["Receiver"])
app.include_router(mapper_config_router, prefix="/api/v1/mapper", tags=["Mapper"])
app.include_router(mapper_preview_router, prefix="/api/v1/mapper", tags=["Mapper"])
app.include_router(edge_presets_router, prefix="/api/v1/edge-presets", tags=["EdgePresets"])
app.include_router(timeline_router, prefix="/api/v1/timeline", tags=["Timeline"])


@app.get("/health", tags=["Health"])
@app.get("/api/v1/health", tags=["Health"])
async def health():
    return {"status": "ok"}
