from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import health, jobs
from app.config import settings

app = FastAPI(title="Fuzhify", version=settings.version)

# CORS solo para el frontend de desarrollo
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(jobs.router,   prefix="/api/v1", tags=["jobs"])
