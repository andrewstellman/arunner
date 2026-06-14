# Panelist B — Detector Completeness (FR-55 continuation contract)

Reviewer B, 3-panel load-bearing review. Charter: the abandonment detector
MUST fire on every real violation and stay silent on every honest run.
Repo `arunner` at `/Users/andrewstellman/Documents/wakecycle`, work UNCOMMITTED.
Files: `tests/integration/checker.py` (`_detect_violations`),
`tests/integration/runner.py` (stub-host knobs),
`tests/integration/scenarios/continuation_*`,
`arunner/engine/tick.py` (`_append_journal`, engine ground-truth verdict).

## 1. The three violation classes fire on their configs — PASS

Verified each fires by running the scenario through the runner and calling
`_detect_violations(run_dir, meta)` directly (not the scenario's own `expected`):

- `continuation_abandon` ⇒ `['silent_abandonment']`.
  Journal tick 2 = `CONTINUE`; meta `host_stop=2 resumed=False eval_now=due+120`.
- `continuation_false_yield` (cites `"good checkpoint"`) ⇒ `['illegitimate_yield']`.
  `_cited_in_set("good checkpoint") == False` (outside the closed halt set).
- `continuation_false_halt_claim` (cites `HALT:done`, engine tick 2 = `CONTINUE`)
  ⇒ `['false_halt_claim']`.

Evidence the detector computes from disk, not from `expected`: `_detect_violations`
takes only `(run_dir, meta)`; it reads `journal.ndjson` (engine `type:"verdict"`
lines + host `type:"yield"` lines) and the runner's `_check_meta.json`
(`host_stopped_after_tick`, `resumed`, `eval_now`, `final_done`, `tick_trace`).
It never opens `scenario.json`. The closed halt set is duplicated locally
(`_HALT_REASONS`, checker.py:27).

## 2. No false-fire on honest runs — PASS

- `continuation_honor` ⇒ `[]` (yield `HALT:done` matches engine tick-4 `HALT:done`;
  `final_done=True`).
- `continuation_crash_then_resume` ⇒ `[]` (`resumed=True`, `final_done=True`;
  the `silent_abandonment` guard at checker.py:90 requires `not resumed`).
- `continuation_scheduled_gap` ⇒ `[]` (`eval_now = due-60 ≤ due+tol`; guard at
  checker.py:96-97 requires `eval_now > due + tol`).
- `continuation_blocked_then_clear` ⇒ `[]` (yield `HALT:blocked` matches engine
  `HALT:blocked`; blocker round-trips; `resumed=True`, `final_done=True`).

## 3. Cross-verdict check catches an in-set false claim — PASS

The most insidious case. `_detect_violations` (checker.py:75-85) compares each
host yield's `cited_verdict` against `engine_verdict_by_tick` — built ONLY from
engine-authored `type:"verdict"` journal lines. Ground truth is engine-side:
`arunner/engine/tick.py:863 _append_journal` writes `type:"verdict"`; the host
writes only `type:"yield"` (runner.py:256-261). The host's claim is never trusted.
Live evidence (`false_halt_claim`): engine journal tick 2 = `CONTINUE`, host yield
cites `HALT:done` → `cv != actual` → `false_halt_claim` fires.

## 4. The detector genuinely discriminates (can fail) — PASS

`python3 -m pytest tests/test_integration_scenarios.py -q` → green (incl.
`test_continuation_detector_discriminates`); full suite of the two files = 6 passed.
Read independently (test_integration_scenarios.py:72-94): it runs `abandon`, then
re-grades with `violations:[]` and asserts `check()` returns failures (detector
must NOT miss the abandonment); and runs `honor`, re-grades with
`violations:["silent_abandonment"]` and asserts failures (must NOT false-fire).
Confirmed in isolation: the discriminate test passes — not a rubber stamp.

## 5. scheduled_gap vs abandon differ ONLY by the clock — PASS

Side-by-side from live runs (identical `host_stop=2`, identical
`due=1781450520`, both tick-2 verdict `CONTINUE`, no yield, no resume):
- abandon:        `eval_now=1781450640` = due+120 → `eval_now>due+tol` True  → `['silent_abandonment']`
- scheduled_gap:  `eval_now=1781450460` = due-60  → `eval_now>due+tol` False → `[]`
The sole input that differs is `past_due`, which runner.py:255 turns into
`eval_now = due+cadence+60` vs `due-60`. The detector's silence on a scheduled
wait is principled, not accidental.

## 6. The checker stays stdlib-only — PASS

`python3 -m pytest tests/test_checker_independence.py -q` → 2 passed. AST scan
(test_checker_independence.py) bans `arunner/tick/ticker/heartbeat/demo_worker/bin`
and relative imports, and asserts every top-level import is in
`sys.stdlib_module_names`. checker.py imports only `json` and `os`.

## Adversarial observations (NON-BLOCKING)

(a) **Cross-check skips yields citing an orphan tick.** In `_detect_violations`
checker.py:83-84, if a yield cites a tick with no engine `verdict` line,
`actual is None` and the `false_halt_claim` comparison is silently skipped.
A synthetic probe (host yield at tick 99, no engine verdict there) returns `[]`.
A dishonest host could cite a true reason against a fabricated tick number and
evade the cross-check. No current scenario exercises this — the runner always
cites `status.get("cycle")`, which aligns with the engine's tick — and the
contract assumes well-formed tick keys, so it does not affect the suite. Worth a
future hardening note (treat a cited tick absent from the engine journal as a
violation), not a ship blocker.

(b) **`false_halt_claim` masking is timing-defended, not timing-fragile — verified.**
The class only fires when engine tick-2 verdict is `CONTINUE`; if the engine
legitimately reached `HALT:done` by tick 2 the host's `HALT:done` would match and
the class would NOT fire (a masked detection). I stress-tested this: 30 serial +
24 thread-parallel (8-way) runs all produced tick-2 = `CONTINUE` and `check()`
PASS. With `pool_size=1` and 3 jobs, plus the deterministic `_settle()`
heartbeat wait, done cannot arrive before ~tick 4, so tick 2 is reliably
`CONTINUE`. One anomalous early-done run appeared only on the very first scenario
of a cold back-to-back 4-scenario loop and was not reproducible in 54 subsequent
runs. Low risk; the masking pathway is structurally closed by the pool/settle
design. Not a blocker.

## Conclusion

All three violation classes fire on their configs and compute from disk
(engine journal + meta), never from the scenario's `expected`. All four honest
runs stay silent, each for a principled reason (resume, scheduled-clock,
verdict-match). The cross-verdict check uses engine-authored ground truth and
never trusts the yield. The detector discriminates (the meta-test would fail a
rubber stamp). The checker is mechanically stdlib-only. scheduled_gap and abandon
differ solely by the clock. The two observations above are real but narrow and
unexercised by the contract; neither breaks a charter requirement.

VERDICT: SHIP
