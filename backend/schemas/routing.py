from pydantic import BaseModel, Field, model_validator


class Coordinate(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class TravelTimeMatrix(BaseModel):
    durations_minutes: list[list[float]]

    @model_validator(mode="after")
    def validate_square_matrix(self):
        _validate_square_matrix(self.durations_minutes, "durations_minutes")
        return self


class DistanceMatrix(BaseModel):
    distances_miles: list[list[float]]

    @model_validator(mode="after")
    def validate_square_matrix(self):
        _validate_square_matrix(self.distances_miles, "distances_miles")
        return self


class RouteGeometry(BaseModel):
    polyline: str | None = None
    coordinates: list[Coordinate] = Field(default_factory=list)


class RouteLeg(BaseModel):
    start: Coordinate
    end: Coordinate
    distance_miles: float = Field(ge=0)
    travel_duration_minutes: float = Field(ge=0)
    geometry: RouteGeometry | None = None


def _validate_square_matrix(matrix: list[list[float]], field_name: str) -> None:
    size = len(matrix)
    for row in matrix:
        if len(row) != size:
            raise ValueError(f"{field_name} must be a square matrix.")

        if any(value < 0 for value in row):
            raise ValueError(f"{field_name} cannot contain negative values.")
