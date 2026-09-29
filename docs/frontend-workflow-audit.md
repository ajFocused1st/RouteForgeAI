# Frontend Workflow Audit

Date: 2026-09-29

## Scope

Reviewed the frontend workflows for manual route creation, screenshot import, address review, route optimization, route map rendering, route history, and AI proposed changes.

## Findings And Fixes

- Manual route creation could leave a previously saved route selected after route name, depot, vehicle, or stop order changes. The Optimize button now requires saving the changed route draft again before optimization.
- Screenshot import Clear removed the preview and review rows but left the previous image file available for extraction. Clear now fully resets the selected screenshot and downstream route state.
- Route History navigation opened a placeholder instead of the saved optimization history workflow. It now lists saved routes and their preserved route versions from the backend.
- Route map attribution and popup separators used non-ASCII glyphs that may render inconsistently in terminals or constrained environments. They now use plain ASCII text.

## No Production Backend Changes

The audit did not require backend code changes. Existing backend APIs already supported the workflow fixes.
