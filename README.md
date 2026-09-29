# RouteForge AI

RouteForge AI is a local-first routing, dispatch, and route-optimization application.

It is designed to turn delivery and pickup stops into optimized routes while keeping as much data and processing as possible on your own computer.

## What RouteForge AI Does

RouteForge AI is built to support:

- Manual stop entry
- Screenshot-to-address extraction
- Address validation and geocoding
- Single-vehicle and multi-vehicle routing
- Payload and time-window constraints
- Pickup/delivery sequencing
- Route optimization with OR-Tools
- Road routing through Valhalla + OpenStreetMap
- Route visualization with MapLibre
- Route history and version comparison
- Deadhead mileage analysis
- Route economics
- Local AI assistance through Ollama

The core design separates AI interpretation from mathematical route optimization.

```text
User / Screenshot
        ↓
Address & stop extraction
        ↓
Validation / geocoding
        ↓
Valhalla road matrix
        ↓
OR-Tools optimization
        ↓
Route geometry
        ↓
Map + ETAs + mileage + route metrics
```

The AI does not calculate the route itself. OR-Tools and Valhalla handle the routing mathematics.

---

## Current Development Status

The repository contains working application structure and implementations for:

- FastAPI backend
- React + TypeScript + Vite frontend
- SQLite persistence
- SQLAlchemy models
- OR-Tools optimization
- MapLibre map rendering
- Ollama AI and vision provider integrations
- Valhalla provider integration
- Route versioning
- Deadhead and route-economics calculations
- Automated tests
- Windows startup tooling

The project is currently development-ready rather than production-ready.

Local Valhalla/OpenStreetMap routing data still needs to be running and verified for full local road routing.

---

# Local Requirements

Recommended system:

- Windows 11
- Python 3.12+
- Node.js 20+
- npm
- Git
- Ollama
- NVIDIA GPU recommended for local AI
- Valhalla for real local road routing

The original development machine uses an NVIDIA RTX 3060 Ti.

## Expected Local Services

| Service | Default Address |
| --- | --- |
| RouteForge frontend | http://127.0.0.1:5173 |
| FastAPI backend | http://127.0.0.1:8000 |
| Ollama | http://127.0.0.1:11434 |
| Valhalla | http://127.0.0.1:8002 |

---

# Quick Start on Windows

## 1. Clone the repository

Open PowerShell, Command Prompt, Windows Terminal, or the VS Code terminal.

```powershell
git clone https://github.com/ajFocused1st/RouteForgeAI.git
cd RouteForgeAI
```

If the repository is private, GitHub may require you to authenticate first.

---

## 2. Create or activate a Python environment

Using Conda:

```powershell
conda create -n RouteForgeAI python=3.12
conda activate RouteForgeAI
```

Or using Python venv:

```powershell
python -m venv .venv
.venv\Scripts\activate
```

---

## 3. Install the Python backend

From the project root:

```powershell
python -m pip install --upgrade pip
python -m pip install -e .
```

For development/test dependencies:

```powershell
python -m pip install -e ".[dev]"
```

The backend currently depends on:

- FastAPI
- Uvicorn
- SQLAlchemy
- Pydantic Settings
- OR-Tools

---

## 4. Install frontend dependencies

```powershell
cd frontend
npm install
cd ..
```

---

## 5. Start Ollama

Make sure Ollama is installed and running.

Test it with:

```powershell
ollama list
```

RouteForge expects Ollama at:

```text
http://127.0.0.1:11434
```

The AI and screenshot-vision features require an appropriate local model to be installed.

---

## 6. Start Valhalla

RouteForge expects Valhalla at:

```text
http://127.0.0.1:8002
```

Valhalla provides:

- Real road distances
- Travel-time matrices
- Route geometry
- Road-network routing

See:

```text
docs/valhalla-florida.md
```

for the repository's current Valhalla/Florida setup notes.

