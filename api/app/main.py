from fastapi import FastAPI

from app.routers import health

app = FastAPI(title="Veylith API", version="0.1.0")

# Every router is mounted under /api so the Next.js rewrite can forward /api/* here.
# Add one line per router; keep them alphabetical to avoid merge conflicts.
app.include_router(health.router, prefix="/api")
