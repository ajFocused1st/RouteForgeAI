from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.base import Base


class CostProfile(Base):
    __tablename__ = "cost_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    operating_cost_per_mile: Mapped[float] = mapped_column(Float, nullable=False)
    driver_hourly_rate: Mapped[float] = mapped_column(Float, nullable=False)
    tolls: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    parking: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    route_expenses: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    default_service_charge: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0,
    )
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
