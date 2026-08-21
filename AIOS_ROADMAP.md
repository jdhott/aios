# AIOS Roadmap

**Last updated:** August 21, 2026

## Guiding Principle

> **AIOS should get smarter without getting more complicated.**

Prefer a small number of general mechanisms---project context, task
history, execution state, review feedback, and AI reasoning---over
narrow special-case rules.

If a proposed feature begins to require substantial duplicated pathways,
domain-specific behaviour, or one-off logic, stop and reconsider the
design before implementing it.

The web application and Supabase are the primary AIOS platform and
authoritative datastore. New work should strengthen that architecture
rather than recreate legacy Notion pathways.

------------------------------------------------------------------------

## 1. Current Focus --- Stabilize and Use

### Daily Journal V1 / V1.1 --- Functional acceptance testing

**Status:** Implemented and in functional testing.

Current scope is deliberately focused on **today**:

-   Persistent free-form daily journal.
-   Completed work for the selected day.
-   Reuse of the existing AI-generated Completed Today Summary rather
    than creating a second AI summarization path.
-   Completed tasks remain secondary detail rather than becoming the
    journal summary.
-   Generated focus/activation work is excluded where appropriate.
-   Journal is accessible from the main web navigation.

**Next:** Use it in normal daily work and fix demonstrated problems.
Avoid expanding the Journal until V1 proves useful.

Possible later evolution, based on actual use:

-   Refine AI summaries to favor higher-level outcomes/activities over
    enumerating closely related production subtasks.
-   Historical browsing and search.
-   Better reflection or synthesis.
-   Trends across days.
-   Additional AI assistance.

These are possibilities, not current requirements.

### Focus Context Loop V3 --- Functional acceptance testing

**Status:** Implemented and in live functional testing.

The current Best Next Action can now use durable **Task Context** and relevant
**Project Context** when generating Start Here work.

The BNA card supports a context-coaching loop:

-   Start Here remains the immediate actionable recommendation.
-   The user can add or edit durable Task Context directly from the BNA card.
-   **Not now** means the suggested action may be valid but is not suitable now.
-   **Not useful** means the suggestion does not fit the task as understood by
    the user and opens context coaching rather than blindly generating another
    guess.
-   AIOS can propose an editable context draft and ask one targeted question.
-   The user can answer the question, let AIOS incorporate the answer into the
    editable draft, then review/edit the result.
-   Durable Task Context changes only when the user explicitly saves it.
-   Saving context retires the old Start Here and regenerates a new one using
    the improved context.
-   Rejected Start Here work remains visible during coaching so the user retains
    the reference for what was considered not useful.

V3 UI polish includes:

-   **Use my answer** as the intermediate coaching action.
-   Normal-weight answer text.
-   Auto-expanding answer and context fields while retaining manual resize.
-   Spinner while AIOS is improving context.
-   Automatic refresh while asynchronous context improvement is pending.

**Next:** Use the workflow across varied real tasks. Avoid adding more
functionality until normal use reveals repeated shortcomings.

### Project Work V3 --- Functional acceptance and AI tuning

**Status:** Working and in extended functional testing.

Project Work can now identify genuinely missing project work rather than
simply repeating existing tasks. V3 is intentionally more selective and
normally proposes a small amount of work.

Current acceptance-testing goals:

-   Find meaningful gaps in real projects.
-   Avoid duplicating open or completed work.
-   Allow grounded research, assessment, comparison, outreach, and
    decision work.
-   Avoid inventing conventional but unsupported project requirements.
-   Avoid premature downstream tasks that depend on unresolved
    decisions.
-   Produce useful task titles at the right level of granularity.
-   Learn from rejected proposals and user corrections without turning
    proposal feedback into durable project facts.

**Development posture:** Do not add more rules simply because an
individual proposal is imperfect. Accumulate real examples and change
the mechanism only when testing reveals a consistent failure mode.

Project Context remains the durable source of project facts, decisions,
constraints, dates, people, and other grounding information.
Proposal-specific feedback remains separate.

------------------------------------------------------------------------

## 2. Complete / Monitor in Normal Use

These items are considered complete for now. Reopen them only if normal
use exposes a problem.

### Dashboard search

Search has been used successfully and is considered fixed for now.

### PWA multiline Brain Dump capture

Multiline PWA submissions now use the shared Brain Dump splitter so each
meaningful line is captured as its own Supabase inbox item.

Consider complete for now; reopen only if normal capture use exposes another
source-specific inconsistency.

