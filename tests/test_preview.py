"""FR-52 interactive builder — the deterministic `preview` helper + the UC-10
worked examples (instr 033).

`preview` is the confirm-gate echo: per job it renders the dispatch mode + the
prompt/command source, then the --check verdict (exit 1 on failure -> no clean
'go'). The host agent does the NL understanding; this only RENDERS the already-
assembled shorthand, so it is deterministic and unit-testable.

MUTATION-VERIFY EVIDENCE (DEVELOPMENT_PROCESS Mutation-test), instr 033:
  Pin: test_preview_renders_per_job_dispatch.
    Mutation: make cli._job_summary always return ("SUBAGENT", ...).
    Observed: a wrap/tail job no longer renders 'SHELL (wrap)'/'SHELL (tail)'
      -> the test FAILs. Restored OK.
"""
from __future__ import annotations

import importlib.util
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, _ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


CLI = _load("arunner_cli_pv", "arunner/cli.py")
TICK = _load("arunner_tick_pv", "arunner/engine/tick.py")
JOBS = _load("arunner_jobs_pv", "arunner/engine/jobs.py")


class _Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _write(self, name, doc):
        p = self.tmp / name
        p.write_text(json.dumps(doc))
        return p

    def _preview(self, path):
        out = io.StringIO()
        with redirect_stdout(out):
            rc = CLI.main(["preview", str(path)])
        return rc, out.getvalue()


class PreviewTests(_Base):

    def test_preview_renders_per_job_dispatch(self):
        mixed = {"pool_size": 2, "jobs": [
            {"id": "review", "repo": str(self.tmp), "agent": "subagent",
             "prompt": "Review for bugs."},
            {"id": "build", "repo": str(self.tmp), "adapter": "wrap",
             "command": ["./build.sh", "--release"]},
            {"id": "watch", "repo": str(self.tmp), "adapter": "tail",
             "log_path": "/tmp/run.log", "success_regex": "OK"}]}
        rc, out = self._preview(self._write("mixed.json", mixed))
        self.assertEqual(rc, 0)
        self.assertIn("job 1 [review]: SUBAGENT", out)
        self.assertIn("job 2 [build]: SHELL (wrap)  wraps: ./build.sh --release", out)
        self.assertIn("job 3 [watch]: SHELL (tail)  tails: /tmp/run.log", out)
        self.assertIn("--check: OK", out)                # clean -> safe to run

    def test_preview_reports_check_failure_no_go(self):
        bad = {"pool_size": 1, "jobs": [
            {"id": "x", "repo": "/no/such/dir", "agent": "subagent", "prompt": "p"}]}
        rc, out = self._preview(self._write("bad.json", bad))
        self.assertEqual(rc, 1)                          # no clean 'go'
        self.assertIn("--check: FAILED", out)
        self.assertIn("target_repo", out)
        self.assertNotIn("Safe to run", out)

    def test_preview_canonical_plan(self):
        plan = {"pool_size": 1, "entries": [
            {"task_id": "t", "target_repo": str(self.tmp), "dispatch_mode": "shell",
             "adapter": "wrap", "command": ["make", "test"]}]}
        rc, out = self._preview(self._write("p.json", plan))
        self.assertEqual(rc, 0)
        self.assertIn("SHELL (wrap)  wraps: make test", out)


class Uc10ExampleTests(_Base):
    """The two FR-52/UC-10 headline examples expand + pass --check."""

    def _expand_check(self, example_name):
        doc = json.loads((_ROOT / "examples" / example_name).read_text())
        plan = JOBS.expand_jobs(doc)
        for e in plan["entries"]:
            e["target_repo"] = str(self.tmp)             # illustrative path -> real dir
        p = self.tmp / "p.json"; p.write_text(json.dumps(plan))
        return TICK.check_plan(p), plan

    def test_three_md_reviews_is_subagent(self):
        probs, plan = self._expand_check("uc10_three_md_reviews.jobs.json")
        self.assertEqual(probs, [])
        self.assertEqual(len(plan["entries"]), 3)
        self.assertTrue(all(e["dispatch_mode"] == "subagent" for e in plan["entries"]))

    def test_four_exes_is_shell_wrap(self):
        probs, plan = self._expand_check("uc10_four_exes.jobs.json")
        self.assertEqual(probs, [])
        self.assertEqual(len(plan["entries"]), 4)
        self.assertTrue(all(e.get("adapter") == "wrap" for e in plan["entries"]))


if __name__ == "__main__":
    unittest.main()
