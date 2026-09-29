from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


AIChangeTarget = Literal[
    "route",
    "stop",
    "vehicle",
    "driver",
    "customer",
    "depot",
    "cost_profile",
    "settings",
]
AIChangeAction = Literal[
    "create",
    "update",
    "deactivate",
    "assign",
    "remove",
    "reorder",
]


class AIStructuredChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target: AIChangeTarget
    action: AIChangeAction
    fields: dict[str, Any] = Field(default_factory=dict)
    rationale: str | None = None
    confidence: float = Field(ge=0, le=1)


class AICommandInterpretation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent: str
    summary: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    proposed_changes: list[AIStructuredChange] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)


class AIResultExplanation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str
    observations: list[str] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)


class AIChangeProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str
    changes: list[AIStructuredChange] = Field(default_factory=list)
    requires_user_confirmation: bool = True


class AIRouteExplanationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1)
    route_id: int = Field(gt=0)
    route_version: int | None = Field(default=None, gt=0)
    base_version: int | None = Field(default=None, gt=0)
    comparison_version: int | None = Field(default=None, gt=0)
    shipment_weight_lbs: float | None = Field(default=None, ge=0)


class AIRouteExplanationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str
    intent: str
    explanation: AIResultExplanation
    application_facts: dict[str, Any]
