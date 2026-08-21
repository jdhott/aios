# Using AIOS day to day

A short guide to the daily workflow in the web app. Routes are shown in parentheses.

## The loop

1. **Capture** what’s on your mind.
2. **Home** (`/`) shows what to do next.
3. **Act** on the focus card, or expand the task lists when you want more context.
4. **Review** (`/reviews`) anything AIOS flagged for a decision.
5. **Journal** (`/journal`) when you want to reflect on the day.

---

## Capture

Use **Brain Dump** whenever a task idea appears:

- Tap the **pencil** button (bottom-right on Home).
- Or press **⌘⇧B** on desktop.
- One bullet per task. Sentence case is fine.

AIOS turns each line into a task and routes duplicates or unclear wording to Review.

---

## Home and focus

Home is built around **one next step**, not a full dashboard.

**Focus card** — AIOS picks a **Best Next Action** (BNA) or **Start Here** guidance when the next step needs context first. From the card you can:

- Open the task
- Mark it done, snooze it, or say **Not now** / **Not useful**
- Add or edit focus context when AIOS asks

**Show More** — Reveals task lists in order: Top 5 → Quick Wins → Today → Just Do It → Completed Today.

**Show Less** — Collapses back to focus-only.

**Search** — Use the search box to find tasks across lists; search mode shows the full panel.

When lists are empty and you’re not searching, Home says **You're all caught up.**

---

## Tasks and projects

- Tap a task to open detail (`/tasks/{id}`): edit fields, breakdown, snooze, complete, delete.
- **Projects** (`/projects`) group related work. Open a project for outcome, context, tasks, and AI-generated work proposals.
- Checkbox and trash on Home use optimistic updates — you get immediate feedback while AIOS syncs in the background.

---

## Reviews

Open **Reviews** from the bottom nav when the badge appears.

AIOS sends work here when it needs your judgment:

**Possible duplicate** — A new capture may match an existing task. Choose:

- **Use existing task** — merge into what you already have
- **Replace with new wording** — keep the task but update the title
- **Keep as separate tasks** — they’re different work

**Clarification** — Wording was too vague. Edit the task title, accept a suggestion, answer a follow-up question, or delete the task if it wasn’t real work.

When both review queues are empty: **All caught up. Nothing needs your review right now.**

After you resolve a review, a brief confirmation toast appears at the bottom of the screen.

---

## Journal

**Journal** (`/journal`) is for daily notes and end-of-day reflection. Today’s entry and any pending AI summary appear on the main journal view.

---

## Tips

- Prefer **capture first, organize later** — Brain Dump is fast; Review handles ambiguity.
- Trust the **focus card** for “what now”; use **Show More** when you’re planning or clearing a category.
- If something looks stuck (spinner on a review card, focus not updating), wait a few seconds — AIOS often finishes async work in the background. Refresh if it persists.

---

*This guide is intentionally short. Expand it when the same “how do I…?” question comes up twice in real use.*
