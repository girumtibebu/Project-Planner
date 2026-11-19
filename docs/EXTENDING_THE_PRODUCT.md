# Extending Event Planner Safely

This guide describes the preferred way to extend Event Planner without breaking existing client behavior.

## Extension Principles

1. Keep planner-owned schema in app code, not ad-hoc manual customization.
2. Keep migrations idempotent so they are safe on already-live sites.
3. Preserve compatibility between ERPNext native behavior and planner behavior.
4. Co-deploy backend API and frontend call-site changes when contracts change.

## Primary Extension Seams

## 1) Custom fields on existing doctypes

- Source of truth: `event_planner/custom_fields.py`
- Applied during install/migrate via `event_planner/install.py`

Use this path when extending:
- `Project` event metadata/schedule fields
- `Task` planner metadata

### Recommended process

1. Add new field definitions under `CUSTOM_FIELDS`.
2. Ensure fieldnames are namespaced (`ep_*`).
3. Run migrate so `after_migrate` applies updates.
4. If field rename is needed, add a patch in `event_planner/patches/` and register it in `patches.txt`.

## 2) Backend API methods for SPA

- API module: `event_planner/api.py`
- Frontend client calls: `frontend/src/composables/useFrappe.ts`

Use this path when:
- existing REST writes are too coarse,
- server-side validation or aggregation is needed,
- cross-doctype writes must stay transactional.

### Recommended process

1. Add/extend a whitelisted method in `api.py`.
2. Validate login/session where required.
3. Use explicit doctype-level writes (`get_doc` + `save`) if hooks must fire.
4. Return stable JSON payloads expected by the Vue pages.
5. Update frontend callers and document changed behavior in `docs/INTERACTION_FLOWS.md`.

## 3) Frontend feature pages/components

- Routes: `frontend/src/main.ts`
- Shared project context: `frontend/src/App.vue`
- Existing pages: `frontend/src/pages/*.vue`

Use this path when adding:
- new planner modules,
- richer UX on current modules,
- new visualizations driven by existing APIs.

### Recommended process

1. Add page/component.
2. Register route in `main.ts` using the existing `/:project/...` convention.
3. Use `useFrappe.ts` wrappers (`frappeGet`, `frappeCall`, `frappeSave`) to preserve CSRF/session behavior.
4. Keep project-aware behavior tied to provided `projectName` context.

## 4) Lifecycle hooks and install/migrate behavior

- Hook registry: `event_planner/hooks.py`
- Lifecycle implementation: `event_planner/install.py`

Use this path when:
- new setup data must exist after install,
- migration-time backfill is required,
- uninstall cleanup for app-owned records is needed.

## 5) Desk-level integration behavior

- `event_planner/public/js/project_button.js`
- `event_planner/public/js/task_list.js`

Use this path when extending native Desk UX that should complement the planner SPA.

## Safe End-to-End Extension Pattern (Example)

Example: Add a **Venue Contact** field to project planning and surface it in planner UI.

### Backend/schema steps

1. Add `ep_venue_contact` custom field in `custom_fields.py` under `Project`.
2. Run migrate to apply field via `after_migrate`.
3. If renaming from a legacy manual field, create a patch in `event_planner/patches/` and register in `patches.txt`.

### API steps

1. If frontend needs custom write logic, add an API method such as `update_project_event_details(project, venue_contact, ...)`.
2. Keep output payload simple and stable (`{"ok": true}` or updated doc subset).

### Frontend steps

1. Add UI control in the target page (for example, `Schedule.vue` or a new Event Details page).
2. Read/write via `frappeGet` / `frappeSave` or new `frappeCall` method.
3. Validate UX against an existing project route (`/:project/...`).

### Documentation + validation

1. Update `docs/INTERACTION_FLOWS.md` with the new interaction.
2. Update `docs/ARCHITECTURE.md` only if boundaries/integration changed.
3. Verify migration on a site with existing records.

## Migration and Patch Workflow

Use patches for one-time data/schema transitions:
- Add patch module under `event_planner/patches/`.
- Register patch import path in `event_planner/patches.txt`.
- Make patch idempotent (safe to rerun).

Existing example: `rename_customize_form_fields.py` migrates pre-app manual fields to app-owned `ep_*` fields while preserving data.

## Compatibility Considerations

## ERPNext/Frappe assignment model

- Native Task assignments live in `_assign`.
- Event Planner mirrors primary assignment into `assigned_to` via `task_hooks.py`.
- Extensions that touch assignment must respect this sync logic.

## Permissions and write-path behavior

- Some API writes currently use `ignore_permissions=True` plus `frappe.db.commit()`.
- If tightening permissions, coordinate frontend error handling and role policy together.

## Template model for brief/debrief

- `Event Brief Template.kind` differentiates `brief` vs `debrief`.
- Create methods enforce kind alignment.
- New template features should preserve this guardrail.

## Anti-Patterns to Avoid

- Adding planner-critical fields only via manual Customize Form.
- Changing API response shape without updating all frontend callers.
- Non-idempotent patches that can fail on rerun.
- Replacing `_assign` behavior without understanding hook synchronization.
- Hardcoding site-specific IDs/values in seeded defaults.
