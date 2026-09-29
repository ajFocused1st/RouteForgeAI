from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


ProviderStatusState = Literal["ok", "warning", "unavailable"]


class ProviderStatusItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    status: ProviderStatusState
    message: str
    details: dict = Field(default_factory=dict)


class ProviderStatusReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    overall_status: ProviderStatusState
    providers: list[ProviderStatusItem]
