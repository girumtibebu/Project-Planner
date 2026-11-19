# Event Planner Interaction Flows

This document maps key user interactions to frontend components, backend APIs, data writes, and side effects.

## How to Read This

Each flow includes:
- **Entry**: where user starts
- **Frontend**: page/components involved
- **Backend/API**: whitelisted methods and resource calls
- **Data touched**: doctypes and fields
- **Side effects/caveats**: behavior that impacts extension and ops

## 1) Planner Entry + Project Context Bootstrap

- **Entry**
  - User opens a `Project` in Desk and clicks **Edit in Planner**.
- **Frontend**
  - `project_button.js` opens `/planner#/<project>/landing`.
  - `main.ts` starts app and ensures CSRF token.
  - `App.vue` loads the `Project` and provides context.
- **Backend/API**
  - `event_planner.api.get_planner_csrf_token`
  - REST read: `GET /api/resource/Project/<name>`
- **Data touched**
  - Read-only `Project` document load at bootstrap.
- **Side effects/caveats**
  - Requires authenticated same-origin session.
  - If CSRF bootstrap fails, write actions will fail later.

## 2) Landing Overview + Activity

- **Entry**
  - Route `/:project/landing`
- **Frontend**
  - `frontend/src/pages/Landing.vue`
- **Backend/API**
  - `event_planner.api.get_landing_summary`
  - `event_planner.api.get_recent_activity`
- **Data touched**
  - `Task` status aggregates and milestones
  - `Project` dates and schedule fields
  - Child table rows in `Equipment Schedule`, `Crew Schedule`, `Vehicle Schedule`
  - `Comment`, `Version` (project activity)
- **Side effects/caveats**
  - API is read-heavy and aggregate-based; can grow with data size.
  - Some parsing/aggregation paths are tolerant to exceptions (best-effort behavior).

## 3) Action Plan (Task Board + Category Management)

- **Entry**
  - Route `/:project/action`
- **Frontend**
  - `frontend/src/pages/Action.vue`
  - `frontend/src/components/CategoryManager.vue`
  - `frontend/src/components/TaskPanel.vue`
- **Backend/API**
  - `event_planner.api.list_categories`
  - `event_planner.api.reorder_tasks_in_category`
  - `event_planner.api.create_category`
  - `event_planner.api.update_category`
  - `event_planner.api.delete_category`
  - `event_planner.api.reorder_categories`
  - metadata support: `event_planner.api.get_doc_meta`
  - plus REST saves for Task updates via `/api/resource/Task/...`
- **Data touched**
  - `Action Category` rows (project-scoped + global)
  - `Task.ep_action_category`
  - `Task.ep_sort_order`
  - `Task.status`, `Task._assign`, `Task.assigned_to` (when edited)
- **Side effects/caveats**
  - Category delete reassigns affected tasks to null category.
  - Reorder writes are committed immediately.
  - Assignment behavior is affected by Task hook sync logic (see flow 7).

## 4) Time Workspace (Hierarchy + Calendar/Kanban/Timeline Actions)

- **Entry**
  - Route `/:project/timeline`
- **Frontend**
  - `frontend/src/pages/TimeWorkspace.vue`
  - `frontend/src/components/KanbanBoard.vue`
  - `frontend/src/components/CalendarBoard.vue`
- **Backend/API**
  - `event_planner.api.list_tasks_with_hierarchy`
  - `event_planner.api.list_categories`
  - REST Task writes via `frappeSave`
- **Data touched**
  - `Task` hierarchy: `parent_task`, `subject`, `description`
  - planning fields: `exp_start_date`, `exp_end_date`, `status`, `priority`
  - category fields: `ep_action_category`, `ep_sort_order`
- **Side effects/caveats**
  - Hierarchy depth is computed server-side and sent as flat enriched list.
  - Category color is enriched from `Action Category`.
  - Large project task counts may impact load time due to computed hierarchy pass.

## 5) Schedule Editor (Project Child Tables)

- **Entry**
  - Route `/:project/schedule`
- **Frontend**
  - `frontend/src/pages/Schedule.vue`
- **Backend/API**
  - REST read `frappeGet("Project", project)`
  - REST write `frappeSave("Project", project, {...schedule fields...})`
- **Data touched**
  - `Project.ep_time_schedule`
  - `Project.ep_equipment_schedule`
  - `Project.ep_crew_schedule`
  - `Project.ep_vehicle_schedule`
  - child rows in doctypes:
    - `Time Schedule`
    - `Equipment Schedule`
    - `Crew Schedule`
    - `Vehicle Schedule`
- **Side effects/caveats**
  - Writes update full schedule field payloads, not incremental row patch APIs.
  - Debounced autosave behavior can create frequent writes during active editing.

## 6) Brief / Debrief Lifecycle (Template -> Document -> Autosave)

- **Entry**
  - Routes `/:project/brief` and `/:project/debrief`
- **Frontend**
  - `frontend/src/pages/Brief.vue`
  - `frontend/src/pages/Debrief.vue`
  - `frontend/src/components/TiptapEditor.vue`
  - `frontend/src/components/ActivityFeed.vue`
  - `frontend/src/components/BriefGallery.vue`
- **Backend/API**
  - `event_planner.api.create_brief_from_template`
  - `event_planner.api.create_debrief_from_template`
  - `event_planner.api.get_doc_meta`
  - `event_planner.api.get_activity_log`
  - `event_planner.api.save_brief_as_template`
  - `event_planner.api.save_debrief_as_template`
  - REST writes for content updates
- **Data touched**
  - `Event Brief`, `Event Debrief`
  - `Event Brief Template` (`kind` = `brief` or `debrief`)
  - supporting activity from `Version`, `Comment`, `ToDo`
- **Side effects/caveats**
  - Create-from-template methods are idempotent (return existing doc if already present).
  - Template kind guardrails prevent brief/debrief mismatch.
  - Template snapshot methods create non-seeded templates for user-authored reuse.

## 7) Task Assignment Synchronization Hook

- **Trigger**
  - Any Task save operation (Desk, API, planner-originated updates).
- **Backend**
  - `event_planner.task_hooks.sync_assigned_to_from_assign` on `Task.before_save`
- **Data touched**
  - `Task._assign` (Frappe JSON assignment list)
  - `Task.assigned_to` (app-owned compatibility field)
- **Side effects/caveats**
  - Keeps native Frappe assignment behavior and planner field in sync.
  - `_assign` is treated as source of truth when non-empty.
  - Extensions that write assignment fields should account for hook reconciliation.

## 8) Activity Feed Composition

- **Entry**
  - Activity widgets on landing/brief/debrief/task panel contexts.
- **Backend/API**
  - `event_planner.api.get_recent_activity`
  - `event_planner.api.get_activity_log`
- **Data touched**
  - Merges records from `Version`, `Comment`, and `ToDo`.
- **Side effects/caveats**
  - Multiple activity streams are normalized into a single time-ordered output.
  - Label generation is heuristic for changed fields and may be concise by design.

## Flow-to-Ownership Matrix (Quick Reference)

- **Landing** -> summary/health -> aggregate reads only.
- **Action** -> task execution -> categories + task write operations.
- **Timeline** -> schedule execution view -> hierarchical task read + task writes.
- **Schedule** -> operational resource planning -> `Project` child-table writes.
- **Brief/Debrief** -> narrative docs -> template-aware doc create/edit with activity.
