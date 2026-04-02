"""Naelia's Chronicles — FastAPI game server."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from server.config import CONFIG
from server.database.connection import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: ensure DB exists. Shutdown: nothing special yet."""
    await init_db()
    yield


app = FastAPI(
    title="Naelia's Chronicles — DM Server",
    version="0.1.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    """Server health check."""
    return {
        "status": "ok",
        "campaign": CONFIG["game"]["campaign_name"],
        "version": "0.1.0",
    }


# ---------------------------------------------------------------------------
# Register route modules
# ---------------------------------------------------------------------------

from server.routes import dm, admin  # noqa: E402

app.include_router(dm.router)
app.include_router(admin.router)
