from fastapi import FastAPI

from app.config import settings

app = FastAPI(title="Fuzhify", version=settings.version)


@app.get("/health")
async def health():
    return {"status": "ok", "version": settings.version}
