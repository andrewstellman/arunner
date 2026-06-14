# Panelist A — §9 Evidence-Ledger Honesty (Iteration 13b, uncommitted)

Reviewer A, 3-panel honesty gate. Charter: §9 evidence-ledger honesty in
`docs/REQUIREMENTS.md` (`## 9. Validation evidence map`). Work is UNCOMMITTED;
reviewed via `git diff HEAD` + direct file reads. Repo: `/Users/andrewstellman/Documents/wakecycle` (git `main`).

## 1. Every flipped VERIFIED row cites a real, existing in-repo test — PASS

The 11 flipped rows and their cited in-repo tests were each checked with `test -f tests/<name>.py`. ALL 18 distinct cited test files exist:

```
OK test_version_single_source  OK test_control_files  OK test_cadence_pool
OK test_poll_now  OK test_cancel  OK test_wrap_adapter  OK test_tail_adapter
OK test_check_plan  OK test_jobs_shorthand  OK test_toolkit_examples
OK test_summary  OK test_incontext  OK test_integration_scenarios
OK test_checker_independence  OK test_preview  OK test_cli  OK test_cli_journey
OK test_positioning_honesty
```

Row-by-row the cited test(s) map cleanly:
- FR-34 → test_version_single_source.py
- FR-35..39 → test_control_files / test_cadence_pool / test_poll_now / test_cancel + scenarios pause_blocks_dispatch / resume_continues / poll_now_collapses_cadence / cancel_shared_state (all 4 dirs exist under tests/integration/scenarios/)
- FR-40/41 → test_wrap_adapter / test_tail_adapter + scenarios wrap_adapter_completes / tail_adapter_completes / wrap_output_keyword_no_misreap (all exist)
- FR-42..44 → test_check_plan / test_jobs_shorthand / test_toolkit_examples
- FR-45 → test_summary
- FR-46..49 → test_incontext
- FR-51 → test_integration_scenarios / test_checker_independence (11 scenarios present)
- FR-50, FR-54 → test_positioning_honesty
- FR-52 → test_preview / test_cli_journey
- FR-53 → test_cli / test_cli_journey

Cited integration scenarios all exist (`tests/integration/scenarios/`: pause_blocks_dispatch, resume_continues, poll_now_collapses_cadence, cancel_shared_state, wrap_adapter_completes, tail_adapter_completes, wrap_output_keyword_no_misreap — 11 scenario dirs total).

Full suite is GREEN: `python3 -m pytest -q` → **209 passed in 13.52s**. The cited tests don't just exist — they pass.

NOTE on the dated iteration pointers (`runner/1.5.9/outputs/0NN-*.md`): these directories do NOT exist inside this repo (`find . -name '018-iteration-1*'` → empty; no `runner/` dir). They point to an external development-log tree (the QPB `runner/1.5.9/` repo). The charter wording is "an in-repo test name (or names) **and/or** a dated iteration pointer" — every flipped row carries at least one real, passing in-repo test, which satisfies the AND/OR. The external pointers are non-blocking provenance, not the load-bearing evidence. Flagged as an observation, not a FIX.

## 2. Floor row (cadence-2/3/4 + shell dispatch + Windows floor) STAYS PENDING — PASS

Status is `**PENDING**`. Reason names the missing recorded evidence exactly: "operator-run Windows V-7/V-8 (Task Scheduler + foreground ticker) and the V-10 safety-tick" and explicitly states "**dogfooding / always-on runs do not satisfy this row** (they measure survival, they do not validate a floor matrix)." Correct.

## 3. FR-55 row STAYS PENDING — PASS

`| Continuation contract ... (FR-55, UC-11, US-11) | PENDING — v0.1.0 build; ...` Not flipped. The footer note still reads "(FR-55 PENDING)" and the §6.x intro note (line 320) still says "build status PENDING (§9)" — which the charter explicitly permits for FR-55.

## 4. No VERIFIED row cites dogfooding/always-on — PASS

`awk` from the §9 header + grep `-iE 'dogfood|always-on'` returns exactly 2 lines: the floor row (PENDING, disclaiming dogfooding) and the FR-55 row (PENDING, "dogfood audit"). Neither is VERIFIED. No VERIFIED row leans on dogfooding/always-on.

## 5. Mechanical guard exists and BITES — PASS

`python3 -m pytest tests/test_positioning_honesty.py -q` → **7 passed**.

Independent bite test:
- Snapshot `docs/REQUIREMENTS.md` → `/tmp/REQUIREMENTS_snapshot_035.md` via `shutil.copy2`.
- Flipped floor row `**PENDING**` → `**VERIFIED**` in working file.
- Re-ran guard → **2 failed, 5 passed**: `test_floor_windows_row_stays_pending` (VERIFIED** found) AND `test_no_verified_row_cites_dogfooding_or_alwayson` (the now-VERIFIED floor row cites dogfooding). The guard bites from two independent angles.
- Restored via `shutil.copy2` from snapshot (NOT git checkout). Re-ran guard → **7 passed**. `git diff --stat docs/REQUIREMENTS.md` → 15 insertions / 15 deletions, identical to the original 13b diff. Restoration confirmed; working-tree edits intact.

The guard (test_positioning_honesty.py) parses the §9 table and asserts: floor + FR-55 rows stay PENDING (`assertNotIn("VERIFIED**")`), no `**VERIFIED**` row contains "dogfood"/"always-on", and the 11 built rows ARE VERIFIED. It is the test the FR-50/FR-54 rows cite, and it is mechanical.

## 6. No stray contradicting all-PENDING note — PASS

`grep -niE 'all PENDING|build status PENDING|status PENDING|PENDING build'` → only line 320, the FR-55 §6.x note ("build status PENDING (§9)"), which is correct and charter-permitted. The §5 v0.1.0-UX intro (line 257) was updated from "all PENDING" to "tracked per-row in §9 (... most are VERIFIED; the cadence/Windows floor matrix and FR-55 remain PENDING)"; the interactive-UX intro (line 303) updated to "(FR-52/FR-53 now VERIFIED)"; the footer updated to "build status per-row in §9 — most VERIFIED ...; FR-55 PENDING". No surviving contradiction. README support table corroborates the macOS-VERIFIED / Claude-Code-only / worker-vs-orchestrator claims the flipped rows lean on.

## Conclusion

All 11 flips rest on real, existing, passing in-repo tests. The floor row and FR-55 stay PENDING with honest "dogfooding does not satisfy" disclaimers. No VERIFIED row cites dogfooding/always-on. The mechanical guard exists, is cited by the rows it protects, and demonstrably bites then cleanly restores. Intro/footer notes reconciled.

VERDICT: SHIP
