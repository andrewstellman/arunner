"""Pre-release reservation entry point (version from arunner.__version__).

Prints a placeholder line so `arunner` / `arunner --version` is a valid
installed command while the name is reserved on PyPI/npm. Intentionally
minimal and ASCII-safe; v0.1.0 wires the real tick engine + ticker."""
from __future__ import annotations
import sys

from arunner import __version__

_MSG = (f"arunner {__version__} - pre-release placeholder; the agent harness "
        f"ships here shortly: https://github.com/andrewstellman/arunner")


def main(argv=None) -> int:
    print(_MSG)
    return 0


if __name__ == "__main__":
    sys.exit(main())
