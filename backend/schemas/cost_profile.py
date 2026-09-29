from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CostProfileBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    operating_cost_per_mile: float = Field(ge=0)
    driver_hourly_rate: float = Field(ge=0)
    tolls: float = Field(default=0, ge=0)
    parking: float = Field(default=0, ge=0)
    route_expenses: float = Field(default=0, ge=0)
    default_service_charge: float = Field(default=0, ge=0)
    active: bool = True


class CostProfileCreate(CostProfileBase):
    pass


class CostProfileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    operating_cost_per_mile: float | None = Field(default=None, ge=0)
    driver_hourly_rate: float | None = Field(default=None, ge=0)
    tolls: float | None = Field(default=None, ge=0)
    parking: float | None = Field(default=None, ge=0)
    route_expenses: float | None = Field(default=None, ge=0)
    default_service_charge: float | None = Field(default=None, ge=0)
    active: bool | None = None


class CostProfileRead(CostProfileBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
