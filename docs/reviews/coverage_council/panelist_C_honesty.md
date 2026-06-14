# Panelist C — Run-Contexts & Honesty of the Coverage Claim

**Charter:** RUN-CONTEXTS & HONESTY of the coverage claim. Adversarial.
**Date:** 2026-06-14
**Verdict: OVERCLAIM-FOUND (in the charter's framing) / docs themselves are HONEST**

There are two things to grade and they diverge. The *documents* (`TRACEABILITY.md`, `ACCEPTANCE_TESTS.md`) are honest and do not overclaim. But the charter's stated premise — "the acceptance tests are BUILT and pass on the dev platform … confirm the docs say so" — is **not** what the docs say, and is **not** true. The acceptance tests are **not built and have not been run anywhere**. So if any coverage claim asserts "every US/UC is mirrored by an acceptance test" as a *present-tense, built-and-passing* fact, that is an **OVERCLAIM**. The docs avoid that overclaim; a council that "concludes coverage" right now on the charter's premise would commit it.

---

## Finding 1 — Run-contexts: honest and complete; but the build state is pre-acceptance-run, not "passing on dev"

The run-context bookkeeping is **honest and complete**. Every UC row in `TRACEABILITY.md` (line 15+) carries a Run-contexts column naming per-OS (Windows/macOS/Linux) for the platform-sensitive cases (UC-5/6/7/8/12) and per-agent (Claude Code / Cursor / Copilot) for the in-agent orchestrator cases (UC-1/2/3/9/10/11). `ACCEPTANCE_TESTS.md` lines 47–50 repeat the same split and add the load-bearing guard: *"A pass from Claude Code on macOS does not clear the §9 Windows floor row; that row flips only on a recorded Windows run (NFR-12)."* Cursor/Copilot are correctly held at **DESIGNED until a recorded acceptance run** (TRACEABILITY line 43; ACCEPTANCE_TESTS line 49). No platform/agent is claimed covered without a named, outstanding run-context. **No dishonesty here.**

**But the charter's premise is wrong about the build state.** The charter says "the acceptance tests are BUILT and pass on the dev platform (Python 3.10/3.14, macOS/Linux)." The docs say the opposite:

- `TRACEABILITY.md` line 3: *"the agent-run acceptance layer is the **current build**"*; line 11: *"most acceptance tests are **TO BUILD**"*; **every UC row's Status is `TO BUILD`** except UC-8 (`PARTIAL` — 13a install-smoke exists, in-agent demo TO BUILD).
- `ACCEPTANCE_TESTS.md` line 3 status banner: *"**design (council-revised 2026-06-14) — building.**"* Its "Status / next (the build)" section (lines 52–58) lists the acceptance layer as **forward work**: extend the checker into a CLI, write subagent stub plans, *"Demonstrate one in-agent acceptance test end-to-end,"* add the `AGENTS.md` bootstrap, *"then **first real runs** from Claude Code on macOS, then Windows."*

So the honest state is **weaker** than the charter assumed: the acceptance tests are **designed/being built, not built; and not yet run on any platform — not even the dev box.** The only thing green on dev is the necessary-condition floor (283 passed, see Finding 4), which is explicitly *not* the acceptance test. The charter's "BUILT and pass on the dev platform" claim should be downgraded to "**designed, mid-build; zero acceptance runs recorded**" before any coverage conclusion rests on it.

## Finding 2 — §9 / NFR-12: clean. No §9 row is implied VERIFIED by building (or designing) the acceptance tests.

The Windows/cadence floor row stays **PENDING**: REQUIREMENTS §9 (line 400) reads *"**PENDING** — needs a recorded cross-platform matrix run (NFR-12): operator-run Windows V-7/V-8 … dogfooding / always-on runs do not satisfy this row."* NFR-12 (line 371) and SDLC §9 (lines 55–60) both enforce "a row flips to VERIFIED only on a real, linked artifact (a named test + scenario, or a dated run-dir)" and "no row flips on dogfooding." Building (or merely designing) the acceptance tests is neither a recorded run nor a dated run-dir, so it cannot flip the floor row — and nothing in `TRACEABILITY.md`/`ACCEPTANCE_TESTS.md` claims it does. ACCEPTANCE_TESTS line 50 explicitly re-states that a macOS Claude-Code pass does not clear the Windows floor. **Building ≠ a recorded run is correctly observed. The Windows floor row must stay PENDING — confirmed, it does.** No overclaim.

## Finding 3 — The coverage CLAIM itself: TRUE only in a *carefully bounded* form, and NOT yet true in the present-tense "built" form

"Every US/UC is mirrored by an acceptance test" is, today, true only as a **plan/design** statement: every UC has a *designed* acceptance test with a runbook entry (ACCEPTANCE_TESTS lines 26–37) and a matrix row with named floor + run-contexts. It is **NOT** true as a present-tense "built and passing on the dev platform" claim — because nothing is built-and-passing yet (Finding 1). The traceability gate is the discipline that prevents the overclaim: SDLC line 51 and TRACEABILITY line 47 both gate the coverage claim on a council concluding "**every US/UC is mirrored by an acceptance test**, with each test's required run-contexts named *and the necessary-condition floor green*." The matrix demonstrably maps every US/UC (TRACEABILITY line 30 collapses all 12 US onto the UCs) and names every run-context. So the **mapping** is complete; the **execution** is zero.

**Therefore the only honest coverage claim a council can sign today is the design-level one — "every US/UC is mirrored by a *designed* acceptance test" — not "verified everywhere" and not even "built and passing on dev."** Any wording that drops the design-level qualifier and reads as built/passing overclaims.

## Finding 4 — Necessary-condition floor (precondition): GREEN ✅

`cd /Users/andrewstellman/Documents/wakecycle && python3 -m pytest tests/ -q` → **283 passed, 31 subtests passed in 22.86s, exit 0** (run on Python 3.10.12). The floor precondition holds. (Note: the charter's "Python 3.10/3.14" is the CI matrix; the dev box this ran on is 3.10.12. The floor being green is necessary, never sufficient — SDLC lines 41–45 — and it is *not* the acceptance test.)

---

## The precise honest wording the coverage claim SHOULD use

Do **not** use: "every US/UC is mirrored by an acceptance test" (bare — reads as built/passing/verified).

Use instead (bounded to today's actual state):

> **Coverage (design-complete; acceptance layer mid-build, zero acceptance runs recorded).** Every user story and use case (US-1…12, UC-1…12) is mirrored by a **designed** acceptance test with a runbook entry, a named necessary-condition floor, and explicitly named required run-contexts (per-OS: Windows/macOS/Linux for UC-4/5/6/7/8/12; per-agent: Claude Code / Cursor / Copilot for UC-1/2/3/9/10/11). The necessary-condition floor is green on the dev platform (283 pytest tests, exit 0; cross-platform in CI). The agent-run acceptance layer is **built? no — being built**: the checker CLI, the subagent stub plans, the end-to-end demonstration, and the `AGENTS.md` bootstrap are the current work. **No acceptance test has yet been run on any platform or agent** — the first recorded runs (Claude Code on macOS, then Windows) are pending. Per NFR-12, the §9 Windows/cadence floor row stays **PENDING** and flips only on a recorded Windows matrix run; a designed-or-built test, and a macOS Claude-Code pass, do not clear it. Cursor and Copilot orchestrator hosts stay **DESIGNED** until a recorded acceptance run on each passes.

If the council's job is to certify the *gate* in SDLC line 51, the honest conclusion today is: **mapping complete + run-contexts named + floor green = the design-traceability gate is satisfiable, but the coverage claim cannot yet read as "built and passing" — let alone "verified everywhere" — because the acceptance layer is mid-build with no recorded runs.**

**Verdict: OVERCLAIM-FOUND** against the charter's premise (the acceptance tests are *not* built-and-passing-on-dev; they are designed and mid-build with zero recorded runs). The documents themselves are **HONEST** and contain the qualifiers that prevent the overclaim — provided the coverage claim is stated in the bounded form above and not collapsed to the bare sentence.