### Task-detail return navigation

Save and Cancel now return to the screen from which the task was opened,
including Project Detail where applicable. Functional testing indicates
this is working.

### Supabase review cutovers

Possible-duplicate and clarification workflows have been cut over to
Supabase/web authority and passed structural validation.

Continue observing them in normal use before removing the remaining
legacy code.

### BNA / Focus improvements

Recent work includes:

-   BNA completion and generated activation-child cleanup.
-   Stable focus refresh behaviour.
-   Rank 1 removed from alternative lists.
-   Start Here guidance and starter timebox.
-   Start Here grounded in Task Context and relevant Project Context.
-   Context coaching from the BNA card, including **Not useful** feedback.
-   Supabase execution-state authority.
-   Quick Wins excluding the current BNA.
-   Timezone-aware due/defer handling using `America/Toronto`.
-   Dashboard Today default sort: Importance first, then Due Date ascending.

Treat these as stable unless use reveals a specific problem.

------------------------------------------------------------------------

## 3. Next --- Complete the Supabase / Web Transition

### Timezone-aware task dates

**Status:** Implemented; monitor in normal use.

Due and defer values are timezone-aware datetimes. Calendar concepts such as
Tomorrow are resolved in `America/Toronto` and stored as unambiguous instants.
Legacy midnight-UTC calendar values were normalized.

Continue observing snooze/defer behavior across local/UTC day boundaries and
daylight-saving transitions. Future due/defer time-of-day support should build
on this model rather than reintroduce date-only timezone ambiguity.

### Verify review workflows in normal use

Continue functional validation of:

-   Possible duplicates.
-   Clarification.
-   Accepted clarification becoming human-authoritative.
-   Review navigation and pending-review visibility.

### Remove obsolete Notion review/runtime code

Once Supabase/web parity is comfortably established:

-   Remove obsolete Notion review UI/runtime pathways.
-   Remove unnecessary Notion polling and mirror behaviour.
-   Avoid maintaining two implementations of the same workflow.
-   Review remaining Notion calls for runtime latency and eliminate
    those that no longer provide value.

Notion may remain useful for selected legacy/archive/context purposes
while those uses are still intentional, but it should not remain an
accidental runtime dependency.

### Brain Dump everywhere

Source-neutral capture is now the working model:

**Any capture surface → Supabase inbox → AIOS processing pipeline**

Recent work includes multiline PWA capture using the same shared Brain Dump
splitter as the web application.

Next UI exploration:

-   Consider removing the permanently visible Brain Dump box from the Dashboard.
-   Treat Brain Dump as a global action rather than dashboard information.
-   Add a compact Dashboard/header control that opens Brain Dump in a modal or
    popover using the existing capture pipeline.
-   Consider a keyboard shortcut for fast capture.
-   Keep the standalone PWA as a thin quick-capture surface rather than launching
    it from the web app.

The goal is one capture model with multiple lightweight entry points.

------------------------------------------------------------------------

## 4. Product Improvements on the Roadmap

### Recurring Tasks

**Status:** Planned; requires a dedicated design pass.

Recurring tasks are more complicated than simply copying a completed
task. Design should address:

-   Whether recurrence belongs to a task template/series rather than an
    individual task instance.
-   Creation of the next occurrence.
-   Completion semantics and historical instances.
-   Due dates and recurrence schedules.
-   Snoozing and deferral.
-   Project membership.
-   Importance, urgency, and execution ranking.
-   Interaction with BNA, Quick Wins, and JDI/focus guidance.
-   Editing one occurrence versus the recurring series.
-   Ending or pausing recurrence.

Do not implement until the data model and lifecycle are clear.

### Project Work refinement

Continue collecting acceptance/rejection examples from real projects.

Potential improvements should be driven by repeated failure patterns
rather than isolated outputs. Keep the architecture general and avoid
accumulating prompt rules for individual project types.

### Dashboard / Home refinements

Recent UI work:

-   Compact application header with AIOS/Home, Projects, Reviews, New Task, and a
    secondary menu.
-   Work Patterns, Journal, and Sign Out moved into the secondary menu.
-   Header and snooze menus dismiss on outside click and Escape.
-   Snooze no longer needs an explicit Cancel option.
-   Today list default sort is Importance, then Due Date ascending.

Possible later refinements:

-   User-selectable task sorting only if normal use demonstrates a real need;
    avoid a complex custom-sort builder.
