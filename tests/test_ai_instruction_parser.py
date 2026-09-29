import pytest

from backend.ai import AIInstructionParseError, StructuredAIInstructionParser
from backend.schemas.ai import AIChangeProposal, AIStructuredChange


class ExampleInstructionProvider:
    provider_name = "example-ai"

    def __init__(self, changes: list[AIStructuredChange]):
        self.changes = changes
        self.context = None

    def interpret_command(self, command, context=None):
        raise NotImplementedError

    def explain_results(self, results, question=None):
        raise NotImplementedError

    def propose_changes(self, command, context=None):
        self.context = context
        return AIChangeProposal(
            summary="Update Stop 6 and set a route return deadline.",
            changes=self.changes,
            requires_user_confirmation=False,
        )


def test_instruction_parser_structures_example_command():
    provider = ExampleInstructionProvider(
        [
            AIStructuredChange(
                target="stop",
                action="update",
                fields={"id": 6, "latest_time": "11:00"},
                rationale="Stop 6 should arrive before 11.",
                confidence=0.92,
            ),
            AIStructuredChange(
                target="route",
                action="update",
                fields={"return_to_depot_deadline": "16:00"},
                rationale="Route should return by 4.",
                confidence=0.9,
            ),
        ]
    )

    result = StructuredAIInstructionParser(provider).parse(
        "Make Stop 6 arrive before 11 and return by 4.",
        context={"route_id": 12},
    )

    assert result.original_command == "Make Stop 6 arrive before 11 and return by 4."
    assert result.requires_user_confirmation is True
    assert result.proposed_actions[0].model_dump() == {
        "action_type": "set_stop_latest_arrival",
        "target": "stop",
        "entity_id": 6,
        "fields": {"latest_time": "11:00"},
        "rationale": "Stop 6 should arrive before 11.",
        "confidence": 0.92,
    }
    assert result.proposed_actions[1].model_dump() == {
        "action_type": "set_route_return_deadline",
        "target": "route",
        "entity_id": None,
        "fields": {"return_to_depot_deadline": "16:00"},
        "rationale": "Route should return by 4.",
        "confidence": 0.9,
    }
    assert provider.context["route_id"] == 12
    assert provider.context["structured_instruction_parser"]["time_format"] == (
        "HH:MM 24-hour local time"
    )


def test_instruction_parser_accepts_explicit_instruction_action():
    provider = ExampleInstructionProvider(
        [
            AIStructuredChange(
                target="stop",
                action="update",
                fields={
                    "id": 4,
                    "instruction_action": "set_stop_earliest_arrival",
                    "earliest_time": "09:30",
                },
                confidence=0.81,
            )
        ]
    )

    result = StructuredAIInstructionParser(provider).parse(
        "Do not arrive at Stop 4 before 9:30."
    )

    assert result.proposed_actions[0].action_type == "set_stop_earliest_arrival"
    assert result.proposed_actions[0].fields == {"earliest_time": "09:30"}


@pytest.mark.parametrize(
    "change",
    [
        AIStructuredChange(
            target="stop",
            action="update",
            fields={"id": 6, "latest_time": "11ish"},
            confidence=0.9,
        ),
        AIStructuredChange(
            target="stop",
            action="update",
            fields={"latest_time": "11:00"},
            confidence=0.9,
        ),
        AIStructuredChange(
            target="stop",
            action="update",
            fields={"id": 6, "latest_time": "11:00", "route_miles": 12},
            confidence=0.9,
        ),
        AIStructuredChange(
            target="route",
            action="update",
            fields={"optimized_stop_order": [1, 2, 3]},
            confidence=0.9,
        ),
    ],
)
def test_instruction_parser_rejects_invalid_ai_output_safely(change):
    provider = ExampleInstructionProvider([change])

    with pytest.raises(AIInstructionParseError, match="structured validation"):
        StructuredAIInstructionParser(provider).parse("Update this route.")


def test_instruction_parser_rejects_empty_ai_action_list_safely():
    provider = ExampleInstructionProvider([])

    with pytest.raises(AIInstructionParseError, match="structured validation"):
        StructuredAIInstructionParser(provider).parse("Make Stop 6 arrive before 11.")


def test_instruction_parser_requires_command_text():
    provider = ExampleInstructionProvider([])

    with pytest.raises(ValueError, match="Command is required"):
        StructuredAIInstructionParser(provider).parse("  ")
