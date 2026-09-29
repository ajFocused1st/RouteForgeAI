from fastapi import APIRouter, Depends, HTTPException, status

from backend.ai import (
    AIInstructionParseError,
    AIProviderError,
    AIRouteExplanationError,
    AIRouteExplanationService,
    AIProvider,
    OllamaAIProvider,
    StructuredAIInstructionParser,
)
from backend.api.responses import success_response
from backend.config import Settings, get_settings
from backend.database.session import get_db_session
from backend.schemas.ai import AIRouteExplanationRequest, AIRouteExplanationResponse
from backend.schemas.ai_instruction import (
    AIInstructionParseRequest,
    AIInstructionParseResult,
)
from sqlalchemy.orm import Session

router = APIRouter(prefix="/ai", tags=["ai"])


def get_instruction_parser(
    settings: Settings = Depends(get_settings),
) -> StructuredAIInstructionParser:
    provider = OllamaAIProvider(
        base_url=settings.ollama_url,
        model=settings.ollama_ai_model,
    )
    return StructuredAIInstructionParser(provider)


def get_ai_provider(settings: Settings = Depends(get_settings)) -> AIProvider:
    return OllamaAIProvider(
        base_url=settings.ollama_url,
        model=settings.ollama_ai_model,
    )


@router.post("/instructions/parse")
def parse_ai_instruction(
    instruction_in: AIInstructionParseRequest,
    parser: StructuredAIInstructionParser = Depends(get_instruction_parser),
) -> dict:
    try:
        result = parser.parse(
            instruction_in.command,
            context=instruction_in.context,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except AIInstructionParseError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except AIProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    return success_response(AIInstructionParseResult.model_validate(result))


@router.post("/route-explanations")
def explain_route_question(
    explanation_in: AIRouteExplanationRequest,
    db: Session = Depends(get_db_session),
    provider: AIProvider = Depends(get_ai_provider),
) -> dict:
    try:
        result = AIRouteExplanationService(db, provider).explain(
            question=explanation_in.question,
            route_id=explanation_in.route_id,
            route_version=explanation_in.route_version,
            base_version=explanation_in.base_version,
            comparison_version=explanation_in.comparison_version,
            shipment_weight_lbs=explanation_in.shipment_weight_lbs,
        )
    except AIRouteExplanationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except AIProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    return success_response(AIRouteExplanationResponse.model_validate(result))
