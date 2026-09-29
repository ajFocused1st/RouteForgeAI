from datetime import datetime, time
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

StopType = Literal["pickup", "delivery", "pickup_delivery"]


class StopBase(BaseModel):
    customer_id: int | None = None
    name: str = Field(min_length=1, max_length=120)
    address: str = Field(min_length=1, max_length=300)
    normalized_address: str = Field(min_length=1, max_length=300)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    stop_type: StopType
    quantity: int = Field(default=1, ge=0)
    weight_lbs: float = Field(default=0, ge=0)
    service_minutes: int = Field(default=0, ge=0)
    priority: int = Field(default=0, ge=0)
    earliest_time: time | None = None
    latest_time: time | None = None
    special_instructions: str | None = None
    address_status: str = Field(min_length=1, max_length=40)
    active: bool = True

    @model_validator(mode="after")
    def validate_time_window(self):
        if (
            self.earliest_time is not None
            and self.latest_time is not None
            and self.earliest_time > self.latest_time
        ):
            raise ValueError("earliest_time cannot be after latest_time.")

        return self


class StopCreate(StopBase):
    pass


class StopUpdate(BaseModel):
    customer_id: int | None = None
    name: str | None = Field(default=None, min_length=1, max_length=120)
    address: str | None = Field(default=None, min_length=1, max_length=300)
    normalized_address: str | None = Field(default=None, min_length=1, max_length=300)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    stop_type: StopType | None = None
    quantity: int | None = Field(default=None, ge=0)
    weight_lbs: float | None = Field(default=None, ge=0)
    service_minutes: int | None = Field(default=None, ge=0)
    priority: int | None = Field(default=None, ge=0)
    earliest_time: time | None = None
    latest_time: time | None = None
    special_instructions: str | None = None
    address_status: str | None = Field(default=None, min_length=1, max_length=40)
    active: bool | None = None

    @model_validator(mode="after")
    def validate_time_window(self):
        if (
            self.earliest_time is not None
            and self.latest_time is not None
            and self.earliest_time > self.latest_time
        ):
            raise ValueError("earliest_time cannot be after latest_time.")

        return self


class StopRead(StopBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
