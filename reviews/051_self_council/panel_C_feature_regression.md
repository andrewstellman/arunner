# Panel C — feature correctness + regression

## Round 1 — VERDICT: FIX-REQUIRED
- **BLOCKING — HUNG? false-positives on every freshly-claimed entry.** `run_health` computed HUNG? from heartbeat-mtime freshness only, never consulting `claimed_at`: a `claimed` entry whose first heartbeat hasn't landed → `hb_mtime is None` → not fresh → **HUNG?** immediately, regardless of how recently it was claimed. The charter and the engine's launch-fail logic (`tick.py _advance`: `(now - claimed_at) > grace_secs`) require "past launch grace". The existing test passed only because the fixture defaulted `claimed_at=1.0` (ancient); no recent-claim test existed.
- **OK — kill wires the real verbs.** STOP (empty body, existence-gate) and CANCEL (run id in body, `_read_control_value`/`_parse_run_id`); both confirm-gated; no silent no-op.
- **OK — clipboard stdlib-only, cross-platform, never raises.** pbcopy/clip/wl-copy/xclip/xsel via `shutil.which` + subprocess; OSError/non-zero/missing → `(False, msg)`; handles None text.
- **OK — no engine dependency / no engine behavior change.** pyproject adds no runtime dep (`[tui]` = textual only). tick.py diff = pure `_reconcile_state` + `_format_table` rendering; reap/dispatch/doneness untouched.
- **OK-with-note** ordering DONE→DEAD→HUNG?→STALE→RUNNING correct; cadence-absent → RUNNING (no false STALE); DONE wins over ancient tick.
- Suite 375, 3× OK (one earlier flake on the pre-existing shared-TMPDIR `test_never_writes` pin — see Panel B).

## Round 2 — VERDICT: SHIP
- HUNG? fix RESOLVED: flags HUNG? only when `claimed_at` numeric AND `(now - claimed_at) > grace_secs`, after a whole-tail terminal skip and a fresh-heartbeat skip — mirrors the engine horizon (tick.py:1425) exactly. A freshly-claimed no-heartbeat entry within grace → RUNNING.
- New tests cover both directions: `test_recent_claim_not_hung` (RUNNING) + `test_claimed_past_grace_no_heartbeat_is_hung` (HUNG?). Priority order intact; degrades on missing fields.
- Re-confirmed: real kill verbs, clipboard stdlib/no-dep/never-raises, no engine behavior change.
- Suite **379**, OK.
