# Instruction 010 — FR-75: per-job retry policy

## What this is
arunner has **no retry** — a `FAILED` or `abandoned` job stays terminal. The gen-007 run had a **~20% transient abort rate** (`child runner exited 1`) that needed manual wrapper re-runs. FR-75 adds a per-job **`max_attempts`** (+ optional backoff): a job that hits a **retryable terminal** (`FAILED`, or `abandoned` via FR-74 reclaim) is **requeued up to `max_attempts`** before going terminal-`FAILED`; with resumable workers a retry **resumes** (doesn't restart). The in-engine version of "recovery by re-run," automatic. It **lands the `stall_retries` seam** FR-74 (006) reserved.

## Prerequisite / branch (single-trunk)
Short-lived branch off `main` (the post-FR-76 HEAD). **Pre-flight:** `git rev-parse main` and confirm `git log --oneline -3 main` shows the FR-76 commits (`71a2608` + `945fab0`) — `main` must contain FR-76 before this branches. Then `git worktree add ~/Documents/arunner-fr75 -b fr75-retry main`. Implement, self-Council to SHIP, commit. **Worker does NOT push/merge** — operator lands.

## Reference (read first — spec, not code to paste)
- `docs/PLANNED_run_robustness.md` **§5 (FR-75)**.
- **The `stall_retries` seam:** FR-74 (006) shipped `stall_retries` as a validated-but-reserved plan field (default 0; FR-74 always abandons) because "the signals-free engine can't safely requeue a subagent without a heartbeat-collision." FR-75 is where safe requeue lands (resume-not-restart + heartbeat isolation). Read `outputs/006-continue-past-stall.md` + the FR-74 reclaim path.
- `arunner/engine/tick.py` (`_dispatch`, `_advance`, the `FAILED`/`abandoned` terminals, the FR-6 claim-lock, the FR-74 reclaim, the FR-76 done_check), `references/STATE_MACHINE.md`, `docs/REQUIREMENTS.md` (FR-6), `SDLC.md`. Re-confirm line numbers on `main`.

## The work
1. **`max_attempts` (schema, both copies, byte-identical).** Per-job optional `max_attempts` (int ≥ 1; **default 1 = no retry**, current behavior). Optional `retry_backoff_seconds` (delay before a requeued attempt becomes dispatch-eligible; default 0, driven by the `ARUNNER_NOW` clock seam — no real sleeps). Add to both schema copies + `--check` validation (`max_attempts ≥ 1`, backoff ≥ 0).
2. **Requeue on retryable-terminal, up to the cap (engine).** When a job reaches `FAILED` (or `abandoned` via FR-74 reclaim) and its recorded attempt count < `max_attempts`: **requeue** it (→ `queued`, attempt++ persisted in run state) instead of leaving it terminal; it becomes dispatch-eligible after `retry_backoff_seconds`. After the cap is exhausted → terminal-`FAILED` (decide + justify whether a reclaimed-`abandoned` job ends `FAILED` or stays `abandoned`).
3. **Resume-not-restart.** A retry of a job with a resumable worker (checkpointed output / an FR-76 `done_check`) **resumes**, not restart. Compose with FR-76: a retry whose `done_check` is now satisfied is **skipped** (no wasted attempt).
4. **Land the `stall_retries` seam.** Fold FR-74's reserved `stall_retries` into this policy — either generalize it to `max_attempts`, or supersede it cleanly (keep back-compat or document the migration; justify). A stalled-reclaimed (`abandoned`) job is now subject to the retry policy.
5. **Invariants.** FR-6 compose: a requeue can **never** double-dispatch (claim-lock holds; a requeued job is `queued`, dispatched once per attempt). Terminal-`FAILED` stays reachable after the cap. Optional transient-vs-fatal classification (a pre-flight/auth failure that can't succeed on retry need not burn attempts) — default is retry-all-up-to-cap; justify if you add it. stdlib-only (NFR-3).

## Tests (red→green, mutation-verified; `jobs`/`mode` format; clock via `ARUNNER_NOW`)
- **THE pin — retry then succeed:** a stub that FAILS attempt 1 with `max_attempts: 2` is **requeued + dispatched again**, and succeeds on attempt 2 → `completed`. Mutation: remove the requeue ⇒ stays `FAILED` after attempt 1 ⇒ bite.
- **Cap honored:** `max_attempts: 2` with an always-failing job → exactly 2 attempts then terminal-`FAILED` (never infinite). Mutation: off-by-one / no cap ⇒ bite.
- **No double-dispatch on requeue (FR-6):** a requeued job is dispatched once per attempt, never concurrently.
- **Resume-not-restart + FR-76 compose:** a retried resumable job resumes; a retry whose `done_check` is satisfied is skipped (no wasted attempt).
- **`max_attempts: 1` / absent = no retry:** a single failure is terminal (back-compat unchanged).
- **stall-reclaim path:** an `abandoned` (FR-74-reclaimed) job with `max_attempts > 1` is requeued (the `stall_retries` seam now live).
- **backoff:** a requeued attempt isn't dispatch-eligible until `retry_backoff_seconds` elapse (via `ARUNNER_NOW`).
- **`--check`:** `max_attempts ≥ 1`, backoff ≥ 0. Full suite green **×3** (counts + Python version). stdlib-only (NFR-3).

## Council — mandatory 3-panel self-Council (`runner/reviews/010_self_council/`, committed)
- **A — state-machine/correctness:** the retryable-terminal → requeue transition; attempt accounting persisted (crash-safe across a tick); terminal-`FAILED` reachable after the cap; resume-not-restart; FR-76 compose; backoff timing.
- **B — regression-safety:** FR-6 no-double-dispatch on requeue; `max_attempts:1`/absent = current behavior (back-compat); the `stall_retries` seam folded cleanly (no FR-74 regression); FR-72 launch + FR-74 reclaim + FR-76 done_check untouched; shell + subagent parity; no real sleeps (ARUNNER_NOW seam).
- **C — tests/honesty:** retry-then-succeed + cap pins mutation-bite; FR-75 + US/UC next-free (no reuse); §9 honest.
Iterate to unanimous SHIP.

## §9 / requirements
Add **FR-75** + a US + a UC at next-free numbers (after FR-76's US-21/UC-17 — no reuse) + a §9 VERIFIED row. Update `references/STATE_MACHINE.md` (both copies, identical) with the retryable-terminal → requeue edge + the attempt-cap terminal. Note the FR-6 / FR-74 (`stall_retries`) / FR-76 lineage.

## Commit / output
Focused commits on `fr75-retry` (do NOT push/merge — operator lands + deletes the branch/worktree). Output → `outputs/010-fr75-retry.md`: the design (`max_attempts`/backoff, requeue point, the `stall_retries` folding + your end-state-for-abandoned decision), before/after, the retry-then-succeed + cap pins + mutation bites, per-test evidence, the 3-panel synthesis, suite counts ×3 + Python version, FR-75 + US/UC + §9 rows, the STATE_MACHINE delta, `git log --oneline`.
