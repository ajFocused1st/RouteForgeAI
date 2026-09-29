from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


InstructionTarget = Literal["route", "stop", "vehicle", "depot"]
InstructionActionType = Literal[
    "set_stop_latest_arrival",
    "set_stop_earliest_arrival",
    "set_route_return_deadline",
    "set_stop_priority",
    "set_stop_service_minutes",
    "assign_vehicle",
    "assign_depot",
]

TIME_FIELDS = {
    "earliest_time",
    "latest_time",
    "return_to_depot_deadline",
}


class AIInstructionAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_type: InstructionActionType
    target: InstructionTarget
    entity_id: int | None = Field(default=None, gt=0)
    fields: dict[str, Any]
    rationale: str | None = None
    confidence: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def validate_action_fields(self):
        allowed_fields_by_action = {
            "set_stop_latest_arrival": {"latest_time"},
            "set_stop_earliest_arrival": {"earliest_time"},
            "set_route_return_deadline": {"return_to_depot_deadline"},
            "set_stop_priority": {"priority"},
            "set_stop_service_minutes": {"service_minutes"},
            "assign_vehicle": {"vehicle_id"},
            "assign_depot": {"depot_id"},
        }
        target_by_action = {
            "set_stop_latest_arrival": "stop",
            "set_stop_earliest_arrival": "stop",
            "set_route_return_deadline": "route",
            "set_stop_priority": "stop",
            "set_stop_service_minutes": "stop",
            "assign_vehicle": "route",
            "assign_depot": "route",
        }

        expected_target = target_by_action[self.action_type]
        if self.target != expected_target:
            raise ValueError(
                f"{self.action_type} must target {expected_target}, not {self.target}."
            )

        allowed_fields = allowed_fields_by_action[self.action_type]
        field_names = set(self.fields)
        if field_names != allowed_fields:
            raise ValueError(
                f"{self.action_type} fields must be exactly {sorted(allowed_fields)}."
            )

        if self.target == "stop" and self.entity_id is None:
            raise ValueError("Stop actions require entity_id.")

        if self.action_type in {"assign_vehicle", "assign_depot"} and self.entity_id is None:
            raise ValueError("Route assignment actions require route entity_id.")

        for field_name in TIME_FIELDS & field_names:
            self._validate_time(field_name, self.fields[field_name])

        self._validate_non_negative_int("priority")
        self._validate_non_negative_int("service_minutes")
        self._validate_positive_int("vehicle_id")
        self._validate_positive_int("depot_id")

        return self

    def _validate_time(self, field_name: str, value: Any) -> None:
        if not isinstance(value, str):
            raise ValueError(f"{field_name} must be an HH:MM string.")

        parts = value.split(":")
        if len(parts) != 2 or not all(part.isdigit() for part in parts):
            raise ValueError(f"{field_name} must be an HH:MM string.")

        hour = int(parts[0])
        minute = int(parts[1])
        if hour < 0 or hour > 23 or minute < 0 or minute > 59:
            raise ValueError(f"{field_name} must be an HH:MM string.")

    def _validate_non_negative_int(self, field_name: str) -> None:
        if field_name not in self.fields:
            return

        value = self.fields[field_name]
        if not isinstance(value, int) or value < 0:
            raise ValueError(f"{field_name} must be a non-negative integer.")

    def _validate_positive_int(self, field_name: str) -> None:
        if field_name not in self.fields:
            return

        value = self.fields[field_name]
        if not isinstance(value, int) or value <= 0:
            raise ValueError(f"{field_name} must be a positive integer.")


class AIInstructionParseResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    original_command: str = Field(min_length=1)
    summary: str
    proposed_actions: list[AIInstructionAction]
    requires_user_confirmation: bool = True

    @field_validator("proposed_actions")
    @classmethod
    def require_actions(
        cls,
        value: list[AIInstructionAction],
    ) -> list[AIInstructionAction]:
        if not value:
            raise ValueError("At least one proposed action is required.")

        return value


class AIInstructionParseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    command: str = Field(min_length=1)
    context: dict[str, Any] = Field(default_factory=dict)
