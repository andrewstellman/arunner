"""FR-34 — one canonical version, every mirror tracks it (drift-tested).

The single source is ``wakecycle/__init__.py:__version__``. ``pyproject.toml``,
``package.json``, and the plugin SKILL.md frontmatter MIRROR it; the
``_reserve`` console stub READS it (no hardcoded literal). This test is
VALUE-AGNOSTIC: it never hardcodes the version number — it only asserts every
surface equals ``__version__`` — so a routine bump touches one place and the
test still guards drift.

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
import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _canonical() -> str:
    for line in (_ROOT / "wakecycle" / "__init__.py").read_text(
            encoding="utf-8").splitlines():
        if line.startswith("__version__"):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise AssertionError("no __version__ in wakecycle/__init__.py")


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
        skill = (_ROOT / "plugins" / "wakecycle" / "skills" / "wakecycle"
                 / "SKILL.md").read_text(encoding="utf-8")
        m = re.search(r"(?m)^version:\s*(\S+)\s*$", skill)
        self.assertIsNotNone(m, "SKILL.md frontmatter has no version")
        self.assertEqual(m.group(1), self.canon)

    def test_reserve_stub_reads_canonical(self):
        sys.path.insert(0, str(_ROOT))
        try:
            import wakecycle
            from wakecycle import _reserve
        finally:
            sys.path.pop(0)
        self.assertEqual(wakecycle.__version__, self.canon)
        # the console stub builds its message from __version__, not a literal
        self.assertTrue(_reserve._MSG.startswith("wakecycle %s" % self.canon),
                        "_reserve._MSG must read __version__: %r" % _reserve._MSG)

    def test_bin_scripts_read_canonical(self):
        # tick.py / ticker.py read the same single source for their banners
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "tick_ver", _ROOT / "bin" / "tick.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        self.assertEqual(mod._wakecycle_version(), self.canon)


if __name__ == "__main__":
    unittest.main()
