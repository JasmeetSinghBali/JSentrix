"""
gateway/src/main.py
Gateway FastAPI application entrypoint.
Supports both HTTP and subprocess MCP server modes.
Usage:
    python src/main.py or uv run ./src/main.py for docker/production mode
    uv run ./src/main.py > tracers/logs/gateway_trace.log 2>&1 without console tracer or logs instead persistance in gateway_trace.log
    python src/main.py --mcp-mode subprocess i.e to start the mcp_server also as subprocess in http api for local dev
"""

import argparse
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import subprocess
from fastapi import FastAPI
from tracers.tracing import setup_tracing
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from infrastructure.database.session import engine, get_db
from infrastructure.database.models import Base
from application.services.logger import logger
from api.routes import auth, tools
from core.config.settings import settings
from application.use_cases.auth import ensure_first_superuser
import httpx


def parse_args():
    parser = argparse.ArgumentParser(description="Gateway server")
    parser.add_argument(
        "--mcp-mode",
        choices=["http", "subprocess"],
        default="http",
        help="How to connect to MCP server: http (default) or subprocess (local dev)",
    )
    parser.add_argument(
        "--mcp-server-script",
        default=os.path.abspath(
            os.path.join(
                os.path.dirname(__file__), "../../mcp_server/interface/mcp_server.py"
            )
        ),
        help="Path to mcp_server.py for subprocess mode",
    )
    return parser.parse_args()


args = parse_args()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application startup and shutdown logic.
    """
    logger.info("Initializing database...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create first superuser if not exists
    async for db in get_db():
        await ensure_first_superuser(db, settings)
        break

    mcp_process = None
    if args.mcp_mode == "subprocess":
        logger.info(f"Starting MCP server as subprocess: {args.mcp_server_script}")
        mcp_process = subprocess.Popen(
            [sys.executable, args.mcp_server_script, "--http"]
        )
        # Optionally, wait for MCP server to be ready (health check loop)
        mcp_url = f"http://localhost:{settings.MCP_SERVER_PORT}/health"
    else:
        mcp_url = f"http://{settings.MCP_SERVER_HOST}:{settings.MCP_SERVER_PORT}/health"

    # Health check for MCP server
    try:
        async with httpx.AsyncClient() as client:
            for _ in range(10):
                try:
                    resp = await client.get(mcp_url, timeout=2.0)
                    if resp.status_code == 200:
                        logger.info("MCP server is healthy and reachable.")
                        break
                except Exception:
                    import asyncio

                    await asyncio.sleep(0.5)
            else:
                logger.warning(
                    f"MCP server healthcheck failed or timed out at {mcp_url}"
                )
    except Exception as e:
        logger.warning(f"MCP server not reachable: {e}")

    yield

    # Shutdown MCP subprocess if started
    if mcp_process:
        logger.info("Shutting down MCP server subprocess...")
        mcp_process.terminate()
        mcp_process.wait(timeout=5)


app = FastAPI(lifespan=lifespan)
tracer = setup_tracing(app)

# CORS for Electron app (update origins for prod)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOW_ORIGINS.split(","),
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(tools.router, prefix="/api/v1", tags=["tools"])

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)
