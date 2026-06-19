# Planned: FR-61 (subagent-mode liveness fix) + FR-62 (Textual TUI)

*Roadmap doc, drafted 2026-06-17. Execute AFTER the in-flight secbench-2 doc-gather run finishes (don't perturb a running orchestrator). Both go through the established arunner change process — an instruction → Claude Code worker → self-Council — NOT a direct Cowork edit. FR-61 is small and fixes active pain; do it first. FR-62 (the TUI) is a normal feature build: the TUI is a fully decoupled, read-only consumer of disk state (FR-59), so its dependencies never touch the stdlib-only engine — no special review bar.*

---

## FR-61 — Subagent-mode workers must not be false-failed on heartbeat absence

### The bug (observed 2026-06-17, secbench-2 doc-gather run)

Two gather workers (`adonisjs-http-server`, `ech0`) were marked `auth_or_launch_failed` (terminal) while they were alive and **successfully producing full 14-file doc corpora on disk**. A third (`addressable`) finished its work but stuck in `running`. Root cause, verified in `tick.py`:

- Completion is recorded **only** via a heartbeat line whose status field is `COMPLETED` (`_terminal_status_of` scans the heartbeat file). Liveness at launch is **only** "any heartbeat within `launch_grace_minutes`" (default 10). The engine has **no awareness of a worker's actual output** — only its heartbeat.
- This is correct for **shell mode**: the ticker `Popen`s the worker and genuinely owns the process, so no-heartbeat-past-grace legitimately means dead.
- It is **wrong for subagent mode**: the engine does NOT own the worker — the orchestrator's Task subagent does. The engine only sees heartbeats and has no authority to observe that subagent's liveness. Applying the shell-mode "no heartbeat → terminal LAUNCH-FAIL" makes the engine declare workers dead it cannot actually see. A subagent that does real work but doesn't self-heartbeat (or starts slowly) gets false-terminal-failed — and `auth_or_launch_failed` is **terminal and irreversible** (`tick.py` line ~926: "NEVER un-terminals a finished run").

This is **mode-confusion**: shell-mode liveness assumptions applied to subagent-mode workers, where the engine lacks process authority.

### Why this is a real bug, not "working as designed"

arunner **already** commits to the no-false-fail invariant — for shell workers. **FR-40** (the `heartbeat.py wrap` adapter) exists so "a long-running quiet command never false-trips LAUNCH-FAIL or STALLED," emitting STARTING on launch + periodic beats on the command's behalf, with "doneness from the exit code, never from parsing output." FR-61 extends that same, already-blessed invariant to subagent mode, which currently has no adapter providing it.

### Fix — two layers

**Layer A — worker-prompt mitigation (cheap, immediate, not an engine change).** A subagent worker_prompt must emit a heartbeat **immediately on launch** (`STARTING`) and a terminal (`COMPLETED`/`FAILED`) at the end — the QPB audit workers do this via the skill's phase flow, which is why they never false-fail; the ad-hoc gather prompt didn't, which is why they did. Fix the gather plan (and add a worker-prompt convention to TOOLKIT) so the first action a subagent takes is a `STARTING` heartbeat. This alone would have prevented every false-fail in this run.

**Layer B — engine hardening (the actual FR-61).** Even with disciplined workers, the engine should not autonomously terminal-fail what it cannot observe. Options, to be Council'd:

1. **Subagent-mode launch-grace is advisory, not terminal.** In subagent mode the orchestrator owns the worker's life; the engine surfaces a `LAUNCH-SLOW`/`NO-HEARTBEAT` *warning* but does not move the entry to `auth_or_launch_failed`. The slot is reconciled when the orchestrator records the subagent's return (the subagent-mode analogue of the shell exit code). A long hard cap (≫ grace) can still reclaim a genuinely-hung slot, but the default short grace must not be terminal in this mode.
2. **Orchestrator emits the lifecycle on the subagent's behalf** (mirrors FR-40's wrap adapter): the dispatch path writes `STARTING` when it launches the subagent and the terminal status when the Task returns — so completion/failure never depends on the worker's own heartbeat discipline. This is the most principled fix: it gives subagent mode the exact guarantee FR-40 gives shell mode.
3. **Result-artifact reconciliation (defense in depth).** Before *or after* a terminal-fail verdict, if the worker's standard result artifact exists, reconcile to `completed`. Tension: this would relax the "terminal is final" invariant, so it's the least preferred unless scoped to "a launch-fail with a present result reconciles to completed" as a narrow, mutation-pinned carve-out.

Recommended: **2 (orchestrator emits lifecycle) as the primary**, with **1 (advisory grace in subagent mode)** as the safety net. Keep `auth_or_launch_failed` reachable only where the engine has authority (shell-mode spawn/auth failures, FR-42 pre-flight) or after the long hard cap.

### Route
Instruction → Claude Code worker → **mandatory 3-panel self-Council** (charters: A — state-machine correctness & the terminal-invariant; B — shell-vs-subagent mode parity & FR-40 consistency; C — regression/idempotency, no false-completion of genuinely-dead workers). Add the FR-61 row to `docs/REQUIREMENTS.md` §9. Pre-flight: capture a regression test that reproduces *this* run's false-fail (a subagent that writes output but no heartbeat must end `completed`/`stalled`, never `auth_or_launch_failed`).

