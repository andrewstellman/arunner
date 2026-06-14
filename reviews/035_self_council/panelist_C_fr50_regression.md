# Panelist C — FR-50 positioning + regression safety (iteration 13b)

Reviewer C, 3-panel honesty gate. Independent/adversarial. Work reviewed UNCOMMITTED (`git diff HEAD` + the untracked new test file).

## Charter item 1 — Unattended → deterministic rungs (FR-50). PASS

Both README and TOOLKIT explicitly steer operators who need reliable unattended runs to the deterministic ticker/cron rungs (2–4) and name them immune to the agent-loop drop.

README in-context section (lines 173–176):
> it is **rung-1 only** and is **not the unattended-reliability path**. If you need reliable *unattended* runs, use the deterministic ticker/cron rungs (2–4), which are immune to the agent-loop drop; the in-context/agent rung is the interactive/convenient mode, backed by the safety tick.

TOOLKIT "What this is" (diff):
> So steer anyone who needs reliable **unattended** runs to the deterministic ticker/cron rungs (2–4) — immune to the Class-C agent-loop drop; the in-session agent rung is the interactive/convenient mode, backed by the FR-26a safety tick, **not** the unattended-reliability path.

Guidance is present and clear in both. PASS.

## Charter item 2 — Agent rung = interactive/convenient + FR-26a safety tick, NOT unattended-reliable. PASS

README explicitly: "the in-context/agent rung is the interactive/convenient mode, backed by the safety tick" and (line 209–210) "The in-session timer (rung 1) is reliable *as a timer* but the resumed turn has a host-side fragility — see the safety tick." Safety-tick section (FR-26a) frames the tick as a no-detection rescue, not a reliability claim for the rung. The README header itself carves out the in-session agent rung as the one place "runs on any agentic system" does NOT extend to. TOOLKIT mirrors with "the in-session agent rung is the interactive/convenient mode … **not** the unattended-reliability path." No place implies the agent rung is unattended-reliable. PASS.

## Charter item 3 — Coherent, not scattered (FR-46 C-7 + FR-26a). PASS

The three places are mutually consistent:
- In-context section (FR-46/C-7, lines 166–176): convenience superset, "**does not fix Class-C**", "rung-1 only", "not the unattended-reliability path".
- Safety-tick section (FR-26a, lines 212+): the external low-frequency tick rescues a dead in-session turn; compaction refuted; cites upstream claude-code#67945.
- Support table + line 209: rung 1 "reliable *as a timer*" but resumed turn is fragile → see safety tick.

No contradiction: every place that mentions the agent rung's reliability denies unattended-reliability and redirects to the floor or the safety tick. One coherent position. PASS.

## Charter item 4 — Regression safety: suite green, no engine change. PASS

- `python3 -m pytest -q` → **209 passed** (202 prior + 7 new). Matches expectation (charter said "7 new doc-consistency tests").
- `git diff HEAD --stat`: only `README.md`, `TOOLKIT.md`, `docs/REQUIREMENTS.md`, `plugins/arunner/skills/arunner/SKILL.md`. The new test file `tests/test_positioning_honesty.py` is UNTRACKED (`git status` `??`), which is why it doesn't appear in `git diff HEAD --stat` — it IS present and IS the 7-test file. (Charter listed `SKILL.md`; actual path is `plugins/arunner/skills/arunner/SKILL.md` — same file.)
- `git diff HEAD --name-only | grep engine` → **NO ENGINE CODE CHANGED**. Zero `arunner/engine/*` or any `.py` engine change. PASS.

## Charter item 5 — New test is sound (non-vacuous). PASS

`tests/test_positioning_honesty.py` parses the real §9 table and asserts FR-50/FR-54 guarantees. I mutation-bit each load-bearing assertion (mutated docs, ran tests, restored):

| Mutation | Result |
|---|---|
| §9 Windows-floor row PENDING→VERIFIED | **2 failed** (bites — floor-pending + no-verified-cites-dogfooding guards) |
| TOOLKIT strip "safety tick" | **1 failed** (bites unattended-steering) |
| README strip "unattended" | **1 failed** (bites unattended-steering) |
| §9 FR-50 row VERIFIED→PENDING | **1 failed** (bites built-rows-are-verified) |
| restore | **7 passed** |

Every guarantee the charter named is enforced: unattended steering (`test_unattended_steers_to_deterministic_rungs` requires "unattended" + "safety tick" in both README and TOOLKIT), cross-agent lead (`test_readme_leads_cross_agent_and_splits_roles`, `test_skill_and_toolkit_lead_cross_agent` — "agentic coding system", worker/orchestrator split, "Claude Code only"), §9 PENDING rows (Windows floor + FR-55 stay PENDING; the dogfooding/always-on honesty rule). Not vacuous. PASS.

## Note (non-blocking)

During my own mutation run, a follow-up `pytest -q` reported 2 failures from stale `.pyc` caching (the in-script restore had already returned 7-passed). Purging `tests/`+`docs/` `__pycache__` and `.pytest_cache` → **209 passed**. Source tree confirmed pristine (no leftover "XXXXX", diff-stat unchanged, Windows-floor row PENDING). This was an artifact of my adversarial mutation loop, not a regression in the work under review.

VERDICT: SHIP
