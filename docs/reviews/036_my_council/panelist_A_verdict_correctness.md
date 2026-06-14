# Panelist A — Verdict Correctness & Fidelity (FR-55, instr 036)

**Charter:** VERDICT CORRECTNESS & FIDELITY — exercise the code, don't trust claims.
**Repo:** `/Users/andrewstellman/Documents/wakecycle`
**HEAD:** `4e43568ce794bf525d2d8e4f5d1e14dcd4cc33af` ("FR-55: 3-panel load-bearing review (unanimous SHIP)") — matches the claimed `4e43568`.
**Suite size:** `230` tests (matches claim; `pytest --co -q | grep -c '::'` → `230`).
**`tests/test_continuation.py`:** 20 passed in 0.03s.

## VERDICT: **SHIP** (with 1 documented CONCERN, non-blocking)

The continuation verdict is a genuine pure function of disk state across the whole closed set; every member of `_CONTINUATION_REASONS` is reachable and emitted (not merely declared); persisted status — not raw control-file presence — is read; STOP stays byte-for-byte read-only; `next_tick_due`/`monitoring_paused` are carried and correct; and the load-bearing pin bites under mutation. Nothing rises to FIX-REQUIRED.

---

## Findings

### Finding 1 — Closed set is exhaustively reachable; all three "suspect" reasons are genuinely computed (PASS)
`_CONTINUATION_REASONS` (tick.py:761-763) = `{done, failed, stop, pause, cancel, blocked, stalled, budget, internal_error}`. I traced each to an emission site in `_halt_reason` (tick.py:784-824) / `_continuation` (tick.py:827-851):

- `stop` — tick.py:796-797 (`stop` arg or persisted `stopped`). Tested.
- `cancel` — tick.py:798-799 (persisted `cancelled`). Tested.
- `done` / `failed` — tick.py:801-802: all-terminal → `done` iff all `completed`, else `failed`. Tested.
- `blocked` — tick.py:804-805 via `_open_blockers`. Tested (`BlockerLifecycle`).
- `pause` — tick.py:806-807 (persisted `paused`). Tested.
- `budget` — tick.py:808-809 (persisted `budget_exhausted`). **Genuinely computed**, tested (`test_budget_flag`).
- `stalled` — tick.py:813-823: non-terminal ∧ none progressing ∧ no free dispatchable slot ∧ ≥1 `stalled` run. **Genuinely computed**, tested by `test_stalled_wedge` plus two negative cases (`..._if_a_run_is_progressing`, `..._if_a_free_slot_can_dispatch`).
- `internal_error` — tick.py:835-836: `_continuation` wraps `_halt_reason` in `except Exception`. **Genuinely reachable** — proven empirically (Finding 2).

No declared-but-unreachable reason. The set is closed and the `test_reason_is_always_in_the_closed_set` invariant guards it.

### Finding 2 — `internal_error` is reachable but UNTESTED (CONCERN, non-blocking)
This is the only closed-set member with zero test coverage. `grep -rn internal_error tests/test_continuation.py` → none. I proved reachability empirically by feeding malformed status into the live module:

```
_halt_reason raises on malformed status: AttributeError - 'int' object has no attribute 'values'
_continuation on malformed status -> HALT internal_error
reason in closed set: True
verdict_str: HALT:internal_error
None-run-record -> HALT internal_error
```

So `internal_error` is real, not declared-only: a fault inside `_halt_reason` (e.g. `status["runs"]` non-dict, or a `None` run record) is caught and converted to `HALT:internal_error`, keeping the set closed rather than crashing the tick. **Why CONCERN not FIX:** the reason is genuinely computed and the closed-set invariant test would catch a regression that produced an off-set value. But the catch-all path itself has no direct test, so a future refactor that broke the `except` (e.g. narrowed it, or let the exception escape `tick()`) would pass the whole suite. A one-line test asserting `_continuation(rd, {"runs": 123}, ...)["reason"] == "internal_error"` would close this. Non-blocking for SHIP.

### Finding 3 — `failed` covers `auth_or_launch_failed` and `abandoned` (PASS)
`_TERMINAL_STATES` (tick.py:87) = `("completed", "failed", "auth_or_launch_failed", "abandoned")`. Because `done` requires `all(s == "completed")` (tick.py:802), any terminal set containing `auth_or_launch_failed`, `abandoned`, or `failed` falls to `failed`. Confirmed by `test_failed_any_non_clean_terminal` (test:57-60), which asserts all three of `["completed","failed"]`, `["abandoned"]`, `["auth_or_launch_failed"]` → `"failed"`. Passes.

