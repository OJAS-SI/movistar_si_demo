#!/usr/bin/env python3
"""Plug-and-play entry point: run the whole Movistar Structural Intelligence demo.

    python run_demo.py                 fast live run (tiny scale)
    python run_demo.py --scale full    the production picture (thousands of homes)
    python run_demo.py --self-test     run and exit non-zero if anything is off

Works from any working directory.
"""
import os
import shutil
import sys

# The demo uses dataclass features (e.g. slots=True) that require Python 3.10+.
# The default `python3` on some machines is older, so if we are running on an
# incompatible interpreter, transparently re-exec on a newer one when available.
MIN_VERSION = (3, 10)


def _ensure_supported_python() -> None:
    if sys.version_info[:2] >= MIN_VERSION:
        return
    if not os.environ.get("_SI_DEMO_REEXEC"):
        for name in ("python3.13", "python3.12", "python3.11", "python3.10"):
            exe = shutil.which(name)
            if exe:
                env = dict(os.environ, _SI_DEMO_REEXEC="1")
                os.execve(exe, [exe, os.path.abspath(__file__), *sys.argv[1:]], env)
    have = ".".join(map(str, sys.version_info[:3]))
    need = ".".join(map(str, MIN_VERSION))
    sys.stderr.write(
        f"error: this demo requires Python {need}+, but found {have}.\n"
        f"       install a newer Python (e.g. python3.13) and re-run:\n"
        f"           python3.13 {os.path.basename(__file__)}\n"
    )
    sys.exit(1)


_ensure_supported_python()

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))

from si_core.orchestrator import main

if __name__ == "__main__":
    sys.exit(main())
