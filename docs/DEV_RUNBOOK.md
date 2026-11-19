# Event Planner Developer Runbook

Operational runbook for local development, CI alignment, migration/release checks, and troubleshooting.

## Local Setup

From bench root:

```bash
bench get-app <repo-url> --branch version-16
bench install-app event_planner
```

From app root (`apps/event_planner`) for contributor tooling:

```bash
pre-commit install
```

If frontend was not built during install:

```bash
cd apps/event_planner/frontend
npm install
npm run build
```

## Day-to-Day Development Commands

### Frontend

```bash
cd apps/event_planner/frontend
npm install
npm run dev
```

Build production frontend assets:

```bash
cd apps/event_planner/frontend
npm run build
```

### Backend/site operations

Apply schema and patch updates:

```bash
bench --site <site-name> migrate
```

Install app to a new site:

```bash
bench --site <site-name> install-app event_planner
```

Run app tests:

```bash
bench --site <site-name> set-config allow_tests true
bench --site <site-name> run-tests --app event_planner
```

## Linting and Quality Checks

The repository relies on pre-commit hooks (ruff/eslint/prettier/pyupgrade). Run before PR:

```bash
cd apps/event_planner
pre-commit run --all-files
```

CI in `.github/workflows/linter.yml` additionally runs:
- Semgrep rules
- `pip-audit`

## CI Expectations

`ci.yml` provisions a full test stack:
- Python 3.14
- Node 24
- MariaDB + Redis services
- bench-based app install + build + tests

Local changes that affect install/migrate/front-end build should be validated with commands that mirror these CI phases.

## Migration and Deployment Checklist

Before release:
- Confirm custom field changes are in `custom_fields.py`.
- Confirm one-time transforms are in patches and registered in `patches.txt`.
- Run `bench --site <site-name> migrate` on a staging copy with realistic data.
- Validate planner entry from Project form (`Edit in Planner` button).
- Validate at least one write in each major module (Action, Schedule, Brief, Debrief).
- Rebuild frontend assets if changed (`npm run build`).

After deployment:
- Verify planner page loads (`/planner#/<project>/landing`) for authenticated users.
- Verify CSRF-backed writes succeed (no token errors).
- Spot-check `Task` assignment sync (`_assign` and `assigned_to` coherence).
- Check seeded templates exist and have expected `kind` values.

## Operational Scripts for Data Bootstrap

Useful one-off setup scripts:

```bash
bench --site <site-name> execute event_planner.setup.demo_data.execute
bench --site <site-name> execute event_planner.setup.migrate_categories.execute
```

Use only in intended environments and confirm data impact before running in shared sites.

## Troubleshooting Guide

## 1) Planner loads but writes fail with CSRF/auth errors

Checks:
- Confirm user is logged in on same site origin.
- Open planner through Desk Project button (ensures expected route/session context).
- Hard refresh planner page to re-bootstrap token.
- Inspect `useFrappe.ts` flow (`ensureCsrfToken` -> `requireCsrfToken`).

## 2) Frontend assets missing after install

Symptoms:
- `/planner` opens blank or cannot load `index.js/index.css`.

Fix:
- Build manually in `apps/event_planner/frontend` with `npm install && npm run build`.
- Confirm assets are produced under app public frontend asset path.

## 3) New custom field not appearing

Checks:
- Field exists in `custom_fields.py` with correct doctype and fieldname.
- `bench --site <site-name> migrate` has been run.
- No conflicting manual Custom Field with same name/semantic role.

## 4) Category or task order changes not persisting

Checks:
- Confirm API methods are called (`reorder_tasks_in_category`, `reorder_categories`).
- Validate that `frappe.db.commit()` is reached (no hidden server exception).
- Verify updated values (`ep_sort_order`) directly on affected docs.

## 5) Assignment appears inconsistent between Desk and planner

Checks:
- Confirm Task hook in `hooks.py` is active.
- Confirm `sync_assigned_to_from_assign` executes on save.
- Verify both `_assign` and `assigned_to` values after write.

## 6) Brief/debrief template mismatch errors

Cause:
- Attempt to create brief from a debrief template or vice versa.

Fix:
- Verify `Event Brief Template.kind` value.
- Use matching creation flow (`create_brief_from_template` or `create_debrief_from_template`).

## Change Management Notes

- Any runtime behavior change should update:
  - `docs/INTERACTION_FLOWS.md` (if flow changed),
  - `docs/ARCHITECTURE.md` (if boundary/integration changed),
  - root README handoff links (if docs list changed).
