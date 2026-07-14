"""
Module 0 - The contract guards and the freeze marker.

This file makes the four-field boundary checkable at runtime and at test time, and
pins the version of the frozen contract that Modules 1 through 8 build against.

The boundary is enforced at three levels:
  1. Structural : CoreRecord is a frozen, slotted dataclass with exactly four
     fields (see types.py). Enrichment physically cannot be attached to it.
  2. Guarded    : assert_core_stream_clean() lets the SI engine assert, at its own
     entry point, that what it received is a stream of CoreRecords and nothing else.
  3. Tested     : assert_four_field_boundary() introspects the CoreRecord type and
     fails if the field set ever drifts from the canonical four. The standalone test
     calls it, so a fifth field can never be added unnoticed.
"""

from __future__ import annotations

import dataclasses
from typing import Iterable, Iterator

from .types import CORE_RECORD_FIELDS, CoreRecord


# The frozen-contract version. Bumping this is a deliberate, breaking act; every
# downstream module records that it was built against this version.
FROZEN_CONTRACT_VERSION = "0.1.0-module0-frozen"


def assert_four_field_boundary() -> None:
    """Introspect the CoreRecord dataclass and confirm it carries exactly the four
    canonical fields, in order. Raises AssertionError if the boundary has drifted.

    This is the structural guarantee in testable form: if any later change adds a
    fifth field to CoreRecord (which would let enrichment leak into the SI engine),
    this assertion fails and the standalone test goes red."""
    actual = tuple(f.name for f in dataclasses.fields(CoreRecord))
    assert actual == CORE_RECORD_FIELDS, (
        f"Four-field boundary violated: CoreRecord fields are {actual}, "
        f"expected exactly {CORE_RECORD_FIELDS}"
    )
    # Confirm slots are in force, so instances cannot have ad-hoc attributes added.
    assert getattr(CoreRecord, "__slots__", None) is not None, (
        "CoreRecord must be slotted so enrichment cannot be attached to an instance"
    )


def assert_core_stream_clean(stream: Iterable[object]) -> Iterator[CoreRecord]:
    """Wrap a stream the SI engine is about to consume, asserting that every element
    is a CoreRecord. Returns a generator that yields the validated records, so the
    SI engine can call this at its entry point as a guard:

        for rec in assert_core_stream_clean(incoming):
            ...

    Any non-CoreRecord element (e.g. an EnrichmentRecord that leaked through) raises
    TypeError immediately, at the boundary, with a clear message."""
    for element in stream:
        if not isinstance(element, CoreRecord):
            raise TypeError(
                "Four-field boundary violated at the SI engine entry: expected "
                f"CoreRecord, received {type(element).__name__}. Enrichment must "
                "never reach the Structural Intelligence engine."
            )
        yield element
