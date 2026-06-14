# Panelist C — Honesty & Regression (FR-55 continuation contract)

Reviewer C, 3-panel load-bearing review. Charter: honesty (NFR-12 post-hoc framing,
§9 evidence fidelity, residual-hole disclosure) and regression (no engine behavior
broken). Work is uncommitted; reviewed via `git diff HEAD` + file reads + test runs.

## 1. Post-hoc, not prevention (NFR-12 honesty) — PASS

- Engine docstring (`arunner/engine/tick.py`, FR-55 header): *"The failure is caught
  POST-HOC, not prevented — see UC-11 / docs/INTEGRATION_TEST_PLAN.md."* The detector
  *flags*; nothing in `_continuation`/`_halt_reason` blocks a host stop.
- §9 row: *"**VERIFIED** (mechanism; post-hoc not prevention) ... catches abandonment
  post-hoc; a live audit ... is measurement, not a deterministic gate."*
- `docs/INTEGRATION_TEST_PLAN.md` "Honest limit (NFR-12)": *"it does not *prevent* a
  stop — silent abandonment is caught **post-hoc**."*
- No artifact claims the engine PREVENTS a host from stopping. Verdict is read, not
  authored (`status["continuation"]` persisted; host READS it).

## 2. §9 flip cites REAL evidence — PASS

- FR-55 row flipped PENDING → **VERIFIED**, citing `test_continuation.py`, the
  `continuation_{honor,abandon,crash_then_resume,false_yield,false_halt_claim,
  scheduled_gap,blocked_then_clear}` scenarios, and
  `test_integration_scenarios.py::test_continuation_detector_discriminates`.
- All cited tests/scenarios EXIST: `tests/test_continuation.py` present; all 7
  `tests/integration/scenarios/continuation_*/scenario.json` present.
- Cadence/Windows-floor row UNCHANGED — still PENDING (diff touches only the FR-55
  line of REQUIREMENTS.md; `git diff` shows a 1-line change).
- The FR-55 VERIFIED row contains NO "dogfooding"/"always-on" literal tokens (grep
  clean); it uses "live audit"/"measurement" — which the honesty guard does not
  forbid. Honest-limit note is explicit, not buried.

## 3. Honesty-guard test updated correctly — PASS

- `test_fr55_row_stays_pending` was correctly renamed/inverted to
  `test_fr55_row_is_verified` — now asserts `**VERIFIED**` AND `test_continuation`
  (a real in-repo test citation).
- CRUCIAL preserved guards confirmed UNCHANGED:
  - `test_floor_windows_row_stays_pending` (lines 47-50) — intact, still asserts
    PENDING + not VERIFIED for the Windows-floor row.
  - `test_no_verified_row_cites_dogfooding_or_alwayson` (lines 60-69) — intact, NOT
    weakened; still bans `dogfood`/`always-on` in any VERIFIED row.
- `python3 -m pytest tests/test_positioning_honesty.py -q` → **7 passed**.

## 4. No engine regression — PASS

- `python3 -m pytest -q` → **230 passed** (matches expected). NOTE: the very first
  cold run reported 16 failures; this was a stale-`__pycache__` cold-start artifact —
  four consecutive runs after a scoped `arunner/tests` pycache purge all returned
  clean 230. Not a real regression. (Documented for transparency.)
- `git diff HEAD -- arunner/engine/tick.py`: **136 insertions, 0 deletions** —
  purely ADDITIVE (new `_CONTINUATION_REASONS`, `_open_blockers`, `_halt_reason`,
  `_continuation`, `_verdict_str`, `_append_journal`, plus verdict wiring in `tick`).
  The existing dispatch/advance/STOP-read-only/SUMMARY flow is unchanged in substance.
- STOP tick remains read-only: `test_stop_tick_emits_halt_stop_but_writes_nothing`
  asserts byte-identical `harness_status.json` AND `journal.ndjson` after a STOP tick;
  the STOP branch computes `cont` for the return value only (no persist, no journal).
- Spot-check: `pytest -k "stop or summary or readonly"` → **19 passed**.
- MUTATION BITE (load-bearing pin): forced `_halt_reason` to `return "done"` →
  `test_continue_healthy_midrun` FAILED (AssertionError, line 52); restored via
  `shutil.copy2` from pristine snapshot → green. Pin genuinely bites. Working tree
  restored byte-exact (diff still 136 insertions).
- Detector genuinely discriminates: `test_continuation_detector_discriminates`
  re-grades a real `abandon` run against a no-violation expected (must fail) and an
  `honor` run against a violation expected (must fail) — not coverage theater.

## 5. Residual hole host-authored — PASS

- `docs/INTEGRATION_TEST_PLAN.md`: *"**Residual hole, acknowledged:** the blocker
  record is host-authored, so a host could fabricate a *genuine-looking* blocker to
  manufacture a clean yield; the cross-verdict check catches a *mismatched* claim but
  cannot adjudicate whether a recorded blocker was truly necessary."* Disclosure is
  present and explicit, not hidden. Engine's `_open_blockers` docstring confirms
  blockers are host-authored and only READ by the engine.

## 6. Commit hygiene readiness — PASS

- Tracked changes are exactly FR-55 build + the §9 flip: `arunner/engine/tick.py`,
  `tests/integration/checker.py`, `tests/integration/runner.py`,
  `tests/test_integration_scenarios.py`, `tests/test_tick.py`,
  `tests/test_positioning_honesty.py`, `docs/REQUIREMENTS.md` (1-line §9 flip).
- Untracked: the 7 `continuation_*` scenarios + `tests/test_continuation.py` (build
  artifacts, to be added), and `SDLC.md` / `docs/TRACEABILITY.md` (operator's
  SEPARATE docs) which remain UNTRACKED and must NOT be swept into this commit.

## Conclusion

Every charter item holds with quoted evidence. Framing is honest (post-hoc, not
prevention). §9 flip rests on real in-repo tests; floor row stays PENDING; dogfooding
guard intact. No engine regression (230 green, additive diff, STOP read-only proven,
mutation pin bites). Residual hole disclosed. No overclaim, no weakened guard, no
hidden hole.

VERDICT: SHIP
