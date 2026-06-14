# Coverage / traceability council — synthesis

*2026-06-14. The gate that decides whether we can claim "every US/UC is mirrored by an acceptance test." Verdict: **NOT YET — design-complete + acceptance layer built + floor green, but coverage is not complete and zero live acceptance runs are recorded.** The docs themselves are honest (they say "TO BUILD"); the error would have been stamping COMPLETE.*

## Where the panelists agreed and disagreed

| | A (completeness) | B (fidelity) | C (honesty) |
|---|---|---|---|
| Verdict | GAPS-FOUND | SHIP (UC-8..12 mirror their UCs) | docs HONEST, claim must be bounded |
| Floor green | yes (283) | yes | yes (283, exit 0) |
| §9 honesty | Windows floor PENDING ✓ | — | no §9 overclaim ✓ |

B is right that the **built UC-8..12 tests genuinely mirror their use cases at the right rung** (verified by execution: the three continuation violations each fire; honor stays silent; UC-8 two rungs vs one expected; UC-10 frozen-canonical pin; UC-12 real wrap subprocess). A and C are right that **coverage is not complete**.

## The honest state

1. **Built + proven:** the acceptance *layer* — plans (uc1–uc12), the checker-from-disk CLI, the runbook, the `AGENTS.md` bootstrap, and **deterministic gradeable-leg tests for UC-8..12** (`test_acceptance_uc89101112.py`, in the green 283). The mechanism is proven end-to-end (the 041/042 in-agent demos).
2. **UC-1..5 — PARTIAL:** plans + `expected` exist and `--check` clean, but there's **no driving test** that runs each to its expected state (only UC-8..12 got those). Their gradeable mechanics are proven against synthetic fixtures, not against the UC plans driven to `done`.
3. **UC-6 / UC-7 — folded into `uc5_floor`, no distinct leg.** Their distinguishing semantics (UC-6 one-tick-per-scheduler-*fire*; UC-7 repeated manual `--once`) aren't exercised. The real cron / manual runs are inherently **operator-recorded**, but the deterministic part (one-tick-per-fire idempotency) can be a gradeable leg.
4. **Zero live acceptance RUNS recorded** on any platform or agent — only the worker's ad-hoc demos. Even the UC-8..12 tests drive via the runner, not a live agent. The live agent runs (per the runbook, per OS/agent) are the **operator's action** — which is exactly the "Claude Code runs the acceptance tests" goal.
5. **US-7/9/10** rest on the floor (`test_positioning_honesty`, §9) rather than an agent-run acceptance leg.

## What's required to claim coverage

- **Buildable now (worker):** driving gradeable-leg tests for UC-1..5 (drive each plan → expected, like UC-8..12); a deterministic UC-6/UC-7 leg (one-tick-per-fire + repeat-to-done) + an honest runbook note that the real-scheduler/manual leg is operator-recorded.
- **Operator action (not buildable by the worker):** the first **recorded live acceptance runs** — open Claude Code, read `AGENTS.md`, run the acceptance tests — on macOS, then Windows; then on Cursor/Copilot for the per-agent cases. These are what flip the §9 host/floor rows (NFR-12) and what the coverage claim ultimately rests on.

## Honest claim wording (until the runs exist)

> Coverage **design-complete**; acceptance layer **built** with deterministic gradeable-leg tests for UC-8..12 and the necessary-condition floor green on dev (283). UC-1..5 driving tests + UC-6/7 legs outstanding; **no live acceptance run recorded on any platform/agent yet**; Windows floor row PENDING (NFR-12); Cursor/Copilot DESIGNED.

Do not say "coverage complete" or "verified" until the live runs are recorded.
