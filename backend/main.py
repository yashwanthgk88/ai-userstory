import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from routers import auth, projects, user_stories, analysis, compliance, custom_standards, export, integrations, ai_console, api_keys, webhooks

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

app = FastAPI(
    title="SecureReq AI",
    version="1.0.0",
    description="AI-Powered Security Requirements Generator",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
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
