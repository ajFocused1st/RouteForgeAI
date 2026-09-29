from fastapi.testclient import TestClient

from backend.api.ai import get_ai_provider, get_instruction_parser
from backend.api.routes import get_routing_provider
from backend.ai import AIInstructionParseError
from backend.config import Settings
from backend.main import create_app
from backend.schemas.ai import AIChangeProposal, AICommandInterpretation, AIResultExplanation
from backend.schemas.ai_instruction import (
    AIInstructionAction,
    AIInstructionParseResult,
)
from backend.schemas.routing import Coordinate, DistanceMatrix, RouteGeometry, RouteLeg, TravelTimeMatrix


def sqlite_url(path) -> str:
    return f"sqlite:///{path.as_posix()}"


class DeterministicInstructionParser:
    def parse(self, command: str, context: dict | None = None):
        return AIInstructionParseResult(
            original_command=command,
            summary="Update Stop 6 and set a return deadline.",
            proposed_actions=[
                AIInstructionAction(
                    action_type="set_stop_latest_arrival",
                    target="stop",
                    entity_id=6,
                    fields={"latest_time": "11:00"},
                    rationale="Stop 6 should arrive before 11.",
                    confidence=0.93,
                ),
                AIInstructionAction(
                    action_type="set_route_return_deadline",
                    target="route",
                    fields={"return_to_depot_deadline": "16:00"},
                    rationale="Route should return by 4.",
                    confidence=0.91,
                ),
            ],
            requires_user_confirmation=True,
        )


class InvalidInstructionParser:
    def parse(self, command: str, context: dict | None = None):
        raise AIInstructionParseError(
            "AI instruction output failed structured validation."
        )


class CapturingAIProvider:
    provider_name = "capturing-ai"

    def __init__(self):
        self.results = None
        self.question = None

    def interpret_command(
        self,
        command: str,
        context: dict | None = None,
    ) -> AICommandInterpretation:
        raise NotImplementedError

    def explain_results(
        self,
        results: dict,
        question: str | None = None,
    ) -> AIResultExplanation:
        self.results = results
        self.question = question
        return AIResultExplanation(
            summary="Explained from application facts.",
            observations=["Used supplied RouteForge metrics."],
            caveats=["No independent route or mileage calculation was performed."],
        )

    def propose_changes(
        self,
        command: str,
        context: dict | None = None,
    ) -> AIChangeProposal:
        raise NotImplementedError


class OrderedRoutingProvider:
    provider_name = "ordered-routing"

    def travel_time_matrix(self, locations: list[Coordinate]) -> TravelTimeMatrix:
        return TravelTimeMatrix(
            durations_minutes=[
                [0, 1, 10],
                [1, 0, 1],
                [10, 1, 0],
            ]
        )

    def distance_matrix(self, locations: list[Coordinate]) -> DistanceMatrix:
        return DistanceMatrix(
            distances_miles=[
                [0, 5, 20],
                [5, 0, 5],
                [20, 5, 0],
            ]
        )

    def route_geometry(self, locations: list[Coordinate]) -> RouteGeometry:
        return RouteGeometry(coordinates=locations)

    def route_legs(self, locations: list[Coordinate]) -> list[RouteLeg]:
        return [
            RouteLeg(
                start=locations[index],
                end=locations[index + 1],
                distance_miles=5,
                travel_duration_minutes=5,
                geometry=RouteGeometry(
                    coordinates=[locations[index], locations[index + 1]]
                ),
            )
            for index in range(len(locations) - 1)
        ]


class AlternateRoutingProvider(OrderedRoutingProvider):
    provider_name = "alternate-routing"

    def travel_time_matrix(self, locations: list[Coordinate]) -> TravelTimeMatrix:
        return TravelTimeMatrix(
            durations_minutes=[
                [0, 10, 1],
                [10, 0, 1],
                [1, 1, 0],
            ]
        )

    def route_legs(self, locations: list[Coordinate]) -> list[RouteLeg]:
        return [
            RouteLeg(
                start=locations[index],
                end=locations[index + 1],
                distance_miles=7,
                travel_duration_minutes=7,
                geometry=RouteGeometry(
                    coordinates=[locations[index], locations[index + 1]]
                ),
            )
            for index in range(len(locations) - 1)
        ]


