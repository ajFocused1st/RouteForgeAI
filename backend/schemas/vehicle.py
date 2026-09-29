from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class VehicleBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    max_payload_lbs: float = Field(ge=0)
    max_volume_cubic_ft: float | None = Field(default=None, ge=0)
    max_route_miles: float | None = Field(default=None, ge=0)
    max_route_minutes: int | None = Field(default=None, ge=0)
    active: bool = True


class VehicleCreate(VehicleBase):
    pass


class VehicleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    max_payload_lbs: float | None = Field(default=None, ge=0)
    max_volume_cubic_ft: float | None = Field(default=None, ge=0)
    max_route_miles: float | None = Field(default=None, ge=0)
    max_route_minutes: int | None = Field(default=None, ge=0)
    active: bool | None = None


class VehicleRead(VehicleBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
