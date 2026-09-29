from backend.schemas.ai import (
    AIChangeProposal,
    AICommandInterpretation,
    AIResultExplanation,
    AIRouteExplanationRequest,
    AIRouteExplanationResponse,
    AIStructuredChange,
)
from backend.schemas.ai_instruction import (
    AIInstructionAction,
    AIInstructionParseRequest,
    AIInstructionParseResult,
)
from backend.schemas.customer import CustomerCreate, CustomerRead, CustomerUpdate
from backend.schemas.cost_profile import (
    CostProfileCreate,
    CostProfileRead,
    CostProfileUpdate,
)
from backend.schemas.depot import DepotCreate, DepotRead, DepotUpdate
from backend.schemas.dispatch import (
    DispatchOptimizeRequest,
    DispatchOptimizeResult,
    DispatchVehicleRoute,
)
from backend.schemas.geocoding import (
    GeocodeResult,
    GeocodeReviewRequest,
    GeocodeReviewResult,
    GeocodeReviewStop,
    GeocodeStatus,
    GeocodeValidationStatus,
)
from backend.schemas.route import (
    OptimizedStopRead,
    RouteCreate,
    RouteVersionComparisonRead,
    RouteOptimizationMetrics,
    RouteOptimizationResult,
    RouteVersionScalarComparison,
    RouteVersionStopOrderComparison,
    RouteVersionStopPositionChange,
    RouteRead,
    RouteUpdate,
    RouteVersionRead,
)
from backend.schemas.routing import (
    Coordinate,
    DistanceMatrix,
    RouteGeometry,
    RouteLeg,
    TravelTimeMatrix,
)
from backend.schemas.stop import StopCreate, StopRead, StopUpdate
from backend.schemas.status import ProviderStatusItem, ProviderStatusReport
from backend.schemas.vehicle import VehicleCreate, VehicleRead, VehicleUpdate
from backend.schemas.vision import ExtractedStop, VisionExtractionRequest, VisionExtractionResult

__all__ = [
    "AIChangeProposal",
    "AICommandInterpretation",
    "AIInstructionAction",
    "AIInstructionParseRequest",
    "AIInstructionParseResult",
    "AIResultExplanation",
    "AIRouteExplanationRequest",
    "AIRouteExplanationResponse",
    "AIStructuredChange",
    "CustomerCreate",
    "CustomerRead",
    "CustomerUpdate",
    "CostProfileCreate",
    "CostProfileRead",
    "CostProfileUpdate",
    "DepotCreate",
    "DepotRead",
    "DepotUpdate",
    "DispatchOptimizeRequest",
    "DispatchOptimizeResult",
    "DispatchVehicleRoute",
    "GeocodeResult",
    "GeocodeReviewRequest",
    "GeocodeReviewResult",
    "GeocodeReviewStop",
    "GeocodeStatus",
    "GeocodeValidationStatus",
    "Coordinate",
    "DistanceMatrix",
    "ExtractedStop",
    "OptimizedStopRead",
    "RouteCreate",
    "RouteVersionComparisonRead",
    "RouteGeometry",
    "RouteLeg",
    "RouteOptimizationMetrics",
    "RouteOptimizationResult",
    "RouteRead",
    "RouteUpdate",
    "RouteVersionScalarComparison",
    "RouteVersionStopOrderComparison",
    "RouteVersionStopPositionChange",
    "RouteVersionRead",
    "StopCreate",
    "StopRead",
    "StopUpdate",
    "ProviderStatusItem",
    "ProviderStatusReport",
    "VehicleCreate",
    "VehicleRead",
    "VehicleUpdate",
    "VisionExtractionRequest",
    "VisionExtractionResult",
    "TravelTimeMatrix",
]
