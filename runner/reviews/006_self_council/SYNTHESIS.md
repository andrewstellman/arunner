# Self-Council synthesis — instr 006 (FR-74 continue-past-stall + FR-73 OUT-AGE)

**Verdict: UNANIMOUS SHIP** (round 2). Three panels, one round-1 FIX (Panel B),
two ratified scope/tradeoff decisions (Panels A, C).

## Panels
- **A — state-machine / correctness:** SHIP. The `stalled → abandoned` reclaim is
  correct and idempotent (reuses the CANCEL synthesis path), the output-fresh guard
  holds (no false-abandon of a live worker), `stalled ↔ running` reversibility is
  intact below the reclaim threshold, and the reclaimed-comeback race reconciles to a
  single stable terminal. Ratified tradeoff: the output-freshness window =
  `stall_threshold_minutes` (45m), calibrated against gen-007.
- **B — regression-safety:** SHIP after **B-F1**. `HALT:stalled` still reachable,
  shell parity, FR-72 launch path unchanged, CANCEL intact, OUT-AGE display-only,
  stdlib-only + bounded. **B-F1 (fixed):** `_format_table` ran the OUT-AGE bounded
  scan for *every* run; now gated to in-flight runs only, so per-render cost is
  ~`pool_size`, not O(all runs) — keeping "never a full recursive walk per render"
  true at batch scale.
- **C — tests / honesty:** SHIP. Both load-bearing pins present and mutation-bitten;
  no FR/US/UC number reuse; §9 honest; the Step-0 calibration finding recorded.
  Ratified: `stall_retries` is a validated-but-reserved FR-75 knob (FR-74 abandons —
  the signals-free engine can't safely requeue), the requeue-vs-abandon default the
  instruction delegated to the Council.

## Step-0 gen-007 calibration (the finding that decided the design)
From the frozen run dirs (`harness_runs/20260622T193939Z` — the 18-tick
`HALT:stalled`):
- **`defu` (job-00011): genuinely hung.** Last heartbeat 22:42:05Z; last OUTPUT write
  ~23:00Z (19:00 EDT); then silent until HALT 00:53:03Z → OUT-AGE ~1h53m at HALT.
  Reclaim is the right fix.
- **`goshs` (job-00015): alive-but-quiet false-stall.** Last heartbeat 00:04:47Z
  (HB-AGE only ~48m at HALT) and it kept WRITING full output AFTER the HALT (BUG
  writeups at 22:37 EDT = 02:37Z; log dir `20260623T014440Z`). A time-only reclaim
  would have abandoned a live worker.
**Conclusion:** mixed case → the output-fresh guard is **load-bearing, not optional**,
which is exactly why FR-74 + FR-73 ship together. Calibrated `stall_reclaim_minutes`
= 90 (2× the 45m stall threshold): `defu` crosses 90m heartbeat-silence at ~00:12Z
with stale output → reclaimed → one slot frees → the 43-queue drains before HALT;
`goshs` at 48m is not even reclaim-eligible and, being output-fresh, would be held
even past 90m.

## Process
- **Committed BEFORE the Council** (`68a3cc3`) — the instr-004/005 lesson. Confirmed
  the hard way this tick: a mutation-test `git checkout` reverted the *uncommitted*
  engine work; restoring from a side backup re-proved the value of committing first.
  The mutation bites were then re-run safely against the committed tree.
- Both load-bearing pin mutations bite-executed in-tree (Python 3.14.6).

## Evidence
- Suite: baseline 463 → **483 passed ×3** (`python3 -m pytest tests/`), Python 3.14.6.
- Mutation bites: drain pin (remove reclaim ⇒ `HALT:stalled`); output-fresh pin (drop
  the guard ⇒ live worker abandoned). Both restored → green.
- stdlib-only engine preserved (NFR-3); OUT-AGE display-only invariant pinned.

**Iterate-to-SHIP complete. Unanimous SHIP.**
