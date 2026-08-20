# AIOS Roadmap

**Last updated:** August 20, 2026

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

### Project-task deferral

Previously identified but intentionally lower priority. Revisit when
there is a demonstrated need and a clean general model.

------------------------------------------------------------------------

## 5. Later / Strategic

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

**Parking lot — review after the current testing-heavy period.**

AIOS is making greater use of AI and development testing may be inflating
current credit consumption. Before optimizing, instrument and understand normal
usage.

Review each AI call for:

-   Frequency.
-   Trigger.
-   Cost.
-   User value.
-   Whether inputs materially changed since the previous call.

Look for simple, general reductions:

-   Better caching.
-   Avoiding regeneration when inputs have not materially changed.
-   Deduplicating equivalent calls.
-   Event-driven generation instead of running on every processor pass.
-   Consolidating calls where doing so does not reduce quality.

Preserve high-value AI behavior such as context coaching rather than optimizing
credits blindly. Prefer simple general reductions over new special-case logic.

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
6.  Design Recurring Tasks before implementation.
7.  Choose subsequent improvements based on actual AIOS usage rather
    than adding features speculatively.

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

------------------------------------------------------------------------

This roadmap should be updated when an item changes status, a new
significant feature is accepted onto the roadmap, or functional testing
materially changes the planned sequence.
