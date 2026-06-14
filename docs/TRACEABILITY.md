# Arunner — Requirements → Acceptance Test Traceability

*The coverage artifact: every user story and use case mapped to the acceptance scenario(s) that exercise it, with each marked **acceptance-testable** (validated by the deterministic suite) or **measurement-only** (requires a recorded run — agent-loop or scheduler/platform). The traceability gate is a council review concluding every US/UC is covered or explicitly measurement-only. Companion to `docs/INTEGRATION_TEST_PLAN.md` and `SDLC.md`.*

## How to read this

- **Acceptance-testable** = the behavior is reachable by the deterministic, ticker-driven suite with the independent stdlib checker; it can be a green gate in CI.
- **Measurement-only** = the behavior requires a real agent loop, a real OS scheduler, or a specific platform; it is validated by a recorded run (NFR-12), never by the deterministic suite or by dogfooding. These are the §9 PENDING/DESIGNED rows.
- Many use cases are **mixed**: the engine/filesystem behavior is acceptance-testable while the real-rung integration is measurement-only. Both halves are listed.

## Use case coverage

| UC | What it covers | Acceptance scenario(s) / tests | Classification |
|----|----------------|-------------------------------|----------------|
| UC-1 | Run a multi-job plan natively (cadence 1 + dispatch 1) | `autonomous_loop`, `pool_staggered` | **Acceptance** (engine behavior via ticker) + measurement-only for the *real* rung-1 agent loop |
| UC-2 | Monitor a run in progress (status table) | `test_cli` (status read-only), `test_cli_journey` (status mid-run) | **Acceptance** |
| UC-3 | Halt a run early (STOP) | `stop_readonly` + `test_control_files` | **Acceptance** |
| UC-4 | Resume after a crash or silent loop-drop (FR-13) | `continuation_crash_then_resume` (landed, instr 036) exercises stop-mid-run → FR-13 resume → `done`. `resume_continues` separately covers PAUSE/RESUME. | **Acceptance** ✓ (closed by 036) |
| UC-5 | Run on a locked-down host (cadence 3 + dispatch 2 — the floor) | engine + shell dispatch: `wrap_adapter_completes`, `tail_adapter_completes` (run on Windows CI) | **Mixed**: engine/shell-dispatch **Acceptance** (incl. Windows CI); the real no-admin scheduler floor is **measurement-only** (Windows V-7/V-8) |
| UC-6 | Scheduled run via cron / host automations (cadence 2) | tick behavior under the ticker | **Mixed**: tick behavior **Acceptance**; real cron firing is **measurement-only** (macOS V-9 recorded; Windows pending) |
| UC-7 | Manual-tick floor (cadence 4) | every scenario (the suite *is* `ticker.py --once` driven by hand) | **Acceptance** (the manual tick is the tested path) |
| UC-8 | Install and run the demo (adopter first contact) | 13a packaging gate: throwaway-venv install + demo-to-`done` (`test_packaging`) | **Acceptance** (the demo runs deterministically; ship the demo in the wheel — see follow-up) |
| UC-9 | Run as an in-context worker (harness + in-context) | `test_incontext` (selection logic, STOP-halts-mid-queue, monitoring-pause render) | **Mixed**: deterministic selection/render **Acceptance**; the real in-context agent loop is **measurement-only** (rung-1 only, C-7) |
| UC-10 | Build and run a session conversationally (headline UX) | `test_preview` (per-job dispatch render), `test_cli_journey` (describe→preview→run→persist) | **Mixed**: deterministic preview + journey **Acceptance**; the real host-agent NL understanding is **measurement-only** (Claude-Code-verified; "any host" DESIGNED) |
| UC-11 | Drive an unattended run through stop-pressure (autonomy integrity) | `continuation_{honor,abandon,crash_then_resume,false_yield,false_halt_claim,scheduled_gap,blocked_then_clear}` (landed, instr 036) + the 3-class detector | **Acceptance** ✓ (stub-host, closed by 036); the real-agent version is **measurement-only** (live audit) |
| UC-12 | Surface meaningful status from a noisy wrapped tool (FR-56) | new wrap/tail scenarios driven by the cross-platform simulator (noisy-log mode) — **build target v0.2** | **Acceptance** once FR-56 + the simulator land |

## User story coverage (clustered with the use cases)

| US | Covered by | Classification |
|----|-----------|----------------|
| US-1 (overnight multi-repo from one prompt) | UC-1 scenarios | Acceptance (engine) + measurement (real agent loop) |
| US-2 (watch a status table each tick) | UC-2 | Acceptance |
| US-3 (halt by dropping STOP) | UC-3 | Acceptance |
| US-4 (resume by one command, no double-run) | UC-4 (`crash_then_resume`) | Acceptance once 036 lands |
| US-5 (locked-down Windows, one script drives the plan) | UC-5 | Mixed (Acceptance engine + measurement Windows floor) |
| US-6 (Codex/Copilot/Cursor workers via own CLI) | adapter/dispatch scenarios + V-14 worker evidence | Mixed (Acceptance shell-dispatch + measurement per-host) |
| US-7 (orchestration on a small/cheap model) | NFR-4 (Haiku run, recorded) | Measurement-only |
| US-8 (`pip install` + one prompt → demo in ~20 min) | UC-8 | Acceptance (install + demo smoke) |
| US-9 (complete disk record, auditable) | every scenario (independent disk-assertion checker) | Acceptance |
| US-10 (honest VERIFIED-vs-DESIGNED README) | `test_positioning_honesty` + §9 ledger | Acceptance (the honesty guard) |
| US-11 (autonomous = unattended; no judgment-stops) | UC-11 (`continuation_contract`) | Acceptance once 036 lands + measurement (dogfood audit) |
| US-12 (declare which log lines are status) | UC-12 (FR-56) | Acceptance once FR-56 lands (v0.2) |

## Open coverage gaps (to close)

1. ~~UC-4 / US-4 crash-resume~~ — **CLOSED** by `continuation_crash_then_resume` (instr 036).
2. ~~UC-11 / US-11 autonomy integrity~~ — **CLOSED** by the `continuation_*` scenarios + 3-class detector (instr 036).
3. **UC-12 / US-12 activity patterns** — pending FR-56 (build target v0.2) + the cross-platform simulator (noisy-log mode).
4. **Measurement-only rows still un-recorded** — Windows floor V-7/V-8, in-context agent-loop, and the real host-agent orchestrator beyond Claude Code. These are operator-run recorded matrix runs (NFR-12); they are *not* gaps the deterministic suite can close.

## The traceability gate

Coverage is *claimed* only after a council review concludes that every US/UC above is either covered by a green acceptance scenario or explicitly classified measurement-only with a named recorded-run requirement. That review — not this table alone — is the traceability gate; this table is its input and its record.
