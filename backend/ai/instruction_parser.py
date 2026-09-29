from typing import Any

from pydantic import ValidationError

from backend.ai.provider import AIProvider
from backend.schemas.ai import AIStructuredChange
from backend.schemas.ai_instruction import (
    AIInstructionAction,
    AIInstructionParseResult,
)


class AIInstructionParseError(RuntimeError):
    """Raised when AI instruction output cannot be safely validated."""


class StructuredAIInstructionParser:
    def __init__(self, provider: AIProvider):
        self.provider = provider

    def parse(
        self,
        command: str,
        context: dict[str, Any] | None = None,
    ) -> AIInstructionParseResult:
        if not command.strip():
            raise ValueError("Command is required.")

        proposal = self.provider.propose_changes(
            command,
            context=self._parser_context(context),
        )

        try:
            actions = [
                AIInstructionAction.model_validate(
                    self._instruction_action_payload(change)
                )
                for change in proposal.changes
            ]
            return AIInstructionParseResult.model_validate(
                {
                    "original_command": command,
                    "summary": proposal.summary,
                    "proposed_actions": actions,
                    "requires_user_confirmation": True,
                }
            )
        except (KeyError, TypeError, ValidationError, ValueError) as exc:
            raise AIInstructionParseError(
                "AI instruction output failed structured validation."
            ) from exc

    def _parser_context(
        self,
        context: dict[str, Any] | None,
    ) -> dict[str, Any]:
        merged = dict(context or {})
        merged["structured_instruction_parser"] = {
            "allowed_action_types": [
                "set_stop_latest_arrival",
                "set_stop_earliest_arrival",
                "set_route_return_deadline",
                "set_stop_priority",
                "set_stop_service_minutes",
                "assign_vehicle",
                "assign_depot",
            ],
            "time_format": "HH:MM 24-hour local time",
            "example": {
                "command": "Make Stop 6 arrive before 11 and return by 4.",
                "actions": [
                    {
                        "target": "stop",
                        "action": "update",
                        "fields": {
                            "id": 6,
                            "latest_time": "11:00",
                        },
                    },
                    {
                        "target": "route",
                        "action": "update",
                        "fields": {
                            "return_to_depot_deadline": "16:00",
                        },
                    },
                ],
            },
            "safety": (
                "Return proposed changes only. Do not calculate mileage, routes, "
                "ETAs, or optimized stop order."
            ),
        }
        return merged

    def _instruction_action_payload(self, change: AIStructuredChange) -> dict[str, Any]:
        fields = dict(change.fields)
        action_type = fields.pop("instruction_action", None) or self._infer_action_type(
            change.target,
            fields,
        )
        entity_id = fields.pop("id", None)
        entity_id = fields.pop(f"{change.target}_id", entity_id)

        return {
            "action_type": action_type,
            "target": change.target,
            "entity_id": entity_id,
            "fields": fields,
            "rationale": change.rationale,
            "confidence": change.confidence,
        }

    def _infer_action_type(
        self,
        target: str,
        fields: dict[str, Any],
    ) -> str:
        if target == "stop" and "latest_time" in fields:
            return "set_stop_latest_arrival"

        if target == "stop" and "earliest_time" in fields:
            return "set_stop_earliest_arrival"

        if target == "route" and "return_to_depot_deadline" in fields:
            return "set_route_return_deadline"

        if target == "stop" and "priority" in fields:
            return "set_stop_priority"

        if target == "stop" and "service_minutes" in fields:
            return "set_stop_service_minutes"

        if target == "route" and "vehicle_id" in fields:
            return "assign_vehicle"

        if target == "route" and "depot_id" in fields:
            return "assign_depot"

        raise ValueError("Unsupported AI instruction action.")