---

## FR-62 — Textual TUI: choose a run → monitor → drill into an entry → tail its log

### Scope (from the request)
An interactive terminal app that lets an operator: (1) **list/choose a run** from the available run-dirs; (2) **monitor** the chosen run live (the FR-59 table, refreshing); (3) **drill into an individual entry** to see its details (state, target_repo, dispatch mode, heartbeat history, result record); (4) **tail that entry's log / heartbeat stream**. An evolution of FR-59's read-only-disk-rendering into a navigable UI.

### The dependency question is already resolved by the FR-59 decoupling
The stdlib-only/no-framework guarantee (FR-54, NFR-3) is about the **engine** — `tick.py`/`ticker.py`, the deterministic state machine that must run wherever Python 3 does. The monitor/TUI is, by FR-59's design, a **fully decoupled, strictly read-only consumer** of externalized disk state — it never writes, takes no `.tick.lock`, fires no tick. A dependency that lives entirely inside that read-only viewer **does not touch the engine's guarantee at all.** So Textual in the TUI is fine — no identity tension, no special review bar.

The only remaining choice is trivial **packaging hygiene**: gate Textual behind an optional `arunner[tui]` extra (or a separate entry point), so a bare `pip install arunner` to run the engine on a minimal box stays dependency-free and "installs anywhere." That keeps the engine's install clean; it is not an architectural decision to agonize over.

### Design notes (assuming Option A)
- **Read-only first.** Match FR-59's strict never-writes property: the TUI only reads `harness_status.json`, per-entry heartbeat files, `plan.json`, `results/`, `journal.ndjson`. Ship read-only first so the safety property is trivially true. **Phase 2 — confirmed by Andrew 2026-06-17 (two features):**
  1. **In-flight overview on open.** The picker opens to a dashboard of ALL run-dirs under the runs dir with live per-run status (cycle / counts / done), and **visibly flags hung / stalled / false-failed / dead runs** — i.e. surface the FR-61 liveness states (stale-tick age, no-heartbeat-but-claimed, terminal-fail) so the operator sees the whole multi-run picture at a glance instead of `ls -dt` + opening each one. Motivated directly by the 2026-06-17 mess (6 run-dirs: 1 hung, several frozen, 1 done — invisible from the old monitor).
  2. **Kill a run.** Wire the existing **CANCEL (FR-39)** / **STOP (FR-10)** control verbs to a TUI keybind so a hung/unwanted run can be terminated and its slot freed. This **relaxes the strict never-writes property** — so it must be a *confined, explicit, confirm-prompted* write of a control file only; every OTHER view stays strictly read-only. Pin that boundary in tests + Council (the never-writes pin becomes "writes nothing except an operator-confirmed control file via the kill action").
- **Reuse, don't fork, the renderer.** The run-list and table views should call the same state-loading + `_format_table` path FR-59 uses, so the TUI can't drift from the monitor (the FR-59 council pinned "renderer-reuse-no-fork").
- **Views:** (1) run picker (list run-dirs newest-first with cycle/counts/done); (2) run view (the live table + verdict/next-tick line); (3) entry view (full per-entry record + heartbeat history + result record); (4) log/heartbeat tail (follow `<run-dir>/<run>/heartbeat.ndjson` and `journal.ndjson`).
- **Relationship to `arunner monitor`:** keep the stdlib `monitor` as the always-available zero-dep fallback; `arunner tui` is the richer optional sibling. Don't remove `monitor`.

### Route
Normal feature build — same lane as FR-59: instruction → Claude Code worker → **3-panel self-Council** (charters: A — read-only-safety: the TUI never writes / no `.tick.lock` / no tick, mutation-pinned like FR-59; B — renderer-reuse-no-fork so the TUI can't drift from `monitor`; C — packaging: Textual gated behind the `[tui]` extra so the bare engine install stays dependency-free). No external Council needed — the dependency lives in a decoupled read-only viewer, not the engine. Add FR-62 + the `[tui]` extra to `docs/REQUIREMENTS.md` and the README.

---

## Sequencing & open decisions

1. **FR-61 first** (small, fixes active pain; self-Council). Includes the Layer-A worker-prompt convention fix.
2. **FR-62 second** (larger; dependency decision needs Council first).

**Open decisions for Andrew:**
- **TUI control actions** — RESOLVED (Andrew, 2026-06-17): **yes** — add an in-flight overview on open + **kill/cancel a run** as FR-62 Phase 2 (details in the FR-62 design notes above). Read-only Phase 1 ships first; Phase 2 adds the one confined control write.
- **FR-61 engine fix shape** — orchestrator-emits-lifecycle (recommended) vs advisory-grace vs artifact-reconciliation (or a combination).

*(Resolved: Textual is fine — the TUI is decoupled + read-only, so it doesn't touch the stdlib engine; just gate it behind an optional extra for clean engine installs.)*
