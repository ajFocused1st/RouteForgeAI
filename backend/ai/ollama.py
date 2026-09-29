import json
from collections.abc import Callable
from dataclasses import dataclass
from json import JSONDecodeError
from typing import Any, TypeVar
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import BaseModel, ConfigDict, ValidationError

from backend.schemas.ai import (
    AIChangeProposal,
    AICommandInterpretation,
    AIResultExplanation,
)

OllamaAITransport = Callable[[str, dict, float], dict]
ResponseModel = TypeVar("ResponseModel", bound=BaseModel)


class AIProviderError(RuntimeError):
    """Raised when local AI assistance cannot produce valid structured data."""


class _InterpretCommandResponse(AICommandInterpretation):
    model_config = ConfigDict(extra="forbid")


class _ExplainResultsResponse(AIResultExplanation):
    model_config = ConfigDict(extra="forbid")


class _ProposeChangesResponse(AIChangeProposal):
    model_config = ConfigDict(extra="forbid")


def _default_transport(url: str, payload: dict, timeout_seconds: float) -> dict:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=timeout_seconds) as response:
        return json.loads(response.read().decode("utf-8"))


@dataclass
class OllamaAIProvider:
    base_url: str = "http://127.0.0.1:11434"
    model: str = "llama3.1"
    timeout_seconds: float = 30.0
    transport: OllamaAITransport = _default_transport
    provider_name: str = "ollama"

    def interpret_command(
        self,
        command: str,
        context: dict[str, Any] | None = None,
    ) -> AICommandInterpretation:
        if not command.strip():
            raise ValueError("Command is required.")

        return self._chat(
            response_model=_InterpretCommandResponse,
            user_content={
                "task": "interpret_command",
                "command": command,
                "context": context or {},
            },
        )

    def explain_results(
        self,
        results: dict[str, Any],
        question: str | None = None,
    ) -> AIResultExplanation:
        return self._chat(
            response_model=_ExplainResultsResponse,
            user_content={
                "task": "explain_results",
                "results": results,
                "question": question,
            },
        )

    def propose_changes(
        self,
        command: str,
        context: dict[str, Any] | None = None,
    ) -> AIChangeProposal:
        if not command.strip():
            raise ValueError("Command is required.")

        proposal = self._chat(
            response_model=_ProposeChangesResponse,
            user_content={
                "task": "propose_structured_changes",
                "command": command,
                "context": context or {},
            },
        )
        return AIChangeProposal(
            summary=proposal.summary,
            changes=proposal.changes,
            requires_user_confirmation=True,
        )

    def _chat(
        self,
        response_model: type[ResponseModel],
        user_content: dict[str, Any],
    ) -> ResponseModel:
        try:
            response = self.transport(
                f"{self.base_url.rstrip('/')}/api/chat",
                self._payload(response_model, user_content),
                self.timeout_seconds,
            )
        except (TimeoutError, HTTPError, URLError, OSError) as exc:
            raise AIProviderError(f"Ollama AI request failed: {exc}") from exc

        return self._parse_response(response, response_model)

    def _payload(
        self,
        response_model: type[BaseModel],
        user_content: dict[str, Any],
    ) -> dict:
        return {
            "model": self.model,
            "stream": False,
            "format": response_model.model_json_schema(),
            "options": {"temperature": 0},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are RouteForge AI's local assistant. You may only "
                        "interpret commands, explain already-calculated backend "
                        "results, and propose structured changes for user review. "
                        "For explanations, use only the supplied application facts "
                        "and never invent numbers, route metrics, capacity, stop "
                        "order, feasibility, mileage, or version differences. "
                        "Do not calculate mileage, travel times, ETAs, route "
                        "geometry, stop order, optimized routes, or driving "
                        "directions. Those values must come from RouteForge's "
                        "routing and optimization services. If a user asks for "
                        "route or mileage calculation, explain that the backend "
                        "routing/optimization engine must perform it."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(user_content, sort_keys=True),
                },
            ],
        }

    def _parse_response(
        self,
        response: dict,
        response_model: type[ResponseModel],
    ) -> ResponseModel:
        content = response.get("message", {}).get("content")
        if not isinstance(content, str):
            raise AIProviderError("Ollama response did not include message content.")

        try:
            data = json.loads(content)
        except JSONDecodeError as exc:
            raise AIProviderError("Ollama response was not valid JSON.") from exc

        try:
            return response_model.model_validate(data)
        except ValidationError as exc:
            raise AIProviderError("Ollama response failed schema validation.") from exc
