# RouteForge AI Project Spec

## Purpose

RouteForge AI is a local-first route planning and optimization application for building, analyzing, and improving delivery, service, or field-operation routes using open mapping data and local AI assistance.

This repository currently contains project documentation only. Application features should not be built until explicitly requested.

## Architecture

The intended stack is:

- Frontend: React + TypeScript + Vite
- Backend: FastAPI
- Database: SQLite
- ORM: SQLAlchemy
- Optimization: OR-Tools
- Routing engine: Valhalla
- Map data: OpenStreetMap
- Map rendering: MapLibre
- Local AI: Ollama
- Deployment posture: local-first
- Required Google Maps APIs: none

## Core Principles

- Local-first: core workflows should run locally whenever practical.
- Open data first: use OpenStreetMap-based data and tooling.
- Real routing and optimization: avoid fake route results, mocked optimization, or simulated integrations unless explicitly requested for tests or prototypes.
- Modular boundaries: keep UI, API, persistence, routing, optimization, and AI assistance cleanly separated.
- Minimal required external services: do not make cloud APIs mandatory for core operation.
- Preserve working behavior: changes should be small, focused, and tested.

## Expected System Boundaries

The frontend should own user interaction, map presentation, and workflow ergonomics.

The FastAPI backend should own application APIs, persistence orchestration, routing requests, optimization workflows, and local AI coordination.

SQLite should store local project data, route inputs, generated plans, configuration, and other user-owned state.

Valhalla should provide routing and travel-time behavior based on OpenStreetMap data.

OR-Tools should provide route optimization and constraint solving.

MapLibre should render maps in the browser using appropriate local or configured tiles.

Ollama should support local AI features without requiring hosted model APIs.

## Non-Goals

- No application features are required at this documentation stage.
- Do not require Google Maps APIs.
- Do not add placeholder business logic that pretends routing, optimization, persistence, or AI behavior exists.
- Do not add broad framework scaffolding until implementation work is requested.
