import json

import pytest

from backend.ai import AIProviderError, OllamaAIProvider


def test_ollama_ai_provider_interprets_commands_with_structured_request():
    captured = {}

    def transport(url: str, payload: dict, timeout_seconds: float) -> dict:
        captured["url"] = url
        captured["payload"] = payload
        captured["timeout_seconds"] = timeout_seconds
        return {
            "message": {
                "content": json.dumps(
                    {
                        "intent": "create_stop",
                        "summary": "Create a new delivery stop.",
                        "parameters": {"name": "Acme"},
                        "proposed_changes": [
                            {
                                "target": "stop",
                                "action": "create",
                                "fields": {"name": "Acme"},
                                "rationale": "User asked to add a stop.",
                                "confidence": 0.88,
                            }
                        ],
                        "confidence": 0.91,
                    }
                )
            }
        }

    provider = OllamaAIProvider(
        base_url="http://localhost:11434",
        model="llama3.1",
        timeout_seconds=7,
        transport=transport,
    )

    result = provider.interpret_command(
        "Add Acme as a delivery stop.",
        context={"screen": "stops"},
    )

    assert captured["url"] == "http://localhost:11434/api/chat"
    assert captured["timeout_seconds"] == 7
    assert captured["payload"]["model"] == "llama3.1"
    assert captured["payload"]["stream"] is False
    assert captured["payload"]["options"] == {"temperature": 0}
    assert "Do not calculate mileage" in captured["payload"]["messages"][0]["content"]
    assert "routing and optimization services" in captured["payload"]["messages"][0]["content"]
    assert captured["payload"]["format"]["properties"]["intent"]["type"] == "string"
    assert json.loads(captured["payload"]["messages"][1]["content"]) == {
        "command": "Add Acme as a delivery stop.",
        "context": {"screen": "stops"},
        "task": "interpret_command",
    }
    assert result.intent == "create_stop"
    assert result.proposed_changes[0].target == "stop"
    assert result.confidence == 0.91


def test_ollama_ai_provider_explains_existing_results_without_recomputing():
    def transport(url: str, payload: dict, timeout_seconds: float) -> dict:
        user_payload = json.loads(payload["messages"][1]["content"])
        assert user_payload["task"] == "explain_results"
        assert user_payload["results"] == {"total_distance_miles": 42.5}
        return {
            "message": {
                "content": json.dumps(
                    {
                        "summary": "The route is 42.5 miles based on backend results.",
                        "observations": ["Mileage came from the route result."],
                        "caveats": ["No independent mileage calculation was performed."],
                    }
                )
            }
        }

    provider = OllamaAIProvider(transport=transport)

    result = provider.explain_results(
        {"total_distance_miles": 42.5},
        question="How long is this route?",
    )

    assert result.summary == "The route is 42.5 miles based on backend results."
    assert "No independent mileage calculation" in result.caveats[0]


def test_ollama_ai_provider_forces_change_proposals_to_need_confirmation():
    def transport(url: str, payload: dict, timeout_seconds: float) -> dict:
        return {
            "message": {
                "content": json.dumps(
                    {
                        "summary": "Deactivate the selected vehicle.",
                        "changes": [
                            {
                                "target": "vehicle",
                                "action": "deactivate",
                                "fields": {"id": 3},
                                "rationale": "User requested deactivation.",
                                "confidence": 0.95,
                            }
                        ],
                        "requires_user_confirmation": False,
                    }
                )
            }
        }

    provider = OllamaAIProvider(transport=transport)

    result = provider.propose_changes("Deactivate vehicle 3.")

    assert result.requires_user_confirmation is True
    assert result.changes[0].target == "vehicle"


def test_ollama_ai_provider_rejects_non_json_response():
    provider = OllamaAIProvider(
        transport=lambda url, payload, timeout_seconds: {
            "message": {"content": "not json"}
        }
    )

    with pytest.raises(AIProviderError, match="not valid JSON"):
        provider.interpret_command("Add a stop.")


def test_ollama_ai_provider_rejects_schema_invalid_response():
    provider = OllamaAIProvider(
        transport=lambda url, payload, timeout_seconds: {
            "message": {"content": json.dumps({"intent": "missing fields"})}
        }
    )

    with pytest.raises(AIProviderError, match="schema validation"):
        provider.interpret_command("Add a stop.")


def test_ollama_ai_provider_requires_command_text():
    provider = OllamaAIProvider(transport=lambda url, payload, timeout_seconds: {})

    with pytest.raises(ValueError, match="Command is required"):
        provider.interpret_command("  ")

    with pytest.raises(ValueError, match="Command is required"):
        provider.propose_changes("")
