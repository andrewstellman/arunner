# Arunner — Acceptance Tests (the runbook)

*The acceptance tests mirror the use cases by having the **agent drive arunner the way it is used**, then grading the result objectively. They are run from Claude Code (and, per use case, the ticker), back to back, on each target platform and agent. The deterministic pytest/unittest suite is the necessary-condition floor underneath (see `SDLC.md`); a real regression test is the acceptance tests **and** that suite, together. This doc is the runbook an agent follows after "Read AGENTS.md, then run the acceptance tests." Status: **design — to be council-reviewed, then built.***

## The core idea (reuse, don't reinvent)

Each acceptance test reuses an existing scenario's **canned stub-worker plan** and its **`expected` end-state**, but the **agent drives the run** (rung 1, bootstrapped from `AGENTS.md`) — or launches the **ticker** for the no-agent cases — instead of the test harness's ticker loop. The run is then graded by the **same independent stdlib checker** the necessary-condition suite already uses.

So the only difference between a necessary-condition test and its acceptance test is **who drives the run**: the harness's ticker (necessary-condition) vs. the live agent / a real ticker invocation (acceptance). Grading is identical and objective — the checker reads the run-dir and compares to `expected`; pass = no failures. No "did it look right" judgment.

Stub workers mean **zero API spend**, so the whole set runs back to back.

## The one new piece to build

A thin **checker CLI** so the agent can grade its own live run:

```
python tests/integration/checker.py <run-dir> <expected.json>   # exit 0 = pass, prints failures otherwise
```

`checker.check(run_dir, expected)` already exists and is stdlib-only; this just exposes it as a command. (Worker iteration — small.) Everything else is canned plans (already exist as the integration scenarios) + this runbook + the `AGENTS.md` bootstrap.

## The runbook (per use case)

For each, the agent: (1) prepares the canned plan, (2) drives it at the listed rung, performing any control actions, (3) grades the run-dir with the checker CLI. The full UC↔test↔rung↔run-context matrix is in `docs/TRACEABILITY.md`; the agent-facing steps are:

- **UC-1 (multi-job native):** bootstrap rung-1 on the pool plan; tick to `done`; grade. Pass = all entries `completed`, `done: true`.
- **UC-2 (monitor):** during UC-1, confirm each tick's status table matches `harness_status.json` (read-only).
- **UC-3 (halt):** mid-run, drop `STOP`; confirm the next tick halts read-only (state byte-unchanged); grade `stopped`.
- **UC-4 (resume):** mid-run, abandon the session; re-bootstrap against the run-dir (skip `--init`) or run `ticker.py --once`; confirm resume with no double-dispatch; grade `done`.
- **UC-5 (locked-down floor):** launch `ticker.py` in a terminal (no admin) on a shell-dispatch plan; drive to `done`; grade. **Run-context: Windows + macOS.**
- **UC-6 (scheduled):** install the printed schedule entry firing `--once`; confirm one tick per fire to `done`. **Recorded, real scheduler.**
- **UC-7 (manual tick):** run `--once` by hand repeatedly to `done`; grade.
- **UC-8 (demo):** from a fresh install, drive the bundled demo to `done` both in-agent and via ticker; grade.
- **UC-9 (in-context):** bootstrap on an instruction folder; do in-context tasks + tick the background harness; simulate a drop and rehydrate; grade outputs + background run-dir.
- **UC-10 (conversational build):** describe → preview → run → persist a session in natural language; confirm the previewed plan ran and the saved bundle re-runs faithfully.
- **UC-11 (autonomy integrity):** drive a long stub run; confirm the continuation contract holds; run the checker's 3-class detector over the journal — pass = no `CONTINUE`-state yields.
- **UC-12 (activity patterns):** run a wrap/tail job with `adapter_activity_patterns` over noisy sim output; confirm the ACTIVITY label shows the relevant line, not the noise.

## Running them

`AGENTS.md` gets a "run the acceptance tests" section: read this runbook, run each test back to back, grade each with the checker CLI, and report a pass/fail roll-up by use case. The agent reports which use cases passed, which failed (with the checker's failure lines), and the run-context (OS + agent).

**Run-contexts (a test isn't complete until run in each):**
- **Per-OS:** the platform-sensitive cases (UC-5/6/7/8) on **Windows and macOS** (Linux too) — where file-locking / process-spawn defects the floor can't see will surface.
- **Per-agent:** the in-agent cases (UC-1/2/3/9/10/11) on **each agent claimed as an orchestrator host** — Claude Code today; Cursor and Copilot stay DESIGNED until an acceptance run on them passes and is recorded.

## Status / next

1. **Council-review this design** (does each test truly mirror its use case at the right rung; is agent-drive + checker-grade sound; are the run-contexts honest). This is the drift-check.
2. Build: the **checker CLI**; any **canned plans** not already covered by the integration scenarios; the **`AGENTS.md` bootstrap** section.
3. First real run: from Claude Code on macOS, then Windows — expect genuine failures the first few times (that is the suite working).
