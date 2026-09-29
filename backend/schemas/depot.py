from datetime import datetime, time

from pydantic import BaseModel, ConfigDict, Field


class DepotBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    address: str = Field(min_length=1, max_length=300)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    default_start_time: time = time(8, 0)
    active: bool = True


class DepotCreate(DepotBase):
    pass


class DepotUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    address: str | None = Field(default=None, min_length=1, max_length=300)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    default_start_time: time | None = None
    active: bool | None = None


class DepotRead(DepotBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
