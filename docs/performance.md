# RouteForge AI Performance

Generated: 2026-09-29T12:10:18

## Routing Benchmark

Provider: `benchmark-deterministic`

Valhalla was unavailable during the benchmark, so results use the synthetic in-process provider. Valhalla check: Valhalla request failed: <urlopen error timed out>

Matrix generation includes coordinate validation, provider matrix calls, and SQLite cache write. Solver time is the OR-Tools single-vehicle solve. Total request time is matrix generation plus solver work inside the benchmark process. Memory reports peak Python allocations from `tracemalloc` and process working-set delta when available.

| Stops | Matrix generation | Solver | Total request | Peak Python memory | Process memory delta | Solver status | Cache hit |
| ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 10 | 0.0101s | 0.1092s | 0.1194s | 0.24 MB | n/a | optimal | False |
| 25 | 0.0096s | 0.1019s | 0.1115s | 0.14 MB | n/a | optimal | False |
| 50 | 0.0236s | 0.1013s | 0.1250s | 0.30 MB | n/a | optimal | False |
| 100 | 0.0742s | 0.1022s | 0.1765s | 0.92 MB | n/a | optimal | False |

## Notes

- Benchmarks use a fresh temporary SQLite database for each stop count, so cache hits are expected to be `False`.
- The optimizer has a 100 ms OR-Tools search time limit in the current single-vehicle implementation.
- Results are development-environment measurements and should be re-run after routing provider, map data, or optimizer changes.
