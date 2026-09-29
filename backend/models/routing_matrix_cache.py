from datetime import datetime

from sqlalchemy import DateTime, Integer, JSON, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.base import Base


class RoutingMatrixCache(Base):
    __tablename__ = "routing_matrix_cache"
    __table_args__ = (
        UniqueConstraint(
            "provider",
            "location_key",
            name="uq_routing_matrix_cache_provider_location_key",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    provider: Mapped[str] = mapped_column(String(80), nullable=False)
    location_key: Mapped[str] = mapped_column(String(1000), nullable=False)
    durations_minutes: Mapped[list[list[float]]] = mapped_column(JSON, nullable=False)
    distances_miles: Mapped[list[list[float]]] = mapped_column(JSON, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
