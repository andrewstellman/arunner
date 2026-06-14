# Instruction 035 self-council synthesis — Iteration 13b: positioning + §9 reconciliation (FR-50/FR-54/NFR-12)

*Mandatory 3-panel honesty gate. Three fresh-context, role-locked, adversarial reviewers, each verifying on disk (running the suite, grepping the docs, mutation-biting the guard). Date: 2026-06-14.*

| Panelist | Charter | Verdict |
|----------|---------|---------|
| `panelist_A_s9_honesty.md` | §9 evidence-ledger honesty | **SHIP** |
| `panelist_B_cross_agent.md` | cross-agent messaging accuracy (FR-54) | **SHIP** |
| `panelist_C_fr50_regression.md` | FR-50 positioning + regression safety | **SHIP** |

## Outcome: unanimous SHIP (round 1)

### Panelist A — §9 honesty (SHIP)
Verified all 11 flipped VERIFIED rows cite real in-repo tests — confirmed all 18 distinct cited test files exist in `tests/` and the cited integration scenarios exist under `tests/integration/scenarios/`; full suite green (209). The cadence/Windows-floor row and the FR-55 row both **stay PENDING** with honest "dogfooding/always-on does not satisfy this" disclaimers; **no VERIFIED row cites dogfooding/always-on** (grep-confirmed). The mechanical guard `tests/test_positioning_honesty.py` passes 7/7 and **bites** (flipping the floor row to VERIFIED produced failures; restored via `shutil.copy2`). No stray "all PENDING" note contradicts the flipped ledger.

### Panelist B — cross-agent accuracy (SHIP)
README, TOOLKIT, and SKILL all **lead** with orchestrating *any* agentic system (Claude Code, Copilot, Codex, Cursor, Antigravity), "not one vendor" — identity, not footnote. The **honesty split** is present and correct in all three: engine + terminal/cron floor host-agnostic ("run identically everywhere"), the in-session agent rung is where hosts differ (Class-C scoped as a Claude Code quirk); "runs on any agentic system" attaches only to engine + floor. Universality grounded **by construction** (stdlib Python + JSON-lines worker contract + subagent/host-CLI dispatch, no vendor SDK). The support table separates the **worker** role (Copilot/Codex VERIFIED, macOS rung 3, V-14) from the **orchestrator** role (FR-52 builder DESIGNED any host / VERIFIED Claude Code only) without conflation. Adversarial grep found **zero** overclaims.

### Panelist C — FR-50 positioning + regression (SHIP)
README + TOOLKIT both steer reliable **unattended** runs to the deterministic ticker/cron rungs (2–4, immune to the Class-C drop) and frame the in-session agent rung as interactive/convenient backed by the FR-26a safety tick, never as unattended-reliable. The in-context (C-7), safety-tick (FR-26a), and support-table sections are mutually consistent. Suite green at **209** (202 + 7 new); the diff touches **only** the four docs/markdown files + the new test — **zero engine-code change**. The new test is genuinely load-bearing (each guarantee mutation-bitten, each bites, restore returns green).

## Net
13b is a pure docs/positioning + §9 reconciliation, no engine change. The three orientation docs now lead with the cross-agent identity (FR-54) with the load-bearing engine/floor-vs-per-host-agent-rung honesty split; the support table separates VERIFIED workers from the DESIGNED/Claude-Code-only orchestrator role; FR-50 steers unattended runs to the deterministic floor. §9 flips 11 build/positioning rows to VERIFIED on linked in-repo test evidence and **keeps the cadence/Windows floor row and FR-55 PENDING**, with `test_positioning_honesty.py` enforcing the gate mechanically. Suite 202 → 209 (the 202 engine/feature tests unchanged + 7 doc-consistency tests). FR-55 itself remains unbuilt (out of scope).

**Non-blocking notes:** (A) the dated `runner/1.5.9/outputs/0NN-*.md` pointers live in the external runner dev-log tree, not this repo — acceptable because every flipped row also carries a real in-repo test (the AND/OR rule is satisfied by the test). (C) the new test file is untracked, so it is absent from `git diff HEAD --stat` until committed (expected).
