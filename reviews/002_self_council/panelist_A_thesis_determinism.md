# Panelist A — Thesis / Determinism (FR-61..65 implementation, instr 002)

**Charter:** disk-truth + determinism (NFR-6); FR-51 "never grades its own homework" + measurement-fencing; tokens reporting-only (FR-65/FR-18); shell gate exit-code-only; single-prompt path unaffected.

**What I traced (read + executed repros against `arunner/engine/tick.py`):**

1. **Read-on-resume / no recomputation.** `_evaluate_gate` early-returns the persisted `gate.json["outcome"]` before any argv runs. Repro: pre-persisted `continue` + a `touch+exit 1` argv → returned `continue`, sentinel **never created**. A malformed/keyless `gate.json` on resume → `internal_error` (fail-closed). `_reap_step` and `_advance_to` are idempotent (result.json existence guard) — a reaped step is never re-run.

2. **FR-51 + measurement fence.** `_check_gate` rejects a reasoning gate without `allow_reasoning_gates:true`, in any `measurement:true` run, with `same_context:true`, and with no distinct judge — all four reproduced. The judge dispatches as a DISTINCT sub-run (`_dispatch_judge`, own dir/heartbeat/task_id). `_evaluate_gate` returns `continue` for non-shell kinds — the engine **never** grades reasoning inline. Absent/malformed `data.verdict` → `internal_error` halt. The deterministic shell gate is the only kind passing `--check` in measurement runs.

3. **Tokens reporting-only.** `_usage_of` reads exactly `data.usage` (sibling keys ignored — verified). IN_PROGRESS+usage → `_terminal_status_of`=None (tokens never make a run done). `done` and `_halt_reason` read only run states/flags/blockers. No-usage → `{}` → cell `-` (no fabricated 0); `_add_tok` leaves None unreported.

4. **Shell gate exit-code-only.** `_eval_shell_gate`: `subprocess.run(..., stdout=DEVNULL, stderr=DEVNULL)`, maps only `returncode`. Repro: argv printing "HALT FAILED" but `exit 0` → `continue`. No stdout/regex surface.

5. **Single-prompt unaffected.** All step/gate/token code gated behind `_is_multistep`/`step_count`/`gate_pending`. Baseline 334 + new tests all green.

**Adversarial finding (NOT blocking):** `init_run` performs no validation, so a `measurement:true` plan with a reasoning gate that bypasses `--check` *would* enter judging at runtime. But `init_run` validates *nothing* — the engine's trust model is "`--check` before `--init`" (NFR-11), the pre-existing contract, not a FR-63 regression. Worth a one-line defense-in-depth doc note, not a code fix.

No FIX-REQUIRED. Every determinism/thesis invariant is upheld on disk.

**VERDICT: SHIP**
