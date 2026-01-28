import logging
import subprocess

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from config import settings
from routers import auth, projects, user_stories, analysis, compliance, custom_standards, export, integrations, ai_console, api_keys, webhooks

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Run database migrations on startup
    logger.info("Running database migrations...")
    try:
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            cwd="/app"  # Railway working directory
        )
        if result.returncode == 0:
            logger.info("Migrations completed successfully")
        else:
            logger.warning("Migration output: %s", result.stdout)
            if result.stderr:
                logger.warning("Migration stderr: %s", result.stderr)
    except Exception as e:
        logger.warning("Could not run migrations: %s", e)
    yield

app = FastAPI(
    title="SecureReq AI",
    version="1.0.0",
    description="AI-Powered Security Requirements Generator",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(projects.router, prefix="/api")
app.include_router(user_stories.router, prefix="/api")
app.include_router(analysis.router, prefix="/api")
app.include_router(compliance.router, prefix="/api")
app.include_router(custom_standards.router, prefix="/api")
app.include_router(export.router, prefix="/api")
app.include_router(integrations.router, prefix="/api")
app.include_router(ai_console.router, prefix="/api")
app.include_router(api_keys.router, prefix="/api")
app.include_router(webhooks.router, prefix="/api")


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "securereq-ai"}
