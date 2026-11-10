from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["health"])


class Health(BaseModel):
    status: str


@router.get("/health", response_model=Health)
def health() -> Health:
    """Used by the uptime pinger and by the web app's hello-world check."""
    return Health(status="ok")
