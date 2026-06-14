# Panelist B — Cross-agent messaging accuracy (FR-54 / NFR-12)

Reviewer B, 3-panel honesty gate. Adversarial, independent of the implementer.
Scope: iteration 13b lead-framing rewrite of README.md, SKILL.md, TOOLKIT.md +
the README "Host support" table. Work is uncommitted; reviewed via `git diff
HEAD` and the files on disk.

## 1. All three docs LEAD with cross-agent universality — PASS

Each opens, in its first lines, by naming the product as orchestrating *any*
agentic system, multiple vendors enumerated, "not one vendor" stated explicitly.

- **README.md:1-6** (the bold lead, line 1 of the file):
  > "**A batch orchestrator for _any_ agentic coding system — Claude Code, GitHub
  > Copilot, Codex, Cursor, Antigravity, … — not one vendor.**"
- **TOOLKIT.md:27-28** (first line of "What this is"):
  > "A batch orchestrator for **any** agentic coding system — Claude Code, Copilot,
  > Codex, Cursor, Antigravity — not one vendor."
- **SKILL.md:16-17** (second paragraph of the body, first substantive framing):
  > "**You may be any agentic coding system** — Claude Code, Copilot, Codex,
  > Cursor, Antigravity — and arunner works the same regardless…"

It is the identity, not a footnote, in all three. PASS.

## 2. The engine/floor-vs-agent-rung honesty split is present and correct — PASS

The split is load-bearing and stated in all three, scoping "runs everywhere" to
the engine + floor and isolating host difference to the in-session agent rung.

- **README.md:19-24:**
  > "**The honesty split that keeps that claim true:** the deterministic engine
  > and the terminal/cron floor are genuinely host-agnostic and run identically
  > everywhere; the one place hosts differ is the *in-session agent rung* (each
  > host has its own scheduling quirks — Class-C is a Claude Code one). So 'runs
  > on any agentic system' describes the engine + floor — never an unvalidated
  > per-host claim about the agent rung."
- **TOOLKIT.md:40-45:** same split; "the engine and the terminal/cron floor are
  host-agnostic and run identically everywhere; the in-session agent rung is
  where hosts differ," steering unattended runs to rungs 2–4, "**not** the
  unattended-reliability path" for the agent rung.
- **SKILL.md:18-25:** "treat the engine + floor as universal; treat your own
  agent-rung reliability as host-specific … Unattended reliability lives in the
  deterministic floor, not this rung."

Class-C is correctly framed as a Claude-Code quirk, not a universal property, and
the docs explicitly state other hosts carry their own quirks. The blanket claim
is correctly attached only to the engine + floor. PASS.

## 3. "By construction" is real (grounded, not asserted) — PASS

The universality is grounded in three concrete structural facts, not a bare
slogan, in all three docs.

- **README.md:14-19:** "vendor-neutral *by construction*: the orchestration
  engine is stdlib-only Python … the worker contract is vendor-neutral (*a job is
  anything that appends JSON lines to a file*), and work is dispatched either as
  in-session subagents or as detached host-CLI processes (FR-14/15) — no vendor
  SDK anywhere."
- **TOOLKIT.md:35-39:** same three pillars (stdlib-only Python + JSON-lines
  worker contract + subagent/host-CLI dispatch, "no vendor SDK").
- **SKILL.md:17-19:** "the engine is stdlib-only Python and the worker contract
  is vendor-neutral."

The "stdlib-only Python," "JSON-lines worker contract," and "no vendor SDK"
claims are the right load-bearing grounds. PASS.

## 4. Support table separates the two host ROLES honestly — PASS

Both roles appear, labeled, with correct verification status.

- **Worker role — README.md:205:** "| **Copilot + Codex** CLIs — host as
  **worker** (macOS, rung 3) | shell | **VERIFIED** | … (VALIDATION V-14)."
  Correctly VERIFIED, macOS, rung 3, V-14.
- **Orchestrator role — README.md:206:** "| Interactive builder — host as
  **orchestrator** (FR-52) | subagent/shell | **DESIGNED** (VERIFIED: Claude Code
  only) | The builder is host-agent-driven and embeds no model; designed for any
  capable host, but only Claude Code has driven it end-to-end. V-14 verified
  Copilot/Codex as detached *workers*, not as builder-driving orchestrators."
- Prose preamble **README.md:186-193** independently states the two roles "are
  independent: V-14 verified Copilot and Codex as *workers*, **not** as
  builder-driving orchestrators," and the builder is "*designed* for any capable
  host but VERIFIED only on Claude Code."

The "any host" builder claim is explicitly DESIGNED / Claude-Code-verified-only,
the two roles are not conflated, and the bold "**not**" negation is an honest
disclaimer, not an overclaim. PASS.

## 5. No overclaim anywhere — PASS

Adversarial grep over all three docs:

- `verified (on)? (all|any|every|each) host`, `works (on)? (all|any|every) host`,
  `verified everywhere`, `proven (on)? (all|any|every)` → **no hits.**
- `works everywhere`, `runs on (all|every|any) host`, `reliable on/everywhere` →
  **no hits.**
- `builder.*verified` / `orchestrator.*verified` → only the two honest, scoped
  uses at README.md:190 and :206 (both "VERIFIED Claude Code only" / "verified as
  workers, **not** orchestrators").
- The three `identically everywhere` / `every host` hits (README:21, TOOLKIT:41,
  SKILL:19) are each scoped to the *engine + floor*, never to the agent rung or
  the builder — the honest claim, not the dishonest one.

REQUIREMENTS.md §9 corroboration: the FR-54 row (line 380) is marked VERIFIED with
the same split ("separates VERIFIED **workers** … from the **orchestrator** role
… DESIGNED any host, VERIFIED Claude Code only"), and FR-52's row keeps the "any
host" orchestrator claim as "DESIGNED / VERIFIED Claude-Code-only." No marketing
claim outruns its §9 status.

No unvalidated per-host agent-rung claim, no multi-host builder verification, no
blanket reliability claim found. PASS.

## Conclusion

All five charter items pass with quoted evidence. The three docs lead with
cross-agent universality; the engine/floor-vs-agent-rung honesty split is present,
correct, and load-bearing; "by construction" is grounded in stdlib-only Python +
the vendor-neutral worker contract + subagent/host-CLI dispatch; the support
table separates the VERIFIED worker role from the DESIGNED/Claude-Code-only
orchestrator role; and no overclaim survives an adversarial grep.

VERDICT: SHIP
