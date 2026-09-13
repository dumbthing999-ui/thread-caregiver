#!/usr/bin/env python3
"""Run actual contract tests; default exits nonzero for unresolved assertions.

--check-baseline validates only the explicitly listed known-red baseline, never
product acceptance. --record writes measured test outcomes and full tracebacks.
"""
import argparse
import datetime
import hashlib
import io
import json
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True


class CapturingResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.outcomes = []

    def addSuccess(self, test):
        super().addSuccess(test)
        self.outcomes.append({'test_id': test.id(), 'outcome': 'PASS'})

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.outcomes.append({'test_id': test.id(), 'outcome': 'ASSERTION_FAILURE',
                              'traceback': self.failures[-1][1]})

    def addError(self, test, err):
        super().addError(test, err)
        self.outcomes.append({'test_id': test.id(), 'outcome': 'ERROR',
                              'traceback': self.errors[-1][1]})


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-baseline', action='store_true')
    parser.add_argument('--record', action='store_true')
    args = parser.parse_args()
    manifest = json.loads((HERE / 'red-manifest.json').read_text())
    expected = set(manifest['expected_red_ids'])
    positive = set(manifest['positive_control_ids'])
    assert len(expected) == len(manifest['expected_red_ids'])
    assert len(positive) == len(manifest['positive_control_ids'])
    assert not expected & positive
    suite = unittest.defaultTestLoader.discover(str(HERE), pattern='test_*.py')
    output = io.StringIO()
    result = unittest.TextTestRunner(stream=output, verbosity=2,
                                    resultclass=CapturingResult).run(suite)
    failed = {test.id() for test, _ in result.failures}
    passed = {row['test_id'] for row in result.outcomes if row['outcome'] == 'PASS'}
    executed = {row['test_id'] for row in result.outcomes}
    integrity = (failed == expected and passed == positive and
                 executed == expected | positive and result.testsRun == len(expected | positive)
                 and not result.errors and not result.skipped and
                 not result.expectedFailures and not result.unexpectedSuccesses)
    paths = list((ROOT / 'docs/day03/spikes').glob('*.py'))
    paths += sorted(HERE.glob('*.py')) + [HERE / 'red-manifest.json']
    report = {
        'recorded_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'suite_command': 'python3 tests/day04/run_red_suite.py',
        'invocation': ['python3', 'tests/day04/run_red_suite.py', *sys.argv[1:]],
        'scope': manifest['scope'],
        'product_acceptance': 'NOT_PASSED' if not result.wasSuccessful() else 'TESTS_PASS_ONLY',
        'baseline_integrity': 'MATCH' if integrity else 'MISMATCH',
        'tests_run': result.testsRun, 'passed': len(passed),
        'assertion_failures': len(result.failures), 'errors': len(result.errors),
        'skipped': len(result.skipped),
        'expected_red_ids': manifest['expected_red_ids'],
        'positive_control_ids': manifest['positive_control_ids'],
        'unexpected_failure_ids': sorted(failed - expected),
        'missing_expected_failure_ids': sorted(expected - failed),
        'results': result.outcomes,
        'sha256': {str(path.relative_to(ROOT)): digest(path) for path in paths},
        'raw_suite_exit_code': 0 if result.wasSuccessful() else 1,
        'baseline_check_exit_code': 0 if integrity else 1,
    }
    text = output.getvalue()
    print(text, end='')
    print(f"Red-baseline integrity: {report['baseline_integrity']} (not product PASS)")
    if args.record:
        evidence = ROOT / 'docs/day04/evidence'
        evidence.mkdir(parents=True, exist_ok=True)
        (evidence / 'red-results.json').write_text(json.dumps(report, indent=2) + '\n')
        (evidence / 'red-tests.txt').write_text(text +
            f"\nRed-baseline integrity: {report['baseline_integrity']} (not product PASS)\n")
    return report['baseline_check_exit_code'] if args.check_baseline else report['raw_suite_exit_code']


if __name__ == '__main__':
    raise SystemExit(main())
