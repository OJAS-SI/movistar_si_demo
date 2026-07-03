#!/usr/bin/env python3
"""
Run every test in the Movistar SI demo: each module's standalone test and the
growing integration test. No third-party dependency required.

    python run_tests.py

Exit code 0 if all suites pass, 1 otherwise. This script grows automatically: it
discovers every tests/test_*.py file and runs it.
"""

from __future__ import annotations

import importlib.util
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
    if os.environ.get("_SI_DEMO_REEXEC"):
        # Already tried to re-exec; avoid an infinite loop.
        _abort_unsupported()
    for name in ("python3.13", "python3.12", "python3.11", "python3.10"):
        exe = shutil.which(name)
        if exe:
            env = dict(os.environ, _SI_DEMO_REEXEC="1")
            os.execve(exe, [exe, os.path.abspath(__file__), *sys.argv[1:]], env)
    _abort_unsupported()


def _abort_unsupported() -> None:
    have = ".".join(map(str, sys.version_info[:3]))
    need = ".".join(map(str, MIN_VERSION))
    sys.stderr.write(
        f"error: this demo requires Python {need}+, but found {have}.\n"
        f"       install a newer Python (e.g. python3.13) and re-run:\n"
        f"           python3.13 {os.path.basename(__file__)}\n"
    )
    sys.exit(1)


_ensure_supported_python()

HERE = os.path.dirname(os.path.abspath(__file__))
TESTS = os.path.join(HERE, "tests")
if HERE not in sys.path:
    sys.path.insert(0, HERE)


def _load(path):
    spec = importlib.util.spec_from_file_location(
        os.path.splitext(os.path.basename(path))[0], path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    files = sorted(f for f in os.listdir(TESTS)
                   if f.startswith("test_") and f.endswith(".py"))
    all_ok = True
    for f in files:
        print(f"\n=== {f} ===")
        mod = _load(os.path.join(TESTS, f))
        runner = getattr(mod, "_run_all", None)
        if runner is None:
            print(f"  (no _run_all in {f}; skipped)")
            continue
        ok = runner()
        all_ok = all_ok and ok
    print("\n" + ("ALL SUITES PASSED" if all_ok else "SOME SUITES FAILED"))
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
