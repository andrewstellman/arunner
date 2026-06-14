# Panelist A — Verdict Correctness & Fidelity (FR-55 continuation contract)

Reviewer A, 3-panel self-council, instruction 036. Charter: the continuation
verdict MUST be a true PURE FUNCTION of run-dir state. Work is UNCOMMITTED
(`git diff HEAD`). Engine: `arunner/engine/tick.py`. Unit tests:
`tests/test_continuation.py`. Independent checker: `tests/integration/checker.py`.

## 1. CONTINUE iff … else HALT:<reason> in the CLOSED set — VERIFIED

`_CONTINUATION_REASONS` (tick.py:761) is the closed frozenset
`{done, failed, stop, pause, cancel, blocked, stalled, budget, internal_error}`.

`_halt_reason` (tick.py:784) precedence, read top-to-bottom:
1. `stop or status["stopped"]` → `stop` (operator control dominates a live run)
2. `status["cancelled"]` → `cancel`
3. all states terminal → `done` if all `completed` else `failed`
4. open blocker on disk → `blocked`
5. `status["paused"]` → `pause`
6. `status["budget_exhausted"]` → `budget`
7. non-terminal wedge (no run progressing ∧ no free pool slot ∧ a stalled run)
   → `stalled`
8. else `None` → CONTINUE

I independently exercised every reachable member and confirmed membership:

```
reachable closed-set reasons: ['budget','cancel','done','failed','pause','stalled','stop']
all in closed set: True
```

`blocked` separately confirmed (§6); `internal_error` separately (below).
Precedence spot-checks all correct:
- `stop beats done` → `stop` (a STOP on an all-completed run still halts as stop)
- `terminal(done) beats open blocker` → `done` (a finished run is done regardless
  of a stale on-disk blocker)
- `open blocker halts a LIVE run` → `blocked`
- `cancel beats blocked` → `cancel`

`internal_error` catch-all (tick.py:835): I forced a genuine fault inside
`_halt_reason` (a `runs` mapping whose `.values()` raises). Direct call raised
`RuntimeError`; routed through `_continuation` it became `HALT:internal_error` —
the `except Exception` keeps the set closed:

```
direct _halt_reason raises?: YES -> RuntimeError boom
internal_error via _continuation -> HALT internal_error
```

(Note: an earlier probe of mine using an empty-but-`.values()`-raising dict
returned CONTINUE — that was a flawed harness, because `status.get("runs") or {}`
discards a *falsy* mapping; a truthy faulting mapping correctly yields
`internal_error`. No defect.)

## 2. Reads PERSISTED status, not raw control-file presence — VERIFIED

`_halt_reason` reads `status["paused"]`, `status["cancelled"]`,
`status["stopped"]`, `status["budget_exhausted"]` and the run `state`s — never
probes for a PAUSE/CANCEL control file. The docstring (tick.py:789-792) states
this explicitly. STOP is the deliberate exception: never consumed (FR-10
read-only gate), so the STOP file IS the truth, carried via the `stop`
parameter (set from `(run_dir/"STOP").exists()` at tick.py:898). Unit pin
`test_pause_reads_persisted_status_not_file` (a consumed PAUSE leaves
`paused:true` and no file → `pause`) passes.

## 3. next_tick_due + monitoring_paused carried — VERIFIED

`_continuation` (tick.py:827) builds `{verdict, reason?, blocker_id?,
next_tick_due, monitoring_paused}`. `next_tick_due = int(round(now +
next_minutes*60))` derived from the tick's `next_tick_minutes` (FR-5);
`monitoring_paused` from persisted status. `test_next_tick_due_and_
monitoring_paused` pins `next_tick_due == 1000 + 5*60` and the flag. Pass.

## 4. Written each tick + journaled; STOP tick writes NOTHING — VERIFIED

`tick()` not-stopped branch (tick.py:962-968): `status["continuation"] = cont`
then `_write_json(harness_status.json)` then `_append_journal(...)`. STOP branch
(tick.py:969-977): computes `cont` for the return envelope ONLY — no status
persist, no journal append (comment at 975-976 is explicit). Pin
`test_stop_tick_emits_halt_stop_but_writes_nothing` does a byte-for-byte
`read_bytes()` comparison of BOTH `harness_status.json` and `journal.ndjson`
before/after a STOP tick and asserts equality — passes, so the read-only
invariant is preserved. The `stop_readonly` integration scenario still passes.

## 5. Verdict-fidelity + load-bearing mutation pin — VERIFIED (pin BITES)

`python3 -m pytest tests/test_continuation.py -q` → **20 passed**.

Mutation pin (the most dangerous bug = a verdict that diverges from state):
- Snapshot `tick.py` → `/tmp/tick_036_pristine.py` via `shutil.copy2`.
- Mutated `_halt_reason` to `return "done"` for a non-terminal run.
- Purged `__pycache__` (scoped `-not -path './repos/*'`).
- `tests/test_continuation.py::HaltReasonClosedSet::test_continue_healthy_midrun`
  → **FAILED**: `AssertionError: 'done' is not None`. The pin BITES.
- Restored via `shutil.copy2` from the pristine snapshot (NOT git checkout),
  re-purged pycache. `filecmp.cmp(..., shallow=False)` → True; mutation residue
  grep → clean.
- Re-ran: `tests/test_continuation.py` → **20 passed**.

## 6. Blocker lifecycle — VERIFIED

`_open_blockers` (tick.py:766) reads host-authored `<run_dir>/blockers/*.json`,
OPEN while `cleared_at` is null; engine only READS (never writes the dir).
`_continuation` sets `blocker_id` from the first open blocker. Open blocker on a
live run → `HALT:blocked` with the id; cleared → CONTINUE. Pins
`test_open_blocker_halts_blocked` / `test_cleared_blocker_resumes_continue` pass,
plus the `continuation_blocked_then_clear` integration scenario (block at tick 2,
HALT:blocked at tick 3, clear + resume to done; detector silent).

## 7. Full suite — VERIFIED

`python3 -m pytest -q` → **230 passed** (run twice, both green). Working tree
matches the pristine snapshot byte-for-byte after restore.

## Additional confirmations

- **Engine ↔ independent checker closed sets are in lockstep** (intentionally
  duplicated; checker imports no repo code):
  `T._CONTINUATION_REASONS == C._HALT_REASONS` → True.
- The 7 `continuation_*` scenarios cover the three violation classes
  (silent_abandonment, illegitimate_yield, false_halt_claim) AND the four honest
  paths (honor, crash_then_resume, scheduled_gap, blocked_then_clear);
  `test_continuation_detector_discriminates` passes (fires on abandon, silent on
  honor). The `abandon` config is the literal incident reproduction
  (CONTINUE + host gone past next_tick_due + no yield + never resumed).

## Adversarial checks that did NOT find a defect

- No reason outside the closed set is reachable (exhaustive probe + the
  `test_reason_is_always_in_the_closed_set` pin).
- No file-presence read substitutes for persisted status (pause/cancel/budget
  all from `status`; only STOP reads the file, by FR-10 design).
- The STOP tick provably writes nothing (byte comparison pin).
- The mutation pin genuinely bites and restoration is genuinely clean.

VERDICT: SHIP
