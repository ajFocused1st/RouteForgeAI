# RouteForge AI Environment Report

Date: 2026-09-28

## Summary

The local machine has the main development CLIs needed to begin RouteForge AI planning work: Python, pip, Node.js, npm, Git, Ollama, NVIDIA GPU drivers, Docker CLI, and WSL2 are present. Docker Desktop's Linux engine is not currently reachable, so Docker is installed but not ready for containerized services yet.

No software was installed or modified during this check.

## Installed

| Component | Status | Detected Version / Details |
| --- | --- | --- |
| Python | Installed | `Python 3.12.0` |
| pip | Installed | `python -m pip --version`: `pip 24.2` for Python 3.12 |
| Node.js | Installed | `v20.11.1` |
| npm | Installed | `10.5.0` |
| Git | Installed | `git version 2.44.0.windows.1` |
| Ollama | Installed | `ollama version is 0.31.2` |
| NVIDIA GPU | Available | NVIDIA GeForce RTX 3060 Ti, 8 GB VRAM |
| NVIDIA Driver / CUDA | Available | Driver `595.95`, CUDA `13.2` reported by `nvidia-smi` |
| Docker CLI | Installed | Docker CLI `27.1.1`; Docker Compose plugin `v2.29.1` |
| WSL2 | Available | Default WSL version is `2` |

## Missing Or Not Ready

| Component | Status | Evidence |
| --- | --- | --- |
| Docker Engine | Not currently reachable | `docker info` could not connect to `dockerDesktopLinuxEngine`; the named pipe was not found. |
| General-purpose WSL distro | Not confirmed | `wsl --status` reports the default distribution as `docker-desktop-data`, which is Docker-managed rather than a normal development distro. |

## Notes

- `pip --version` resolves to `pip 25.0.1` for Python 3.13, while `python -m pip --version` resolves to `pip 24.2` for Python 3.12. For this project, prefer `python -m pip ...` so package operations target the active Python interpreter.
- The NVIDIA GPU is visible from Windows via `nvidia-smi`, which is promising for local Ollama acceleration. Actual Ollama GPU usage should be verified later with a model run after project setup decisions are made.
- Docker Desktop appears installed, but the Linux engine is not running or not available to the current shell.
- WSL2 is enabled, but no normal Linux development distribution was confirmed during this check.

## Recommendations

- Use Python 3.12 for the FastAPI backend unless a later dependency requires a different version.
- Use `python -m pip` instead of bare `pip` to avoid Python 3.12 / Python 3.13 path confusion.
- Use Node.js 20.x and npm 10.x for the future React + TypeScript + Vite frontend.
- Start Docker Desktop before relying on Docker for Valhalla, databases, or local service orchestration.
- Consider installing or selecting a normal WSL2 distro, such as Ubuntu, if Linux-native tooling is needed.
- Verify Ollama model availability and GPU acceleration later, after choosing the local model and runtime workflow.
- Keep the RouteForge AI stack local-first and avoid required Google Maps APIs.

## Commands Checked

- `python --version`
- `pip --version`
- `python -m pip --version`
- `node --version`
- `npm --version`
- `git --version`
- `ollama --version`
- `nvidia-smi`
- `docker --version`
- `docker info`
- `wsl --status`
