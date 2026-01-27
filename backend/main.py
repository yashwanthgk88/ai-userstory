import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from routers import auth, projects, user_stories, analysis, compliance, custom_standards, export

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

app = FastAPI(title="SecureReq AI", version="1.0.0", description="AI-Powered Security Requirements Generator")

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


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "securereq-ai"}
