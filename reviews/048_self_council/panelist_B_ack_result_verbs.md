# Panelist B — ack/result + verb semantics (FR-60)

Charter: every message acked; results correlate id↔task_id; closed verb set only; loop semantics
stay in `worker_prompt`s, not the engine.

1. **Acks.** `_write_ack` writes `<id>.ack.json` (message_id + status + reason + task_ids),
   append-only (written once, never mutated). `_drain_inbox` acks EVERY message — malformed JSON →
   `rejected "malformed JSON"`; `--check` fail → `rejected` with problems; applied verbs →
   `applied`. `AckResultLifecycle` 2/2.
2. **Results correlate id↔task_id.** Live e2e: `e1.ack.json` = applied, task_ids:["chat"];
   `e1.result.json` = completed:true, task_ids:["chat"], run_states:{run-04:completed}.
   `_emit_ready_results` emits only once `all(state in _TERMINAL_STATES)`, inside the not-STOP path.
3. **Closed verb set / loop semantics out of engine.** `_MSG_VERBS` is exactly enqueue / control /
   dispatch-job / run-batch / snapshot / note — no grade/improve/council/commit-and-rerun verb.
   `dispatch-job` forces `dispatch_mode:"subagent"` and the `worker_prompt` is placeholder-
   substituted for an orchestrator to launch — never `subprocess`/shell. `control` writes the
   existing FR-35..39 control files (PAUSE/RESUME/POLL-NOW/CADENCE/CANCEL) consumed by
   `_apply_controls`, not reimplemented.
4. **CLI.** `arunner msg ... snapshot` sends (exit 0); `control --op cadence` (no minutes) is
   rejected before send (exit 1, never lands) via send-side `_check_message`; unknown verb blocked
   by argparse `choices`; `arunner outbox` reads acks + results. `msg_verb` is a `metavar="verb"`
   positional — no dispatch collision.

Note (non-blocking): one transient `Idempotency` failure on a cold first run, then 57+ consecutive
passes; manual replay confirmed the mark-first ledger is correct. Stale-`.pyc` first-import
artifact, not a code defect. Full module 11/11; broader suite no regressions.

VERDICT: SHIP
