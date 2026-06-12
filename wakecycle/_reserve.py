"""Pre-release reservation entry point (0.0.1).

Prints a placeholder line so `wakecycle` / `wakecycle --version` is a valid
installed command while the name is reserved on PyPI/npm. Intentionally
minimal and ASCII-safe; v0.1.0 wires the real tick engine + ticker."""
from __future__ import annotations
import sys

_MSG = ("wakecycle 0.0.1 - pre-release placeholder; the agent harness ships "
        "here shortly: https://github.com/andrewstellman/wakecycle")


def main(argv=None) -> int:
    print(_MSG)
    return 0


if __name__ == "__main__":
    sys.exit(main())
