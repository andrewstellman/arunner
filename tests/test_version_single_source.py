"""FR-34 — one canonical version, every mirror tracks it (drift-tested).

The single source is ``arunner/__init__.py:__version__``. ``pyproject.toml``,
``package.json``, and the plugin SKILL.md frontmatter MIRROR it; the engine
banner (``tick.py``) and the REAL installed console script (``arunner.cli:main``
via ``arunner --version``) READ it (no hardcoded literal). The pre-release
``_reserve`` stub is RETIRED (13a) — this test now guards the real entry point.
This test is VALUE-AGNOSTIC: it never hardcodes the version number — it only
asserts every surface equals ``__version__`` — so a routine bump touches one
place and the test still guards drift.

MUTATION-VERIFY EVIDENCE (DEVELOPMENT_PROCESS §Mutation-test), instr 018:
  Pin: test_pyproject_mirrors_canonical (and the package.json / SKILL twins).
  Mutation: change ``version = "0.1.0"`` in pyproject.toml to ``"0.1.1"``.
  Observed: the pyproject drift assertion FAILs (mirror != __version__).
  Restored -> OK. (The 1.5.9-vs-0.0.1 extraction bug is exactly the drift
  this guards.)
"""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _canonical() -> str:
    for line in (_ROOT / "arunner" / "__init__.py").read_text(
            encoding="utf-8").splitlines():
        if line.startswith("__version__"):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise AssertionError("no __version__ in arunner/__init__.py")


class VersionSingleSourceTests(unittest.TestCase):

    def setUp(self):
        self.canon = _canonical()

    def test_canonical_is_nonempty_semverish(self):
        self.assertRegex(self.canon, r"^\d+\.\d+\.\d+")

    def test_pyproject_mirrors_canonical(self):
        m = re.search(r'(?m)^version\s*=\s*"([^"]+)"',
                      (_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        self.assertIsNotNone(m, "pyproject.toml has no version line")
        self.assertEqual(m.group(1), self.canon)

    def test_package_json_mirrors_canonical(self):
        pkg = json.loads((_ROOT / "package.json").read_text(encoding="utf-8"))
        self.assertEqual(pkg.get("version"), self.canon)

    def test_skill_frontmatter_mirrors_canonical(self):
        # the 1.5.9-vs-0.0.1 extraction bug lived exactly here
        skill = (_ROOT / "plugins" / "arunner" / "skills" / "arunner"
                 / "SKILL.md").read_text(encoding="utf-8")
        m = re.search(r"(?m)^version:\s*(\S+)\s*$", skill)
        self.assertIsNotNone(m, "SKILL.md frontmatter has no version")
        self.assertEqual(m.group(1), self.canon)

    def test_plugin_json_mirrors_canonical(self):
        # 13a: the marketplace plugin.json version is a release surface too;
        # it had drifted to 0.0.1 while every other surface was 0.1.0.
        pj = json.loads((_ROOT / "plugins" / "arunner" / ".claude-plugin"
                         / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(pj.get("version"), self.canon)

    def test_console_script_is_the_real_cli_not_reserve(self):
        # 13a: the entry point invokes the real CLI router, and the retired
        # pre-release stub is gone with no dangling reference.
        pyproject = (_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn('arunner = "arunner.cli:main"', pyproject)
        self.assertNotIn("_reserve", pyproject)
        self.assertFalse((_ROOT / "arunner" / "_reserve.py").exists(),
                         "the pre-release _reserve stub must be retired (13a)")

    def test_console_script_prints_canonical(self):
        # the REAL console script (arunner.cli:main) prints the single source
        # via `--version` — value-agnostic, so a bump needs no test edit.
        import contextlib
        import importlib.util
        import io
        spec = importlib.util.spec_from_file_location(
            "cli_ver", _ROOT / "arunner" / "cli.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        buf = io.StringIO()
        with self.assertRaises(SystemExit) as cm, \
                contextlib.redirect_stdout(buf):
            mod.main(["--version"])
        self.assertEqual(cm.exception.code, 0)
        self.assertEqual(buf.getvalue().strip(), "arunner %s" % self.canon)

    def test_bin_scripts_read_canonical(self):
        # tick.py / ticker.py read the same single source for their banners
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "tick_ver", _ROOT / "arunner" / "engine" / "tick.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        self.assertEqual(mod._arunner_version(), self.canon)


if __name__ == "__main__":
    unittest.main()
