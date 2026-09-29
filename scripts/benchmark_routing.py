from __future__ import annotations

import argparse
import ctypes
import math
import platform
import sys
import tempfile
import time
import tracemalloc
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.database.session import (
    create_database_engine,
    create_session_factory,
)
from backend.database.base import Base
from backend.models.depot import Depot
from backend.models.stop import Stop
from backend.optimization.single_vehicle import SingleVehicleOptimizer
from backend.routing.valhalla import ValhallaRoutingProvider
from backend.schemas.routing import Coordinate, DistanceMatrix, RouteGeometry, RouteLeg, TravelTimeMatrix
from backend.services.routing_matrix import RoutingMatrixService


STOP_COUNTS = [10, 25, 50, 100]
MILES_PER_DEGREE_LATITUDE = 69.0


@dataclass(frozen=True)
class BenchmarkResult:
    stop_count: int
    matrix_generation_seconds: float
    solver_seconds: float
    total_request_seconds: float
    peak_python_memory_mb: float
    process_memory_delta_mb: float | None
    solver_status: str
    cache_hit: bool


class DeterministicRoutingProvider:
    provider_name = "benchmark-deterministic"

    def travel_time_matrix(self, locations: list[Coordinate]) -> TravelTimeMatrix:
        distances = self._distance_rows(locations)
        return TravelTimeMatrix(
            durations_minutes=[
                [round(distance / 32 * 60, 3) for distance in row]
                for row in distances
            ]
        )

    def distance_matrix(self, locations: list[Coordinate]) -> DistanceMatrix:
        return DistanceMatrix(distances_miles=self._distance_rows(locations))

    def route_geometry(self, locations: list[Coordinate]) -> RouteGeometry:
        return RouteGeometry(coordinates=locations)

    def route_legs(self, locations: list[Coordinate]) -> list[RouteLeg]:
        distances = self._distance_rows(locations)
        return [
            RouteLeg(
                start=locations[index],
                end=locations[index + 1],
                distance_miles=distances[index][index + 1],
                travel_duration_minutes=round(distances[index][index + 1] / 32 * 60, 3),
                geometry=RouteGeometry(coordinates=[locations[index], locations[index + 1]]),
            )
            for index in range(len(locations) - 1)
        ]

    def _distance_rows(self, locations: list[Coordinate]) -> list[list[float]]:
        center_latitude = sum(location.latitude for location in locations) / len(locations)
        miles_per_degree_longitude = (
            MILES_PER_DEGREE_LATITUDE * math.cos(math.radians(center_latitude))
        )
        rows: list[list[float]] = []
        for origin in locations:
            row = []
            for destination in locations:
                latitude_miles = (
                    destination.latitude - origin.latitude
                ) * MILES_PER_DEGREE_LATITUDE
                longitude_miles = (
                    destination.longitude - origin.longitude
                ) * miles_per_degree_longitude
                row.append(round(math.hypot(latitude_miles, longitude_miles), 3))
            rows.append(row)
        return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark RouteForge routing.")
    parser.add_argument(
        "--provider",
        choices=["auto", "deterministic", "valhalla"],
        default="auto",
        help="Routing provider to benchmark.",
    )
    parser.add_argument(
        "--output",
        default="docs/performance.md",
        help="Markdown output path.",
    )
    args = parser.parse_args()

    provider, provider_note = select_provider(args.provider)
    results = [run_benchmark(stop_count, provider) for stop_count in STOP_COUNTS]
    write_report(Path(args.output), provider.provider_name, provider_note, results)


def select_provider(provider_name: str):
    if provider_name == "deterministic":
        return DeterministicRoutingProvider(), (
            "Synthetic in-process provider. This isolates RouteForge matrix caching "
            "and OR-Tools solver timing from external routing service latency."
        )

    if provider_name in {"auto", "valhalla"}:
        valhalla = ValhallaRoutingProvider(timeout_seconds=2.0)
        try:
            valhalla.health_check()
            return valhalla, "Live local Valhalla provider."
        except RuntimeError as exc:
            if provider_name == "valhalla":
                raise
            return DeterministicRoutingProvider(), (
                "Valhalla was unavailable during the benchmark, so results use the "
                f"synthetic in-process provider. Valhalla check: {exc}"
            )

    raise ValueError(f"Unsupported provider: {provider_name}")