-   Consider Brain Dump as a global modal/popover action rather than a permanent
    dashboard section.

Search is considered complete for now.

### UX polish and feedback consistency

**Status:** Active — task save feedback shipped locally August 21, 2026; remaining
items queued after normal-use observation.

The dashboard and focus loop are the most polished surfaces. Task detail, projects,
reviews, and journal are capable but uneven in async feedback, optimistic
interaction, and human-readable labels.

#### Implemented (August 21, 2026)

-   **Task edit save feedback (v4)** — Save waits for a confirmed API write via
    `/edit-optimistic`, shows **Saving…** on the button, surfaces inline errors on
    failure, and displays a **Task saved.** flash on return (including
    `history.back()` via `sessionStorage`).
-   **Focus context loading feedback (v1)** — Dashboard focus-context save, help,
    and answer forms submit via fetch with immediate loading UI (**Saving…**,
    **Updating your focus…**, **Improving your context…**), then poll the focus
    card until processor work completes. Errors show a retry toast.

#### Next opportunities (priority order)

1.  **Empty-state copy fixes** — dashboard “No matching tasks” when no search;
    reviews “All caught up” when both queues are empty.
2.  **Review resolution confirmation** — brief success toast/banner after
    accepting or dismissing a review card.
3.  **Journal summary polling** — auto-refresh pending daily summary on today’s
    journal page.
4.  **Project name on task detail** — replace raw Project ID; optional project
    picker on create/edit.
5.  **Project page optimistic complete/snooze** — align with dashboard patterns.
6.  **Preserve form data on errors** — create-task and dashboard Brain Dump
    failures should keep user input.
7.  **Shared toast/banner system** — unify scattered `?message=` / `?error=`
    query-param notices.
8.  **Hide or collapse BNA Rank/Score** for normal daily use.

#### UX principles

-   One feedback language across surfaces: saving, success, error, pending, timeout.
-   Optimistic interaction wherever the user acts frequently.
-   Progressive disclosure for technical metadata (rank, score, raw IDs).
-   Do not wait for SSE to fix silent failures or misleading empty states.

### Real-time UI updates (Server-Sent Events)

**Status:** Partially implemented (JSON polling); SSE planned as Phase 3.

The web app previously relied on full-page reload loops while AIOS processed
work asynchronously (focus refresh, breakdown generation, project work
proposals, review re-evaluation). That has been replaced incrementally with
**JSON fragment polling** and targeted DOM patching:

| Phase | Scope | Status |
|-------|--------|--------|
| 1 | Focus card (`/api/focus-card`) | Done |
| 1.5 | Dashboard task list (`/api/dashboard-tasks`) | Done |
| 2a | Undo sync + poll timeout retry UX on dashboard | Done |
| 2b | Breakdown, project work, and review inbox pending panels | Done |

Shared infrastructure includes fragment fingerprints, exponential backoff,
re-bind after patch, and timeout UI with **Try again** / **Refresh page**.

**Next:** Validate the polling model in normal use before investing in SSE.
Polling is boring but reliable; only move to SSE if testing shows meaningful
latency pain or unnecessary API load.

**Phase 3 --- SSE (planned):**

Replace client poll timers with a single long-lived **Server-Sent Events**
stream (e.g. `GET /api/events`). The client keeps existing fragment fetch/patch
logic; SSE tells it *when* to refresh, not *how*.

Typed events to consider:

-   `focus.updated`
-   `tasks.updated`
-   `breakdown.ready`
-   `project_work.ready`
-   `review.resolved`

**Why SSE is a step change (not a small frontend swap):**

-   **Event source:** The processor or API must emit when workflow state
    changes (focus activation published, breakdown proposed, etc.). Polling
    works today because the client asks until data appears; SSE requires
    something upstream to signal completion.
-   **Cloud Run:** Streaming responses, heartbeats (~15--30s), reconnect
    handling, and sensible timeout configuration.
-   **Multi-instance delivery:** If Cloud Run scales beyond one instance,
    events may need Redis pub/sub, Postgres `LISTEN/NOTIFY`, Supabase
    Realtime, or similar so all tabs/instances receive updates.

**Rough sizing:**

-   **SSE-lite** (~2--4 days): One stream; coarse events like
    `dashboard.refresh`; client still uses existing fragment endpoints.
    Minimal processor wiring.
-   **SSE proper** (~1--2 weeks): Typed events emitted on workflow
    completion; heartbeats and reconnect; removes most polling.
