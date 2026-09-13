"""Unified test runner for Day 3 Feasibility Spikes (A, B, C)."""

from __future__ import annotations

import pathlib
import sys
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from docs.day03.spikes.spike_a_anchors import TestSpikeAAnchors
from docs.day03.spikes.spike_b_schema_gate import TestSpikeBSchemaGate
from docs.day03.spikes.spike_c_revisions import TestSpikeCRevisions


def run_all_spikes() -> bool:
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()

    suite.addTests(loader.loadTestsFromTestCase(TestSpikeAAnchors))
    suite.addTests(loader.loadTestsFromTestCase(TestSpikeBSchemaGate))
    suite.addTests(loader.loadTestsFromTestCase(TestSpikeCRevisions))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_all_spikes()
    sys.exit(0 if success else 1)