def run_benchmark(stop_count: int, provider) -> BenchmarkResult:
    with tempfile.TemporaryDirectory(prefix="routeforge-benchmark-") as temp_dir:
        database_url = f"sqlite:///{Path(temp_dir, f'benchmark-{stop_count}.db').as_posix()}"
        import backend.models  # noqa: F401

        engine = create_database_engine(database_url)
        Base.metadata.create_all(bind=engine)
        session_factory = create_session_factory(engine)
        depot = benchmark_depot()
        stops = benchmark_stops(stop_count)

        try:
            tracemalloc.start()
            process_memory_before = process_memory_mb()
            total_start = time.perf_counter()

            with session_factory() as session:
                matrix_start = time.perf_counter()
                matrix_result = RoutingMatrixService(
                    session,
                    provider,
                ).build_for_depot_and_stops(depot, stops)
                matrix_end = time.perf_counter()

                solver_start = time.perf_counter()
                solver_result = SingleVehicleOptimizer().solve(
                    matrix_result.travel_time_matrix.durations_minutes,
                    depot_index=0,
                    stop_weights=[0, *[stop.weight_lbs for stop in stops]],
                    vehicle_payload_capacity=100000,
                    service_durations=[0, *[stop.service_minutes for stop in stops]],
                    route_start_time=480,
                    required_end_time=1440,
                )
                solver_end = time.perf_counter()

            total_end = time.perf_counter()
            _, peak_memory_bytes = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            process_memory_after = process_memory_mb()
        finally:
            engine.dispose()

    return BenchmarkResult(
        stop_count=stop_count,
        matrix_generation_seconds=matrix_end - matrix_start,
        solver_seconds=solver_end - solver_start,
        total_request_seconds=total_end - total_start,
        peak_python_memory_mb=peak_memory_bytes / 1024 / 1024,
        process_memory_delta_mb=memory_delta(process_memory_before, process_memory_after),
        solver_status=str(solver_result.solver_status),
        cache_hit=matrix_result.cache_hit,
    )


def benchmark_depot() -> Depot:
    return Depot(
        name="Benchmark Depot",
        address="4100 George J Bean Parkway, Tampa, FL 33607",
        latitude=27.9755,
        longitude=-82.5332,
    )


def benchmark_stops(stop_count: int) -> list[Stop]:
    center_latitude = 27.9506
    center_longitude = -82.4572
    stops = []
    for index in range(stop_count):
        angle = index * 2 * math.pi / stop_count
        ring = 0.04 + (index % 5) * 0.018
        latitude = center_latitude + math.sin(angle) * ring
        longitude = center_longitude + math.cos(angle) * ring
        stops.append(
            Stop(
                id=index + 1,
                name=f"Benchmark Stop {index + 1}",
                address=f"{index + 1} Benchmark Way, Tampa, FL",
                normalized_address=f"{index + 1} Benchmark Way, Tampa, FL",
                latitude=latitude,
                longitude=longitude,
                stop_type="delivery",
                quantity=1,
                weight_lbs=25,
                service_minutes=5,
                priority=1,
                address_status="confirmed",
            )
        )
    return stops


def process_memory_mb() -> float | None:
    if platform.system() == "Windows":
        return windows_process_memory_mb()

    try:
        import resource

        usage = resource.getrusage(resource.RUSAGE_SELF)
        value = float(usage.ru_maxrss)
        if platform.system() == "Darwin":
            return value / 1024 / 1024
        return value / 1024
    except (ImportError, OSError):
        return None


def windows_process_memory_mb() -> float | None:
    class ProcessMemoryCounters(ctypes.Structure):
        _fields_ = [
            ("cb", ctypes.c_ulong),
            ("PageFaultCount", ctypes.c_ulong),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    counters = ProcessMemoryCounters()
    counters.cb = ctypes.sizeof(ProcessMemoryCounters)
    handle = ctypes.windll.kernel32.GetCurrentProcess()
    success = ctypes.windll.psapi.GetProcessMemoryInfo(
        handle,
        ctypes.byref(counters),
        counters.cb,
    )
    if not success:
        return None

    return counters.WorkingSetSize / 1024 / 1024


def memory_delta(before: float | None, after: float | None) -> float | None:
    if before is None or after is None:
        return None

    return after - before


def write_report(
    output_path: Path,
    provider_name: str,
    provider_note: str,
    results: list[BenchmarkResult],
) -> None:
    lines = [
        "# RouteForge AI Performance",
        "",
        f"Generated: {datetime.now().isoformat(timespec='seconds')}",
        "",
        "## Routing Benchmark",
        "",
        f"Provider: `{provider_name}`",
        "",
        provider_note,
        "",
        "Matrix generation includes coordinate validation, provider matrix calls, "
        "and SQLite cache write. Solver time is the OR-Tools single-vehicle solve. "
        "Total request time is matrix generation plus solver work inside the benchmark "
        "process. Memory reports peak Python allocations from `tracemalloc` and process "
        "working-set delta when available.",
        "",
        "| Stops | Matrix generation | Solver | Total request | Peak Python memory | Process memory delta | Solver status | Cache hit |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    lines.extend(format_result_row(result) for result in results)
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Benchmarks use a fresh temporary SQLite database for each stop count, so cache hits are expected to be `False`.",
            "- The optimizer has a 100 ms OR-Tools search time limit in the current single-vehicle implementation.",
            "- Results are development-environment measurements and should be re-run after routing provider, map data, or optimizer changes.",
            "",
        ]
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")


def format_result_row(result: BenchmarkResult) -> str:
    process_delta = (
        "n/a"
        if result.process_memory_delta_mb is None
        else f"{result.process_memory_delta_mb:.2f} MB"
    )
    return (
        f"| {result.stop_count} | "
        f"{result.matrix_generation_seconds:.4f}s | "
        f"{result.solver_seconds:.4f}s | "
        f"{result.total_request_seconds:.4f}s | "
        f"{result.peak_python_memory_mb:.2f} MB | "
        f"{process_delta} | "
        f"{result.solver_status} | "
        f"{result.cache_hit} |"
    )


if __name__ == "__main__":
    main()
