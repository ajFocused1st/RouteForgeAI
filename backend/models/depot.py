from datetime import datetime, time

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Time, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.base import Base


class Depot(Base):
    __tablename__ = "depots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    address: Mapped[str] = mapped_column(String(300), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    default_start_time: Mapped[time] = mapped_column(
        Time,
        nullable=False,
        default=time(8, 0),
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
