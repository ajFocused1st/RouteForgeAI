from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from backend.api.responses import success_response
from backend.database.session import get_db_session
from backend.services.provider_status import ProviderStatusService

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check(request: Request) -> dict:
    settings = request.app.state.settings
    return success_response(
        {
            "service": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
        }
    )


@router.get("/status/providers")
def provider_status(request: Request, db: Session = Depends(get_db_session)) -> dict:
    settings = request.app.state.settings
    return success_response(ProviderStatusService(settings, db).report())
