# Panelist A — message-handling correctness (FR-60)

Charter: drain under the `.tick.lock`; idempotent-by-id processed-ids ledger; crash-replay safe;
`--check` pre-gate; append-only numbering + placeholders unresolved.

1. **Drain under `.tick.lock`, STOP-gated.** `tick()` calls `_drain_inbox` inside
   `if not (run_dir/"STOP").exists():`, mirroring the FR-57 `_absorb_incoming` idiom one line
   above. Both call sites (tick.py main, ticker `_one_tick`) hold the lock before `tick()`. A STOP
   tick drains nothing (FR-10 read-only).
2. **Idempotent, mark-FIRST, crash-replay safe.** `_drain_inbox` commits the id via
   `_mark_processed` BEFORE `_process_message`. PIN bite: mutating `if mid in processed:` → `if
   False:` made both `Idempotency` PINs FAIL ("replay double-dispatched", 3≠2); `git checkout` +
   pycache purge → 2 passed. No double-dispatch window: a same-drain duplicate hits the in-memory
   `processed` set; a cross-tick replay hits the on-disk `.processed`. The mark→batched-persist
   window is at-most-once (a crash loses an unacked effect, never double-applies) — the spec's
   load-bearing property.
3. **`--check` pre-gate.** `_check_message` (closed verb + args) + `check_plan` on the synthesized
   entries run BEFORE `pentries.append`. Live repro: a `frobnicate` message → rejected ack, tick
   still ran (entries unchanged). `test_check_rejects_bad_entry_before_landing` covers entry-level
   rejection.
4. **Append-only numbering + placeholders unresolved.** `idx = len(pentries)+1` (positional,
   same as `_absorb_incoming`); `pentries.append(e)` stores the entry verbatim — `{TARGET_REPO}`
   resolved only at dispatch. Full module 11 passed.

No drain-outside-lock, no STOP-drains, no apply-before-mark double-dispatch, no malformed-crash,
no renumber. Repo left clean.

VERDICT: SHIP
