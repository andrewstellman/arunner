#!/usr/bin/env python3
"""arunner jobs  -  the plan defaults + placeholder filler (FR-43).

ONE format: a plan is a single ``jobs`` list whose jobs carry friendly,
mode-discriminated keys (``id``/``repo``/``mode`` + the per-mode field). There
is no longer a shorthand/canonical dialect split, so this module no longer
RENAMES anything -- it is a thin convenience layer that:

  * merges a plan-level ``defaults`` map UNDER each job (the job's own key
    wins), and
  * injects the reserved-placeholder preamble into each ``agent`` job's
    ``prompt`` so a saved/expanded plan is concrete.

Both are IDEMPOTENT and OPTIONAL: the engine (tick.py) merges the same defaults
at ``--init`` and auto-injects the same preamble at dispatch, so a bare source
plan and an expanded one run identically. ``expand_jobs`` exists for the session
bundle (FR-52.4) and for tools that want the concrete plan on disk.

Stdlib only. Usage: ``jobs.py expand <plan.json>`` prints the filled plan JSON.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# The placeholder preamble injected into every agent prompt. Carries the FULL
# engine placeholder block; the engine substitutes these with absolute paths at
# dispatch (FR-21a, no model-transcribed paths). Keep in lockstep with
# tick._PLACEHOLDERS / tick._PLACEHOLDER_HEADER.
_PLACEHOLDER_KEYS = ("HEARTBEAT_PATH", "TASK_ID", "RUN_DIR", "TARGET_REPO",
                     "HARNESS_BIN")
_PLACEHOLDER_HEADER = "".join("%s={%s}\n" % (k, k) for k in _PLACEHOLDER_KEYS) + "\n"


def _inject_preamble(prompt: str) -> str:
    """Prepend the placeholder preamble unless the prompt already carries
    {HEARTBEAT_PATH} (idempotent — never doubles a header)."""
    if "{HEARTBEAT_PATH}" in (prompt or ""):
        return prompt or ""
    return _PLACEHOLDER_HEADER + (prompt or "")


def _fill_job(job: dict, defaults: dict) -> dict:
    if not isinstance(job, dict):
        return job
    merged = dict(defaults) if defaults else {}
    merged.update(job)
    if merged.get("mode") == "agent" and isinstance(merged.get("prompt"), str):
        merged["prompt"] = _inject_preamble(merged["prompt"])
    return merged


def expand_jobs(doc: dict) -> dict:
    """Fill ``defaults`` into each job + inject the agent placeholder preamble.
    A doc without ``jobs`` is returned unchanged (so a tool can fill-then-check
    uniformly)."""
    if not isinstance(doc, dict) or "jobs" not in doc:
        return doc
    defaults = doc.get("defaults") if isinstance(doc.get("defaults"), dict) else {}
    plan = {k: v for k, v in doc.items() if k != "defaults"}
    plan["jobs"] = [_fill_job(j, defaults) for j in (doc.get("jobs") or [])]
    return plan


def session_bundle(doc: dict) -> dict:
    """FR-52.4 ``my_run.json``: one file carrying the SOURCE (``jobs`` + knobs +
    optional ``defaults``) AND the filled ``plan``, so a saved session reruns
    faithfully (run the ``plan``) yet stays editable (the source)."""
    bundle = {k: v for k, v in doc.items() if k != "plan"}
    bundle["plan"] = expand_jobs(doc)
    return bundle


def bundle_drifted(bundle: dict) -> bool:
    """True if re-filling a my_run.json bundle's source no longer matches its
    saved ``plan`` (a hand-edit-drift signal -- warn, don't block)."""
    src = {k: v for k, v in bundle.items() if k != "plan"}
    return expand_jobs(src) != bundle.get("plan")


def _write_json(obj, out_path) -> None:
    Path(out_path).write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    out = save = None
    if "--out" in args:
        i = args.index("--out"); out = args[i + 1] if i + 1 < len(args) else None
        del args[i:i + 2]
    if "--save" in args:
        i = args.index("--save"); save = args[i + 1] if i + 1 < len(args) else None
        del args[i:i + 2]
    if len(args) == 2 and args[0] == "expand":
        try:
            doc = json.loads(Path(args[1]).read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            print("jobs: cannot read plan %s (%s)" % (args[1], exc),
                  file=sys.stderr)
            return 2
        if save:                              # FR-52.4: persist source + plan
            _write_json(session_bundle(doc), save)
            print(save)
        elif out:                             # FR-52.4: write the filled plan
            _write_json(expand_jobs(doc), out)
            print(out)
        else:
            print(json.dumps(expand_jobs(doc), indent=2))
        return 0
    print("usage: jobs.py expand <plan.json> [--out <plan>] [--save <my_run.json>]",
          file=sys.stderr)
    return 64


if __name__ == "__main__":
    sys.exit(main())