def create_ai_route(client: TestClient, first_stop_type: str = "pickup") -> dict:
    depot = client.post(
        "/api/depots",
        json={
            "name": "Main Depot",
            "address": "123 Dispatch Way, Tampa, FL",
            "latitude": 27.9506,
            "longitude": -82.4572,
            "default_start_time": "08:00:00",
            "active": True,
        },
    ).json()["data"]
    vehicle = client.post(
        "/api/vehicles",
        json={
            "name": "Cargo Van 1",
            "max_payload_lbs": 300,
            "active": True,
        },
    ).json()["data"]
    first_stop = client.post(
        "/api/stops",
        json=stop_payload("First Stop", first_stop_type, 100),
    ).json()["data"]
    second_stop = client.post(
        "/api/stops",
        json=stop_payload("Second Stop", "delivery", 100),
    ).json()["data"]
    route = client.post(
        "/api/routes",
        json={
            "name": "AI Route",
            "depot_id": depot["id"],
            "vehicle_id": vehicle["id"],
            "stop_ids": [first_stop["id"], second_stop["id"]],
            "active": True,
        },
    ).json()["data"]
    return {
        "route": route,
        "depot": depot,
        "vehicle": vehicle,
        "stops": [first_stop, second_stop],
    }


def stop_payload(name: str, stop_type: str, weight_lbs: float) -> dict:
    return {
        "name": name,
        "address": "123 Dispatch Way, Tampa, FL",
        "normalized_address": "123 Dispatch Way, Tampa, FL 33602",
        "latitude": 27.9506,
        "longitude": -82.4572,
        "stop_type": stop_type,
        "quantity": 1,
        "weight_lbs": weight_lbs,
        "service_minutes": 15,
        "priority": 1,
        "address_status": "confirmed",
        "active": True,
    }


