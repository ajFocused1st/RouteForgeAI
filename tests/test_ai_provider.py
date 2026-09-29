from typing import Any

from backend.ai import AIProvider
from backend.schemas.ai import (
    AIChangeProposal,
    AICommandInterpretation,
    AIResultExplanation,
)


class LocalTestAIProvider:
    provider_name = "local-test-ai"

    def interpret_command(
        self,
        command: str,
        context: dict[str, Any] | None = None,
    ) -> AICommandInterpretation:
        return AICommandInterpretation(
            intent="create_stop",
            summary=f"Interpreted: {command}",
            parameters=context or {},
            confidence=0.9,
        )

    def explain_results(
        self,
        results: dict[str, Any],
        question: str | None = None,
    ) -> AIResultExplanation:
        return AIResultExplanation(
            summary="Explained backend results.",
            observations=[f"Question: {question or 'none'}"],
            caveats=[],
        )

    def propose_changes(
        self,
        command: str,
        context: dict[str, Any] | None = None,
    ) -> AIChangeProposal:
        return AIChangeProposal(
            summary="Proposed structured changes for review.",
            changes=[],
            requires_user_confirmation=True,
        )


def test_ai_provider_contract_allows_only_assistance_capabilities():
    provider: AIProvider = LocalTestAIProvider()

    interpretation = provider.interpret_command("Add a stop")
    explanation = provider.explain_results({"total_distance_miles": 12.4})
    proposal = provider.propose_changes("Deactivate vehicle 2")

    assert provider.provider_name == "local-test-ai"
    assert interpretation.intent == "create_stop"
    assert explanation.summary == "Explained backend results."
    assert proposal.requires_user_confirmation is True
    assert not hasattr(provider, "calculate_mileage")
    assert not hasattr(provider, "calculate_route")
    assert not hasattr(provider, "optimize_route")
