import base64
from binascii import Error as Base64Error

from fastapi import APIRouter, Depends, HTTPException, Request, status

from backend.api.responses import success_response
from backend.config import Settings, get_settings
from backend.schemas.vision import VisionExtractionRequest, VisionExtractionResult
from backend.vision import (
    OllamaVisionExtractionProvider,
    VisionExtractionError,
    VisionExtractionProvider,
)

router = APIRouter(prefix="/vision", tags=["vision"])
ALLOWED_IMAGE_CONTENT_TYPES = {"image/png", "image/jpeg", "image/webp"}


def get_vision_provider(
    settings: Settings = Depends(get_settings),
) -> VisionExtractionProvider:
    return OllamaVisionExtractionProvider(
        base_url=settings.ollama_url,
        model=settings.ollama_vision_model,
    )


@router.post("/extract")
def extract_screenshot_stops(
    extraction_in: VisionExtractionRequest,
    request: Request,
    provider: VisionExtractionProvider = Depends(get_vision_provider),
) -> dict:
    settings: Settings = request.app.state.settings
    if extraction_in.content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="content_type must be image/png, image/jpeg, or image/webp.",
        )

    try:
        image = base64.b64decode(extraction_in.image_base64, validate=True)
    except (Base64Error, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="image_base64 must contain valid base64 image data.",
        ) from exc

    if len(image) > settings.max_vision_image_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                "Image is too large. Maximum size is "
                f"{settings.max_vision_image_bytes} bytes."
            ),
        )

    try:
        stops = provider.extract_stops(image, content_type=extraction_in.content_type)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except VisionExtractionError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    return success_response(VisionExtractionResult(stops=stops))