-   **SSE + pub/sub** (~2--3 weeks): Production-grade fan-out across
    Cloud Run instances and multiple browser tabs.

**Prerequisites before starting SSE:**

1.  Normal-use validation of current polling (snooze, complete, undo,
    breakdown, project work, review processing).
2.  Clear list of which state transitions must push events.
3.  Decision on delivery mechanism if more than one Cloud Run instance
    is expected.

Do not implement SSE until polling limitations are demonstrated in real
use or event emission can be wired cleanly from the processor.

### Project-task deferral

Previously identified but intentionally lower priority. Revisit when
there is a demonstrated need and a clean general model.

------------------------------------------------------------------------

## 5. Later / Strategic

### Workspace tenancy (multi-user foundation)

**Status:** Phase 1 in progress (August 21, 2026) — migration
`migrations/20260821_workspace_tenancy_phase1_v1.sql` adds `workspaces`,
`workspace_members`, and `workspace_id` on core tables with default-workspace
backfill. Apply in Supabase SQL editor; validate with
`python -m scripts.workspace_tenancy_phase1_v1_validate`. Phase 2 (query
scoping through API/processor) follows after migration is applied.

AIOS today is effectively **single-user**: one web login, one service identity
to the API, Supabase service-role access, global processor state, and one global
Best Next Action. Moving to workspaces is a deliberate migration, not a config
change.

#### Target model

-   A **workspace** is the primary tenancy boundary for shared AIOS state.
-   **Members** belong to a workspace (later: roles such as owner / member).
-   **Tasks, projects, inbox, reviews, journal, summaries, and processor
    work** are scoped to a workspace.
-   **Best Next Action / execution ranking** runs **per workspace** (each
    workspace has its own focus winner).
-   **Personal vs shared** within a workspace can come later (e.g. private tasks
    vs workspace-visible projects); do not over-design v1.

#### What is already well positioned

-   Supabase as authoritative datastore (RLS-ready).
-   API / web / processor separation (workspace context can enter at the API
    boundary).
-   Source-neutral inbox queue.
-   Signed web session (can later carry workspace + user claims).

#### Phased plan

| Phase | Scope | User-visible change |
|-------|--------|---------------------|
| **1 — Schema foundation** | `workspaces`, `workspace_members`; `workspace_id` on core tables; backfill one default workspace; optional `AIOS_DEFAULT_WORKSPACE_ID` env | None (single-user behavior unchanged) |
| **2 — Data access scoping** | Thread `workspace_id` through API, web proxies, processor, and execution engine queries | None if only one workspace exists |
| **3 — Authentication** | Supabase Auth (or equivalent); replace shared web password; user JWT to API | Real login per person |
| **4 — Authorization** | RLS policies and/or mandatory workspace filters; membership checks | Members see only their workspaces |
| **5 — Multi-workspace product** | Workspace switcher, invites, roles, per-workspace timezone and AI budgets | Multi-user / small-team use |
| **6 — Collaboration (optional)** | Shared project editing rules, assignment, activity — only if demonstrated need | Shared household / team workflows |

#### Phase 1 deliverables (first foundational element)

1.  Migration: `workspaces`, `workspace_members`.
2.  Add `workspace_id` (not null, indexed, FK) to at minimum:
    `tasks`, `projects`, `inbox_items`, `daily_journal`,
    `daily_completion_summaries`, and review-adjacent / cache tables as they
    are touched.
3.  Backfill all existing rows into a single default workspace (e.g.
    slug `default`, name from env or “Personal”).
4.  Composite uniques where needed (e.g. `(workspace_id, journal_date)` instead
    of `journal_date` alone).
5.  Validation script documenting schema expectations; **no** RLS or auth yet.

#### Explicitly defer until Phase 2+

-   Supabase Auth, invites, workspace switcher UI.
-   Row Level Security (until API uses user-scoped credentials).
-   Per-workspace processor leases (global job may remain; work units become
    workspace-scoped).
-   Per-member AI spend accounting.

#### Principles

-   **Default workspace preserves today’s behavior** — single-user production
    must keep working throughout Phase 1–2.
-   **New tables get `workspace_id` from day one** — avoid another retrofit.
-   **Workspace before collaboration** — get isolation right before shared-edit
    semantics.
-   Do not split Notion pathways or add parallel datastores for multi-user.

### Reusable knowledge / durable learned context

**Parking lot — requires design work.**

Explore a reusable knowledge layer above individual Task Context so useful
context learned through repeated work can ground future related tasks.

