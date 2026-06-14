# Panelist A — Fidelity Review (Instruction 042)

Charter: each acceptance test mirrors its UC at the correct rung. Verified against
`docs/ACCEPTANCE_TESTS.md` (authoritative runbook) and the uncommitted plans/checker.

## 1. UC-2/3/4 are real SUBAGENT plans (rung 1) — PASS
All three plans (`uc2_monitor`, `uc3_halt`, `uc4_resume`) have every entry with
`dispatch_mode: "subagent"` and a `worker_prompt` that is the trivial heartbeat
stub ("emit STARTING + COMPLETED, return one-line ack, do nothing else"). No
`worker_cmd`, no `adapter` field on any entry.

Preview check (engine `preview … | tail`):
```
uc2_monitor: job 1/2 SUBAGENT  --check: OK - no problems found. Safe to run.
uc3_halt   : job 1/2 SUBAGENT  --check: OK - no problems found. Safe to run.
uc4_resume : job 1/2 SUBAGENT  --check: OK - no problems found. Safe to run.
```
All `--check: OK`. The stub prompt is the heartbeat stub the runbook §"Two run
paths" prescribes for the in-agent rung-1 path. Correct.

## 2. UC-2 grades the idempotent tick-now affordance, not table serialization — PASS
`uc2_expected.json` keys: `done:true`, `counts.completed:2/failed:0`,
`run_states` both `completed`, **`no_double_dispatch: true`**. It grades that an
extra tick advances only the cycle and never re-dispatches — exactly the lived
"tick now" monitor affordance (runbook UC-2 / FR-6). It does NOT attempt to grade
table-vs-status text; that table-reading leg is explicitly agent-self-reported in
the runbook §"Disk-gradeable vs agent-reported" and the table-vs-status check is
the floor's `test_cli`, not this plan. Graded the right thing.

## 3. UC-4 covers both resume legs + the wall-clock-jump leg — PASS
No implementer `outputs/042-*.md` exists (work is uncommitted; only `reviews/` is
present) — verified from runbook + plan + engine instead.
- `uc4_resume.json`: `pool_size: 1`, 2 entries ⇒ entry-2 is QUEUED while entry-1
  runs. Abandon mid-run, then resume: the queued entry-2 is the one that gets
  dispatched; the `no_double_dispatch:true` in `uc4_expected.json` asserts the
  done entry-1 is NOT re-dispatched. (a) Re-bootstrap-on-resume leg and (b)
  `ticker.py --once` reap-resume leg are both documented in the runbook
  (ACCEPTANCE_TESTS.md line 29: "(a) re-bootstrap a fresh session … (b) separately
  resume via `ticker.py --once`; both must continue with no double-dispatch").
  `arunner/engine/ticker.py --once <run-dir>` is the real single-tick entry point.
- (c) Hibernate/wall-clock-jump leg is documented same line ("inflated heartbeat
  ages → wall-clock-jump guard, not a false STALL").

INDEPENDENT guard check (`arunner/engine/tick.py`): E2 suppression is real.
`suppress_stall = last_wall is not None and (now-last_wall) > max(stall_secs,
tick_interval*60) * _WALLCLOCK_JUMP_FACTOR` (factor=4). The stall branch
(line ~1058) is gated `and not suppress_stall`, so a worker whose heartbeat only
LOOKS stale because ARUNNER_NOW jumped far past the last tick is NOT marked
STALLED that tick. Additionally, a fresh terminal-on-disk worker is reaped to its
terminal state by the earlier terminal/`continue` paths BEFORE the stall branch is
reached — so it can never be false-STALLED regardless of the jump. Guard present
and correct.

## 4. UC-5/6/7 are the FLOOR (ticker + shell), not faked in-agent — PASS
`uc5_floor.json`: 3 entries, every one `dispatch_mode: "shell"` with a
`worker_cmd` invoking the stub (`python3 {STUB} --heartbeat … --steps 1`). Preview
confirms `SHELL  worker_cmd: …` for each. The preview `--check: FAILED` on
`{STUB}` is EXPECTED, not a defect: `{STUB}` is the integration runner's own
substitution (`tests/integration/runner.py:135` maps `{STUB}` → `stub_worker.py`),
identical to every existing shell scenario under `tests/integration/scenarios/*`.
The engine's preview legitimately doesn't know `{STUB}`; the ticker/runner does.
So these are genuine ticker-driven shell-dispatch floor plans, NOT faked in-agent.

Runbook documents the ticker procedure for the floor: §"Two run paths" line 8
("a real `ticker.py` invocation drives a shell-dispatch plan … the no-agent floor
cases UC-5, UC-6, UC-7"), and UC-5/6/7 entries (lines 30-32) — launch `ticker.py`
in a terminal (UC-5), install a schedule firing `--once` (UC-6), run `--once` by
hand (UC-7). UC-6/UC-7 reuse the same shell floor plan driven differently
(scheduler vs manual), so the absence of separate uc6/uc7 plan files is by design,
not a gap.

## Other checks
- `python3 -m pytest tests/test_acceptance_checker.py -q` → 12 passed. The checker
  CLI extension grades from durable artifacts as the runbook §Grading requires.

## Notes (non-blocking)
- No implementer output doc (`outputs/042-*.md`) found. All four charter items are
  verifiable from the plans + runbook + engine, so this did not block the review,
  but the missing demonstration write-up is worth noting for the panel.

VERDICT: SHIP