RouteForge can open without Valhalla, but real optimized road routing will be unavailable until Valhalla is running with map data.

---

# Easiest Way to Start RouteForge

The repository includes:

```text
start-routeforge.bat
```

Before launching, run the built-in checks:

```powershell
start-routeforge.bat --check-only
```

This verifies:

- Python
- npm
- backend Python packages
- SQLite
- frontend dependencies
- Ollama connectivity
- Valhalla connectivity

Ollama and Valhalla may report warnings if they are offline.

When the required checks pass:

```powershell
start-routeforge.bat
```

The script starts:

### Backend

```text
http://127.0.0.1:8000
```

### Frontend

```text
http://127.0.0.1:5173
```

It then opens RouteForge AI in your default browser.

---

# Manual Startup

If you prefer to run each part manually, open two terminal windows.

## Terminal 1 — Backend

From the project root:

```powershell
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

## Terminal 2 — Frontend

```powershell
cd frontend
npm run dev -- --port 5173
```

Then open:

```text
http://127.0.0.1:5173
```

---

# Running Tests

From the project root:

```powershell
pytest
```

Or:

```powershell
python -m pytest
```

Focused tests can be run by file, for example:

```powershell
python -m pytest tests/test_single_vehicle_optimizer.py
```

---

# Important Local Files

| File | Purpose |
| --- | --- |
| `PROJECT_SPEC.md` | Core product architecture and requirements |
| `ROUTEFORGE_BUILD_PLAN.md` | Numbered implementation plan |
| `TASKS.md` | Development task/status tracking |
| `CHANGELOG.md` | Development history |
| `AGENTS.md` | Coding-agent instructions |
| `docs/environment-report.md` | Development computer environment |
| `docs/release-readiness.md` | Current release-readiness audit |
| `docs/valhalla-florida.md` | Valhalla / Florida routing setup |
| `start-routeforge.bat` | Windows startup/check script |

---

# Privacy and Local-First Design

RouteForge AI is intended to keep customer, route, financial, and driver information local whenever practical.

Current local components include:

- SQLite
- OR-Tools
- Ollama
- Valhalla when running locally

Some current default OpenStreetMap-based geocoding or tile services may still use external network services unless configured for fully local operation.

Do not commit private customer data, route databases, API secrets, or screenshots containing real customer information to GitHub.

The repository's `.gitignore` excludes common local/runtime files such as:

- `.env`
- local SQLite database files
- Python environments
- Node modules
- frontend build output

---

# Development Workflow

Before changing code, read:

```text
AGENTS.md
PROJECT_SPEC.md
ROUTEFORGE_BUILD_PLAN.md
TASKS.md
```

When using a coding agent such as Codex, work one numbered build step at a time.

Recommended workflow:

```text
Implement one task
      ↓
Run focused tests
      ↓
Verify PASS
      ↓
Commit to Git
      ↓
Continue
```

---

# Git Workflow

After a successful milestone:

```powershell
git status
git add .
git commit -m "Describe completed RouteForge milestone"
git push
```

---

# Troubleshooting

## Backend dependencies missing

Run:

```powershell
python -m pip install -e ".[dev]"
```

## Frontend node_modules missing

Run:

```powershell
cd frontend
npm install
cd ..
```

## Ollama offline

Verify:

```powershell
ollama list
```

Then start Ollama if necessary.

## Valhalla offline

Run:

```powershell
start-routeforge.bat --check-only
```

If Valhalla reports offline, follow the setup notes in:

```text
docs/valhalla-florida.md
```

## Port already in use

RouteForge uses these development ports by default:

- 5173 — frontend
- 8000 — backend
- 8002 — Valhalla
- 11434 — Ollama

Stop the conflicting service or change the relevant configuration before restarting.

---

# License

No open-source license has been assigned yet.

Until a license is explicitly added, do not assume permission to copy, redistribute, sublicense, or commercially reuse this code.
