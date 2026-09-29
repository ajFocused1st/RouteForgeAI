from typing import Any, Protocol

from backend.schemas.ai import (
    AIChangeProposal,
    AICommandInterpretation,
    AIResultExplanation,
)


class AIProvider(Protocol):
    """Provider contract for local AI assistance without route calculation."""

    provider_name: str

    def interpret_command(
        self,
        command: str,
        context: dict[str, Any] | None = None,
    ) -> AICommandInterpretation:
        """Interpret a user command without calculating mileage or routes."""

    def explain_results(
        self,
        results: dict[str, Any],
        question: str | None = None,
    ) -> AIResultExplanation:
        """Explain backend-calculated results without recomputing them."""

    def propose_changes(
        self,
        command: str,
        context: dict[str, Any] | None = None,
    ) -> AIChangeProposal:
        """Return structured change proposals requiring caller confirmation."""