Example: recurring workshop knowledge might include standard format, teaching
approach, reusable materials, typical preparation lead time, or venue
constraints.

Design questions:

-   What belongs in reusable knowledge versus Task Context or Project Context?
-   When should AIOS suggest promoting task-specific context into reusable
    knowledge?
-   How does the user approve, edit, or remove learned knowledge?
-   How should AIOS retrieve relevant knowledge without over-generalizing?
-   How should knowledge accumulate over time without becoming stale or noisy?

Do not implement until the retrieval, approval, and lifecycle model is clear.

### Task breakdown versus project emergence

**Parking lot — requires design work.**

The Focus Context work raises a useful boundary question: when is a parent task
plus child breakdown sufficient representation, and when has the work become a
project?

Potential distinction to explore:

-   Task + Start Here: one outcome where the main problem is activation.
-   Task + breakdown: one outcome requiring several concrete steps.
-   Project: multiple independent work streams, decisions, dependencies,
    evolving context, or coordination over time.

Avoid using task count alone as the criterion. Eventually AIOS may be able to
notice when a task is starting to behave like a project and suggest promotion.

### Lightweight Today experience / PWA / native app

The web app remains primary.

A later lightweight Today experience could provide:

-   Quick capture.
-   Current BNA.
-   Start Here guidance.
-   Task completion.
-   Notifications.
-   Very fast mobile interaction.

Do not duplicate the full web application. Any mobile/PWA experience
should be a thin client over the same Supabase/API architecture.

### AI usage / credit efficiency

**Status:** Active — first optimizations shipped August 21, 2026; observe in
normal use for at least a few days before the next pass.

All live model calls run through the Cloud Run processor (`run_aios.py`) using
OpenAI `gpt-4.1-mini`. The web app and API enqueue processor runs; they do not
call models directly.

#### Implemented (August 21, 2026)

-   **Project work generation cache** — automatic project-work proposals store a
    `work_proposals_generation_key` fingerprint (outcome, context, work lists,
    activation history, proposal feedback). Unchanged inputs reuse existing
    proposals instead of calling generate + validate again. Manual **Generate
    work**, feedback/retry, and material project changes still trigger fresh AI.
-   **Light maintenance runs** — when the inbox is empty, the pipeline did no
    meaningful work this run, and no pending AI queues exist (breakdown,
    focus-context coaching, project-work dialogue), the processor skips heavy
    maintenance: project candidate detector and automatic project-work refresh.
    Execution ranking, focus activation (when needed), and daily summary
    (fingerprint-cached) still run.
-   **Scheduled processor throttling** — Cloud Scheduler reduced from every 15
    minutes to every 30 minutes (5am–8pm Toronto), plus the existing 9pm run.

Override env vars for debugging: `AIOS_FORCE_HEAVY_MAINTENANCE`,
`AIOS_SKIP_HEAVY_MAINTENANCE`.

#### Next opportunities (after observation period)

Review processor logs and OpenAI usage after a few days of normal use. If spend
is still higher than desired, consider these in rough priority order:

1.  **Existing-task project discovery throttling** — `run_existing_task_project_discovery`
    can invoke a large batch AI call (`ask_ai_existing_project_clusters`) on
    every heavy processor run when ≥2 unprojected open tasks exist. Options:
    run at most once per day, or only when the unprojected-task fingerprint
    changes. Interim toggle: `RUN_EXISTING_TASK_PROJECT_DISCOVERY=false`.
2.  **Instrument AI call counts** — add a per-run tally in processor logs
    (calls by category: inbox, duplicate, project work, focus, etc.) so
    before/after savings are visible without guessing from OpenAI dashboards.
3.  **Merge inbox title-prep calls** — `prepare_task_title` can chain up to
    three sequential calls (noun rewrite, hard rewrite, soft rewrite). Consider
    one structured JSON call when rule-based prep is insufficient.
4.  **Merge clarification route + suggestions** — clarify-routed tasks may hit
    `ask_ai_clarification_route` and `generate_clarification_suggestions`
    separately; combine when rule-based routing is not already confident.
5.  **Batch duplicate detection** — `judge_duplicate` runs per inbox item with
    lexical candidates; batch multiple new titles in one run when several
    captures arrive together.
6.  **Project work generate + validate** — two calls per generation by design
    (fail-closed grounding). Consider a single-call path for low-stakes automatic
    gap-filling only; keep the two-call path for manual generation.
