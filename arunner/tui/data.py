"""FR-62 read-only DATA LAYER for the Textual TUI -- pure stdlib, no Textual.

Every function here is a STRICTLY READ-ONLY consumer of a run-dir's externalized
disk state -- the same load-bearing property FR-59's monitor holds: no run-state
write, no ``.tick.lock``, no control file, no tick. It only *reads*
``harness_status.json``, ``plan.json``, per-entry ``run-NN/heartbeat.ndjson`` +
``manifest.json``, ``results/``, and ``journal.ndjson``.

It reuses, never forks:
  * the FR-59 monitor's frame renderer (``cli.render_monitor_frame`` ->
    ``tick._format_table``) for the live run-view table, so the TUI can't drift
    from ``arunner monitor``;
  * the engine's own record readers (``tick._read_result_record``,
    ``tick._heartbeat_path``, ``tick._hb_observe``) for entry detail.

Splitting this out from ``arunner.tui.app`` is what keeps Textual off the engine
path: this module is importable on a bare ``arunner`` install (no `[tui]`
extra), so the never-writes / renderer-reuse pins run without Textual present.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

# Reuse the FR-59 monitor render path (shared `_format_table`, no fork) and the
# engine's on-disk record readers. `arunner.cli` is stdlib-only and imports no
# Textual, so importing it here keeps the data layer Textual-free.
from arunner import cli as CLI

TICK = CLI.TICK

# How many trailing lines a heartbeat/journal tail returns by default.
DEFAULT_TAIL = 200


def default_runs_root() -> Path:
    """The directory ``arunner run`` scaffolds run-dirs under: ``ARUNNER_RUNS_DIR``
    if set, else ``<repo>/harness_runs`` -- the same resolution ``init_run`` uses
    (kept in sync via the engine constant path, not a forked default)."""
    base = os.environ.get("ARUNNER_RUNS_DIR")
    if base:
        return Path(base)
    # arunner/engine/tick.py -> parents: engine, arunner, <repo>
    return Path(TICK.__file__).resolve().parent.parent.parent / "harness_runs"


def _read_json(path: Path):
    """Best-effort read of a JSON file -- None on missing/garbage/partial (the
    engine's atomic write-temp-rename means a *successful* read is never partial;
    a transient failure just yields None, never an exception). READ-ONLY."""
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def is_run_dir(path) -> bool:
    """A path is a run-dir iff it holds a ``harness_status.json`` (the same probe
    ``status``/``monitor``/``add`` use). READ-ONLY."""
    return (Path(path) / "harness_status.json").is_file()


def list_runs(runs_root=None) -> list[dict]:
    """The run picker's model: every run-dir under ``runs_root`` (default
    ``default_runs_root()``), NEWEST-FIRST, each as a summary dict
    ``{run_dir, name, cycle, counts, done, pool_size, mtime, ok}``.

    Strictly read-only: it lists directories and reads each
    ``harness_status.json`` -- it never creates ``runs_root`` and never writes.
    A run-dir whose status is missing/garbage is reported with ``ok=False`` (so
    the picker can show it rather than crash), never skipped silently."""
    root = Path(runs_root) if runs_root is not None else default_runs_root()
    if not root.is_dir():
        return []
    out = []
    for child in root.iterdir():
        if not child.is_dir():
            continue
        sp = child / "harness_status.json"
        if not sp.is_file():
            continue
        try:
            mtime = sp.stat().st_mtime
        except OSError:
            mtime = 0.0
        status = _read_json(sp)
        if status is None:
            out.append({"run_dir": child, "name": child.name, "cycle": None,
                        "counts": {}, "done": None, "pool_size": None,
                        "mtime": mtime, "ok": False})
            continue
        out.append({
            "run_dir": child,
            "name": child.name,
            "cycle": status.get("cycle"),
            "counts": dict(status.get("counts") or {}),
            "done": bool(status.get("done")),
            "pool_size": status.get("pool_size"),
            "mtime": mtime,
            "ok": True,
        })
    out.sort(key=lambda r: r["mtime"], reverse=True)            # newest-first
    return out


def run_view_frame(run_dir, interval: float = 2.0, now=None):
    """The live run-view table. Delegates to the FR-59 monitor's
    ``cli.render_monitor_frame`` -- the SAME ``_format_table`` + state-loader the
    ``monitor`` verb uses, so the TUI's table can never fork from the monitor's.
    Returns ``(text, terminal, ok)``; ``ok=False`` skips a transient bad frame
    (the view keeps its last good render). STRICTLY READ-ONLY."""
    return CLI.render_monitor_frame(Path(run_dir), interval=interval, now=now)


def entry_names(run_dir) -> list[str]:
    """The ``run-NN`` names in this run, ordered (the entry-list model). Reads
    ``harness_status.json['runs']``. READ-ONLY."""
    status = _read_json(Path(run_dir) / "harness_status.json") or {}
    return sorted((status.get("runs") or {}).keys())


def entry_detail(run_dir, run_name: str) -> dict | None:
    """The entry view's model: the FULL per-entry record for one ``run-NN`` --

      * the lifecycle record from ``harness_status.json['runs'][run_name]``
        (state, task_id, job_id, target_repo, claimed_at, last_hb_status),
      * ``dispatch_mode`` + any ``heartbeat_path`` from the per-run
        ``manifest.json`` (where the engine records them),
      * the live heartbeat observation (status / activity / mtime),
      * the ``results/`` record if the job is terminal.

    Returns None if the run-dir or the named entry is absent. STRICTLY
    READ-ONLY (the only fs ops are reads + a heartbeat tail)."""
    run_dir = Path(run_dir)
    status = _read_json(run_dir / "harness_status.json")
    if status is None:
        return None
    rec = (status.get("runs") or {}).get(run_name)
    if rec is None:
        return None
    manifest = _read_json(run_dir / run_name / "manifest.json") or {}
    hb_path = TICK._heartbeat_path(run_dir, run_name)
    has_any, hb_status, activity, hb_mtime = TICK._hb_observe(hb_path)
    result = TICK._read_result_record(run_dir, rec.get("job_id"))
    return {
        "run": run_name,
        "task_id": rec.get("task_id"),
        "job_id": rec.get("job_id"),
        "target_repo": rec.get("target_repo"),
        "state": rec.get("state"),
        "dispatch_mode": manifest.get("dispatch_mode"),
        "claimed_at": rec.get("claimed_at"),
        "last_hb_status": rec.get("last_hb_status"),
        "heartbeat_path": str(hb_path),
        "heartbeat_present": bool(has_any),
        "hb_status": hb_status,
        "activity": activity,
        "hb_mtime": hb_mtime,
        "result": result,
        "terminal": result is not None,
    }


def heartbeat_history(run_dir, run_name: str, limit: int = DEFAULT_TAIL) -> list[dict]:
    """The entry's heartbeat history: the last ``limit`` lines of its
    ``run-NN/heartbeat.ndjson`` parsed to dicts (a malformed line is surfaced as
    ``{'_raw': <line>}`` rather than dropped, so the operator sees it). Honors a
    FR-20 ``heartbeat_path`` override via ``_heartbeat_path``. READ-ONLY."""
    hb = TICK._heartbeat_path(Path(run_dir), run_name)
    return _tail_parsed(hb, limit)


def journal_tail(run_dir, limit: int = DEFAULT_TAIL) -> list[dict]:
    """The run's ``journal.ndjson`` tail (per-tick verdict + note records),
    parsed like ``heartbeat_history``. READ-ONLY."""
    return _tail_parsed(Path(run_dir) / "journal.ndjson", limit)


def tail_lines(path, limit: int = DEFAULT_TAIL) -> list[str]:
    """Raw trailing lines of any file (the log/heartbeat tail primitive). Reads
    with ``errors='replace'`` -- worker-written heartbeat/journal content may
    carry stray non-UTF-8 bytes, which must not crash the reader (the
    185/189/190 encoding lesson). READ-ONLY; missing file -> ``[]``."""
    p = Path(path)
    if not p.is_file():
        return []
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    lines = [ln for ln in text.splitlines() if ln.strip()]
    return lines[-limit:] if limit else lines


def _tail_parsed(path, limit: int) -> list[dict]:
    out = []
    for ln in tail_lines(path, limit):
        try:
            obj = json.loads(ln)
        except ValueError:
            out.append({"_raw": ln})
            continue
        out.append(obj if isinstance(obj, dict) else {"_raw": ln})
    return out


# --- pure text view-models (Textual-free, so they're testable headless) ------

def format_picker_row(run: dict) -> str:
    """One run-picker line: name, cycle, queued/running/completed/failed counts,
    done flag -- a pure function of a ``list_runs`` summary dict."""
    if not run.get("ok"):
        return "%-22s  (unreadable harness_status.json)" % run["name"]
    c = run.get("counts") or {}
    failed = (c.get("failed", 0) + c.get("auth_or_launch_failed", 0)
              + c.get("abandoned", 0))
    flag = "DONE" if run.get("done") else "live"
    return ("%-22s  cyc %-4s  Q%-3d R%-3d C%-3d F%-3d  %s" % (
        run["name"], run.get("cycle"), c.get("queued", 0), c.get("running", 0),
        c.get("completed", 0), failed, flag))


def format_entry_detail(detail: dict) -> str:
    """The entry view's text body: the full per-entry record + heartbeat history
    + the results record if terminal. Pure function of ``entry_detail`` +
    ``heartbeat_history`` output (passed in), so it renders identically in a test
    and in the live TUI."""
    if detail is None:
        return "(no such entry)"
    lines = [
        "Entry %s  (task %s, job %s)" % (
            detail["run"], detail.get("task_id"), detail.get("job_id")),
        "-" * 60,
        "state         : %s" % detail.get("state"),
        "target_repo   : %s" % detail.get("target_repo"),
        "dispatch_mode : %s" % detail.get("dispatch_mode"),
        "claimed_at    : %s" % detail.get("claimed_at"),
        "last_hb_status: %s" % detail.get("last_hb_status"),
        "activity      : %s" % detail.get("activity"),
        "heartbeat     : %s" % detail.get("heartbeat_path"),
    ]
    result = detail.get("result")
    if result is not None:
        lines += ["", "results/ record (terminal):"]
        for k in ("status", "result_file", "summary", "reaped_ts"):
            if k in result:
                lines.append("  %-12s: %s" % (k, result[k]))
    return "\n".join(lines)


def format_history(records: list[dict], limit: int = 20) -> str:
    """Compact heartbeat/journal history: the last ``limit`` records, one per
    line (status + label/text), newest last. Pure function of parsed records."""
    if not records:
        return "(no heartbeat lines yet)"
    out = []
    for rec in records[-limit:]:
        if "_raw" in rec:
            out.append("  ! " + str(rec["_raw"]))
            continue
        ts = rec.get("ts") or ""
        status = rec.get("status") or rec.get("type") or ""
        label = rec.get("label") or rec.get("phase") or rec.get("text") \
            or rec.get("verdict") or ""
        out.append("  %s  %-12s %s" % (ts, status, label))
    return "\n".join(out)
