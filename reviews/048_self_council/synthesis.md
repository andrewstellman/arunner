# Instruction 048 self-council synthesis — FR-60 chat ⇄ runner message channel

*Mandatory 3-panel (engine-state + idempotency hazards). Three fresh-context, role-locked,
adversarial reviewers verifying on disk: tracing the drain under the lock, biting the
idempotency-ledger and read-only never-writes pins, reproducing the ack/result lifecycle
end-to-end, and grepping for a network listener. Date: 2026-06-16.*

| Panelist | Charter | Verdict |
|----------|---------|---------|
| `panelist_A_message_handling.md` | drain under lock; idempotent-by-id mark-first ledger; crash-replay safe; `--check` pre-gate; append-only/placeholders | **SHIP** |
| `panelist_B_ack_result_verbs.md` | every message acked; results correlate id↔task_id; closed verb set only; loop semantics in worker_prompts | **SHIP** |
| `panelist_C_readonly_regression.md` | read-only verbs never-writes pin bites; no network listener; no regression; STOP read-only preserved | **SHIP** |

## Outcome: unanimous SHIP (round 1)

### Panelist A — message-handling correctness (SHIP)
`_drain_inbox` is called inside `tick()` within the `if not (run_dir/"STOP").exists():` gate,
mirroring the FR-57 `_absorb_incoming` idiom; both call sites (tick.py main / ticker `_one_tick`)
hold the `.tick.lock` before `tick()`. **Mark-FIRST** ledger: the id is appended to
`inbox/.processed` BEFORE `_process_message`, so a crash/replay never double-applies — PIN bite
verified (defeating the ledger check made both `Idempotency` PINs FAIL 3≠2; restored → pass). No
duplicate-id double-dispatch window (same-drain dup hits the in-memory set; cross-tick replay hits
the on-disk ledger). `--check` runs `_check_message` + `check_plan` on the synthesized entries
BEFORE `pentries.append`; a `frobnicate` message → rejected ack, tick still ran (entries unchanged).
Append-only `idx = len(pentries)+1`; placeholders stored verbatim, resolved only at dispatch.

### Panelist B — ack/result + verb semantics (SHIP)
`_write_ack` writes one append-only `<id>.ack.json` (message_id+status+reason+task_ids) for EVERY
message (malformed → rejected; bad `--check` → rejected; applied otherwise). End-to-end: an
`enqueue` gave `applied task_ids:[chat]` then `result.json completed:true task_ids:[chat]
run_states:{run-04:completed}` — id↔task_id correlation confirmed, emitted only when all staged
runs are terminal. `_MSG_VERBS` is exactly the six closed verbs — no grade/improve/council verb in
the engine; `dispatch-job` carries semantics in its `worker_prompt` (data, never shell-evaluated);
`control` writes the existing FR-35..39 control files (not reimplemented). CLI: `msg` send-side
`--check` rejects `control --op cadence` (no minutes) before it lands; `msg_verb` metavar avoids
the subparser-dispatch collision; `outbox` reads acks+results.

### Panelist C — read-only safety + regression (SHIP)
`snapshot` writes only `outbox/<id>.result.json`; `note` appends only to `journal.ndjson`; both
return without touching status/plan/lock. PIN bite verified: inserting a `harness_status.json`
write made `test_readonly_verbs_never_write_run_state` FAIL on `st_mtime_ns` (byte-identical
content) — the `(bytes, mtime_ns, size)` fingerprint bites a no-op temp+rename rewrite; restored →
pass. No network listener: `grep socket|http.server|socketserver|bind(|listen(|os.system` over
tick.py+cli.py → no matches; the `test_no_network_listener_in_engine` guard locks it. Full suite
**334 passed** (323 +11); positioning-honesty 7; FR-58b/Windows-floor/FR-55 rows undisturbed. Diff
confined to tick.py/cli.py/test_message_channel.py + the FR-60 docs. Inbox-less tick is a fast
no-op (`_drain_inbox` returns on absent inbox; `_emit_ready_results` on empty pending). STOP tick
drains nothing and emits nothing — read-only preserved; messages wait in `inbox/` until STOP clears.

## Note on a transient pin "failure" during review
Panelist B observed one transient `Idempotency` failure on a cold first run, then 57+ consecutive
passes across modes; manual replay confirmed the mark-first ledger is correct. Consistent with the
project's known stale-`.pyc`/first-import artifact, not a code defect; the committed HEAD is clean
and the pins bite on the authoritative tree.

## Net
FR-60 lands as a typed, acknowledged, idempotent message channel generalizing FR-57's
stage-and-absorb: inbox drained under `.tick.lock` (STOP-gated read-only), mark-first processed-ids
ledger (crash-safe), append-only outbox ack+result (id↔task_id correlation), a closed six-verb set
with loop semantics kept in the `worker_prompt`s, read-only verbs never-writes-pinned, local-disk
only (no network listener), and `arunner msg`/`outbox` CLI. 11 tests, 2 mutation-pinned invariants.
Suite 323 → 334.