### Finding 4 — Reads PERSISTED status, not control-file presence (PASS)
`_halt_reason` keys off `status.get("paused"/"stopped"/"cancelled"/"budget_exhausted")` and terminal run states — all persisted fields — never off file existence. The docstring (tick.py:786-792) and `test_pause_reads_persisted_status_not_file` (test:66-68) confirm: a consumed PAUSE (`paused:true`, no file) → `HALT:pause`. STOP is the deliberate exception (read-only gate, never consumed) so the `stop` arg carries the file truth; `test_stop_from_file_or_persisted_flag` covers both the file path and a persisted `stopped:true`. Precedence is correct: `test_precedence_terminal_beats_stale_pause` (completed+stale paused → `done`) and `test_precedence_stop_beats_done` both pass.

### Finding 5 — STOP tick is byte-for-byte read-only (PASS)
`tick()` gates ALL persistence inside the `if not stop:` branch (tick.py:911-968); the `else` branch (969-977) computes the verdict for the return value but performs **no** `_write_json` and **no** `_append_journal`. The test `test_stop_tick_emits_halt_stop_but_writes_nothing` (test:203-215) is a true byte-compare: it snapshots `read_bytes()` of both `harness_status.json` and `journal.ndjson` before the STOP tick and asserts equality after, with the failure messages naming the exact regression. The worker's "byte-verified" claim is accurate. Passes.

### Finding 6 — `next_tick_due` + `monitoring_paused` carried and correct (PASS)
`_continuation` (tick.py:837-841): `next_tick_due = int(round(now + next_minutes*60))`, `monitoring_paused = bool(status.get("monitoring_paused", False))`. `test_next_tick_due_and_monitoring_paused` (test:136-142): `now=1000, next_minutes=5` → `next_tick_due == 1000 + 5*60 == 1300`, and `monitoring_paused` is carried `True`. Passes. The `try/except` around the arithmetic degrades a bad `next_minutes` to `None` rather than crashing — sound. (`monitoring_paused` semantically suspends the abandonment clock; that field is carried faithfully here — its downstream effect on the abandonment clock is outside this module's surface but the carry is correct.)

### Finding 7 — MUTATION-BITE: the pin genuinely bites (PASS)
I mutated `_halt_reason` in the working tree (backed up to `/tmp/tick_orig.bak`) two ways and ran the suite, then restored via `git checkout` each time:

**(a) Broad mutation** — early `return "done"` at top of `_halt_reason`:
```
15 failed, 5 passed in 0.10s
FAILED ...test_continue_healthy_midrun   <-- the load-bearing pin
```

**(b) Surgical mutation** — only the CONTINUE result (`return None` → `return "done"`), isolating the pin:
```
FAILED tests/test_continuation.py::HaltReasonClosedSet::test_continue_healthy_midrun
E       AssertionError: 'done' is not None
tests/test_continuation.py:52: AssertionError
1 failed in 0.04s
```

The healthy-mid-run → CONTINUE assertion (test:51-52) catches a verdict that diverges from state (the exact bug FR-55 §192/§199 cares about: a host believing a live run is `done`, hiding abandonment). The pin is load-bearing and bites precisely.

**Restore integrity:** after the broad mutation, `diff -q /tmp/tick_orig.bak arunner/engine/tick.py` → byte-identical; `git status --short arunner/engine/tick.py` → clean after both mutations. `/tmp/tick_orig.bak` removed. Final `git status` shows only pre-existing untracked `SDLC.md` and `docs/TRACEABILITY.md` (unrelated to this work); `tick.py` and `tests/` are clean.

---

## Spec fidelity summary (REQUIREMENTS.md FR-55, §192/§199)
- Pure function of run-dir state: **confirmed** (no I/O beyond reading persisted status + blocker records; deterministic).
- `CONTINUE` iff non-terminal ∧ status not paused/stopped/cancelled ∧ no open blocker ∧ progress possible: **confirmed** in `_halt_reason` precedence and the negative `stalled` cases.
- Closed halt set with every member reachable: **confirmed** (Findings 1-3).
- Persisted-status reads, STOP read-only: **confirmed** (Findings 4-5).
- `next_tick_due`/`monitoring_paused` carried: **confirmed** (Finding 6).
- Persisted + journaled each tick (non-STOP): **confirmed** (`test_continuation_persisted_and_journaled`, tick.py:962-968).

## Recommendation
**SHIP.** One non-blocking CONCERN (Finding 2): add a direct test for the `internal_error` catch-all to pin the closed-set guarantee under a `_halt_reason` fault. Everything else is correct, tested, and faithful to FR-55.
