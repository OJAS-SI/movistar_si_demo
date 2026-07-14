"""Entry point so the whole demo runs with `python -m si_core`."""
import sys

from .orchestrator import main

if __name__ == "__main__":
    sys.exit(main())