def test_parse_ai_instruction_returns_validated_proposed_actions():
    app = create_app(Settings(database_url="sqlite:///:memory:"))
    app.dependency_overrides[get_instruction_parser] = (
        lambda: DeterministicInstructionParser()
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/ai/instructions/parse",
            json={
                "command": "Make Stop 6 arrive before 11 and return by 4.",
                "context": {"route_id": 12},
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["data"]["requires_user_confirmation"] is True
    assert body["data"]["proposed_actions"][0] == {
        "action_type": "set_stop_latest_arrival",
        "target": "stop",
        "entity_id": 6,
        "fields": {"latest_time": "11:00"},
        "rationale": "Stop 6 should arrive before 11.",
        "confidence": 0.93,
    }

    app.dependency_overrides.clear()


def test_parse_ai_instruction_rejects_invalid_ai_output_safely():
    app = create_app(Settings(database_url="sqlite:///:memory:"))
    app.dependency_overrides[get_instruction_parser] = lambda: InvalidInstructionParser()

    with TestClient(app) as client:
        response = client.post(
            "/api/ai/instructions/parse",
            json={"command": "Make Stop 6 arrive before 11."},
        )

    assert response.status_code == 422
    assert response.json()["error"]["message"] == (
        "AI instruction output failed structured validation."
    )

    app.dependency_overrides.clear()


def test_ai_route_explanation_uses_app_deadhead_facts(tmp_path):
    app = create_app(Settings(database_url=sqlite_url(tmp_path / "deadhead.db")))
    ai_provider = CapturingAIProvider()
    app.dependency_overrides[get_ai_provider] = lambda: ai_provider
    app.dependency_overrides[get_routing_provider] = lambda: OrderedRoutingProvider()

    with TestClient(app) as client:
        dependencies = create_ai_route(client)
        route = dependencies["route"]
        first_stop_id = dependencies["stops"][0]["id"]
        optimize_response = client.post(f"/api/routes/{route['id']}/optimize")
        response = client.post(
            "/api/ai/route-explanations",
            json={
                "question": "Which stop creates the most deadhead?",
                "route_id": route["id"],
            },
        )

    assert optimize_response.status_code == 200
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["intent"] == "deadhead"
    assert data["explanation"]["summary"] == "Explained from application facts."
    assert data["application_facts"]["most_deadhead_stop"] == {
        "stop_id": first_stop_id,
        "unloaded_miles_into_stop": 5.0,
    }
    assert ai_provider.results["most_deadhead_stop"]["stop_id"] == first_stop_id
    assert "ai_grounding_rule" in ai_provider.results

    app.dependency_overrides.clear()


def test_ai_route_explanation_uses_app_version_comparison_facts(tmp_path):
    app = create_app(Settings(database_url=sqlite_url(tmp_path / "versions.db")))
    ai_provider = CapturingAIProvider()
    provider_holder = {"provider": OrderedRoutingProvider()}
    app.dependency_overrides[get_ai_provider] = lambda: ai_provider
    app.dependency_overrides[get_routing_provider] = lambda: provider_holder["provider"]

    with TestClient(app) as client:
        dependencies = create_ai_route(client)
        route = dependencies["route"]
        first_stop_id = dependencies["stops"][0]["id"]
        second_stop_id = dependencies["stops"][1]["id"]
        first = client.post(f"/api/routes/{route['id']}/optimize")
        provider_holder["provider"] = AlternateRoutingProvider()
        second = client.post(f"/api/routes/{route['id']}/optimize")
        response = client.post(
            "/api/ai/route-explanations",
            json={
                "question": "What changed from Version 1 to Version 2?",
                "route_id": route["id"],
                "base_version": 1,
                "comparison_version": 2,
            },
        )

    assert first.status_code == 200
    assert second.status_code == 200
    assert response.status_code == 200
    facts = response.json()["data"]["application_facts"]
    assert facts["miles"] == {"base": 15.0, "comparison": 21.0, "difference": 6.0}
    assert facts["drive_time_minutes"] == {"base": 15, "comparison": 21, "difference": 6}
    assert facts["stop_order"]["base"] == [first_stop_id, second_stop_id]
    assert facts["stop_order"]["comparison"] == [second_stop_id, first_stop_id]
    assert ai_provider.question == "What changed from Version 1 to Version 2?"

    app.dependency_overrides.clear()


def test_ai_route_explanation_uses_app_capacity_facts_for_shipment_fit(tmp_path):
    app = create_app(Settings(database_url=sqlite_url(tmp_path / "fit.db")))
    ai_provider = CapturingAIProvider()
    app.dependency_overrides[get_ai_provider] = lambda: ai_provider
    app.dependency_overrides[get_routing_provider] = lambda: OrderedRoutingProvider()

    with TestClient(app) as client:
        route = create_ai_route(client)["route"]
        client.post(f"/api/routes/{route['id']}/optimize")
        response = client.post(
            "/api/ai/route-explanations",
            json={
                "question": "Can this shipment fit?",
                "route_id": route["id"],
                "shipment_weight_lbs": 50,
            },
        )

    assert response.status_code == 200
    facts = response.json()["data"]["application_facts"]
    assert facts["current_payload_lbs"] == 200.0
    assert facts["remaining_capacity_lbs"] == 100.0
    assert facts["shipment_weight_lbs"] == 50.0
    assert facts["fits"] is True
    assert ai_provider.results["fits"] is True

    app.dependency_overrides.clear()


def test_ai_route_explanation_uses_app_infeasible_facts(tmp_path):
    app = create_app(Settings(database_url=sqlite_url(tmp_path / "infeasible.db")))
    ai_provider = CapturingAIProvider()
    app.dependency_overrides[get_ai_provider] = lambda: ai_provider
    app.dependency_overrides[get_routing_provider] = lambda: OrderedRoutingProvider()

    with TestClient(app) as client:
        dependencies = create_ai_route(client)
        route = dependencies["route"]
        first_stop = dependencies["stops"][0]
        client.put(f"/api/stops/{first_stop['id']}", json={"latest_time": "08:00:00"})
        optimize_response = client.post(f"/api/routes/{route['id']}/optimize")
        response = client.post(
            "/api/ai/route-explanations",
            json={
                "question": "Why is this route infeasible?",
                "route_id": route["id"],
            },
        )

    assert optimize_response.status_code == 409
    assert response.status_code == 200
    facts = response.json()["data"]["application_facts"]
    assert facts["solver_status"] == "no_feasible_solution"
    assert facts["is_infeasible"] is True
    assert facts["stops"][0]["latest_time"] == "08:00:00"
    assert ai_provider.results["solver_status"] == "no_feasible_solution"

    app.dependency_overrides.clear()