7.  **Focus guidance vs activation overlap** — review whether legacy
    `ensure_focus_guidance` is still needed now that activation children are
    canonical; guidance is fingerprint-cached but may be redundant on BNA change.

#### Principles (unchanged)

Before optimizing further, prefer simple, general reductions:

-   Better caching and fingerprinting when inputs have not materially changed.
-   Event-driven or state-driven generation instead of running on every
    processor pass.
-   Consolidating calls where doing so does not reduce quality.
-   Throttling or scheduling heavy batch passes (project discovery) separately
    from inbox-driven work.

Preserve high-value AI behavior such as context coaching rather than optimizing
credits blindly. Prefer simple general reductions over new special-case logic.

Do not start the next item until normal use after the August 21 changes shows
whether further reduction is still needed.

### Execution intelligence

Continue improving BNA, Quick Wins, JDI, focus guidance, and execution
ranking when real use reveals specific shortcomings.

The objective is not to continuously add scoring rules. Prefer better
use of shared task/project state and AI reasoning where appropriate.

------------------------------------------------------------------------

## 6. Development Approach

### Build from demonstrated need

Use AIOS regularly between major feature additions. Real-world use is
now an important part of development.

For AI-heavy features such as Project Work:

1.  Implement the simplest viable reasoning model.
2.  Test against varied real projects.
3.  Record good and bad outputs.
4.  Identify repeated failure patterns.
5.  Tune only when the evidence supports a general improvement.

### Control complexity

Before implementing a feature, ask:

-   Does this require a new concept, or can an existing abstraction
    handle it?
-   Are we creating a second pathway for something AIOS already does?
-   Is the behaviour general, or are we hard-coding one domain/use case?
-   Will this create long-term compatibility or cleanup work?
-   Can the same outcome be achieved more simply?

If complexity grows disproportionately to the user value, simplify or
defer.

### Prefer one authoritative path

Supabase is the authoritative task/project datastore and the web/API
architecture is the primary application path.

As migration completes, remove superseded compatibility code instead of
indefinitely maintaining old and new implementations.

------------------------------------------------------------------------

## 7. Near-Term Sequence

Unless functional testing uncovers a higher-priority defect, the working
sequence is:

1.  Finish Daily Journal V1/V1.1 functional acceptance testing.
2.  Continue Project Work V3 acceptance testing during normal AIOS use.
3.  Validate possible-duplicate and clarification workflows in normal
    use.
4.  Clean up obsolete Notion review/runtime pathways after parity is
    confirmed.
5.  Advance source-neutral Brain Dump / capture.
6.  Validate async UI polling (dashboard, breakdown, project work,
    reviews) in normal use.
7.  Design Recurring Tasks before implementation.
8.  Observe AI spend optimizations in normal use for a few days; revisit
    **AI usage / credit efficiency** next opportunities if needed.
9.  Continue **UX polish and feedback consistency** — empty-state copy fixes are
    next after focus context loading feedback.
10. Consider SSE (Phase 3) only if polling validation shows latency or
    load problems worth solving, or processor event emission is ready.
11. Choose subsequent improvements based on actual AIOS usage rather
    than adding features speculatively.
12. When stabilization load allows, begin **workspace tenancy Phase 1**
    (schema + default workspace backfill) before more feature surface area
    accumulates without `workspace_id`.

------------------------------------------------------------------------

## Completed Milestones

Recent milestones that materially changed the architecture:

-   Supabase established as authoritative datastore for tasks and
    projects.
-   Supabase execution-state persistence established.
-   Possible-duplicate review cut over to Supabase/web.
-   Clarification review cut over to Supabase/web.
-   Native Supabase-only task creation established.
-   Project Context added as human-editable durable project grounding.
-   Project Work generation and proposal-feedback loop established.
-   Dashboard focus / Start Here guidance implemented.
-   BNA completion behaviour implemented.
-   Task-detail origin navigation restored.
-   Dashboard search considered fixed.
-   Daily Journal V1/V1.1 implemented and entering normal-use
    validation.
-   Dashboard async UI: focus-card and task-list JSON polling; undo
    sync; breakdown, project work, and review pending-fragment polling
    (Phases 1--2b).
-   AI spend optimizations: project-work generation fingerprint cache,
    processor light-maintenance gating, and 30-minute scheduled processor
    cadence (August 21, 2026).

------------------------------------------------------------------------

This roadmap should be updated when an item changes status, a new
significant feature is accepted onto the roadmap, or functional testing
materially changes the planned sequence.
