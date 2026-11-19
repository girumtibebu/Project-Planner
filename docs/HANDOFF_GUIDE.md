# Event Planner Developer Handoff Guide

This guide is for the client engineering team taking over the `event_planner` app. It explains how the product is organized, how to get productive quickly, and where to go deeper.

## Product Purpose and Scope

Event Planner extends ERPNext/Frappe with an event-focused planning workspace:
- A Vue SPA for planners (`/planner#/:project/...`).
- Backend APIs that aggregate and persist planning data.
- Custom fields and DocTypes that model event operations.
- Desk integrations that bridge native ERPNext screens with the planner UX.

The app is intentionally built as a hybrid:
- **Frappe owns authentication, permissions, persistence, DocTypes, and lifecycle hooks.**
- **The Vue SPA owns interactive planning workflows and rich document editing UX.**

## First-Week Onboarding Checklist

1. Read this file completely.
2. Read `docs/ARCHITECTURE.md` for module boundaries and runtime behavior.
3. Read `docs/INTERACTION_FLOWS.md` for page-by-page data and API flow.
4. Read `docs/EXTENDING_THE_PRODUCT.md` before making schema or API changes.
5. Read `docs/DEV_RUNBOOK.md` and run setup + lint/test commands locally.
6. Open the app from a Project in Desk and click **Edit in Planner** to validate end-to-end flow.

## Quick Start (Developer)

Use bench from your Frappe bench root:

```bash
bench get-app <repo-url> --branch version-16
bench install-app event_planner
```

If frontend assets do not build automatically during install:

```bash
cd apps/event_planner/frontend
npm install
npm run build
```

For day-to-day contributor setup:

```bash
cd apps/event_planner
pre-commit install
```

## Handoff Reading Order

1. `docs/ARCHITECTURE.md`  
   Understand runtime structure, integration seams, and data ownership.
2. `docs/INTERACTION_FLOWS.md`  
   Follow user interactions from page -> API -> DocType writes.
3. `docs/EXTENDING_THE_PRODUCT.md`  
   Learn safe extension patterns and migration strategy.
4. `docs/DEV_RUNBOOK.md`  
   Operational commands, CI expectations, and troubleshooting.

## What to Treat as Critical

- `event_planner/hooks.py` controls lifecycle hooks, Desk JS injection, and Task event hooks.
- `event_planner/api.py` is the SPA backend contract and contains most write-path behavior.
- `event_planner/custom_fields.py` is the source of truth for schema additions on `Project` and `Task`.
- `event_planner/install.py` defines install/migrate behavior, default template seeding, and frontend build-on-install logic.
- `frontend/src/composables/useFrappe.ts` centralizes session/CSRF-aware client API behavior.

## Recommended Team Conventions

- Keep API shape changes backward compatible with existing frontend call sites unless there is a coordinated frontend update in the same PR.
- Prefer adding app-owned `ep_*` fields over ad-hoc Customize Form fields for planner-owned behavior.
- Keep migration logic idempotent and safe to run on existing sites.
- Keep feature docs updated in this `docs/` directory when flows or integration points change.

## Definition of Done for Client Team Changes

A change is handoff-ready when:
- local setup remains documented and reproducible,
- interaction flow docs still match runtime behavior,
- migration/patch effects are documented if schema changes,
- and README handoff links remain accurate.
