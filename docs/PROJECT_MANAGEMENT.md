# Project management guide

How work is organized on the GitHub board, so anyone (or any coding agent) can pick up an issue and know what to do.

## Structure

```
Milestone (phase)          M1 Baseline and platform | M2 The plant | M3 Defend and harden | M4 Demo and release
  Sprint (tracker issue)   Sprint 0 ... Sprint 7, each with goal, task list, exit criteria
    Task issues            sized, tagged, with a user story and acceptance checkboxes
```

| Milestone | Sprints | Done when |
|---|---|---|
| M1 - Baseline and platform | 0, 1 | The current build is rebuildable from the docs; the Kali seat sees only intended hosts and ports |
| M2 - The plant: sensors, control, physical process | 2, 3, 4 | Stages 5-10 work end to end; the interlock trips to a safe state |
| M3 - Defend and harden | 5, 6 | Every attack raises an alert and fails against the hardened build |
| M4 - Demo and release | 7 | A first-time visitor sees attack, detection and hardened block |

Sprints are not time-based. A sprint ends when its exit criteria are met and the owner approves.

## Sizes (effort for one person)

| Label | Size | Time |
|---|---|---|
| `size:S` | Small | about 1 day |
| `size:M` | Medium | about 3 days |
| `size:L` | Large | about 1 week |

If a task grows past Large, split it into smaller issues.

## Where the work happens

| Label | Meaning |
|---|---|
| `where:remote` | Doable from home: research, docs, design, code that is compile-checked only |
| `where:lab-hardware` | Needs the bench: wiring, sensors, flashing, physical tests |
| `where:lab-network` | Needs the plant/lab network: Pi, broker, firewall, Kali seat, scans |

A task can carry both lab labels. Rule of thumb: write and design remotely, then run a separate lab task to verify on real hardware.

## Other labels

- **Sprint:** `sprint:0` to `sprint:7` filter tasks by sprint; `sprint` marks the tracker issue.
- **Kind:** `deliverable`, `spike`, `decision`, `gate` (owner approval needed), `stretch`, `priority:high`.
- **Status:** `status:ready`, `status:in-progress`, `status:blocked`, `status:needs-review`. Closed means done.
- **Area:** `documentation`, `firmware`, `hardware`, `infrastructure`, `security`, `safety`, `dashboard`.

## Progress markers

- Every issue has acceptance-criteria checkboxes. GitHub shows `x of y` next to the issue in the list.
- Each sprint tracker has a task list with checked boxes for closed tasks. Run `python tools/apply.py --sync` to refresh it, or tick by hand.
- Each milestone shows percent complete from open vs closed issues.
- Status labels show who is doing what right now.

## Issue anatomy (written to be agent-friendly)

1. **Header:** sprint, milestone, size, where, deliverable/output path, dependencies, status.
2. **User story:** As a (role), I want (goal), so that (benefit).
3. **Acceptance criteria:** checkboxes; each one is observable and testable.
4. **Verification:** how to prove it; defaults to recording results in `docs/VERIFIED.md`.
5. **Inputs and outputs:** files to read and files to produce.
6. **Agent guidance:** what is safe to do remotely; for lab tasks, the human steps.
7. **Guardrails:** secrets, no commits without approval, no invented facts, public-only information, stop before irreversible steps.
8. **Done when:** criteria ticked, docs updated, status updated, issue closed.

## Working a task

1. Pick a `status:ready` issue; check its dependencies are closed.
2. Set `status:in-progress`.
3. Do the work; tick criteria as you go; keep changes small.
4. Record what was verified and what was not in `docs/VERIFIED.md`.
5. Set `status:needs-review`; the owner reviews and closes. Gate issues need explicit owner approval.

## Changing the plan

Structure lives in `tools/plan_data.py` (labels, milestones, sprints, tasks). Edit it and re-run `python tools/apply.py`. Existing issues are matched by a hidden key and are not overwritten, so ticked checkboxes stay. Use `--force-bodies` only when you want to reset an issue's text.

## Public-repo rule

This repository and its issues are public. Never put flag values, the answer key, real Wi-Fi credentials, certificates or anything controlled or sensitive in code, docs or issues.
