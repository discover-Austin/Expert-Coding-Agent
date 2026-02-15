#!/usr/bin/env python3
"""
Day 5 Validation: Error Recovery & Learning

Binary validation — pass or fail, no soft passes.

Tests:
1. Stack trace parsing: extracts file, line, function, code
2. Error classification: maps errors to correct categories + fixes
3. Recovery strategies: suggests appropriate recovery for each category
4. Learning loop: failures feed into taxonomy and knowledge core
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from knowledge_core import (
    KnowledgeCore, StructuredContext, PatternCategory, OutcomeType
)
from failure_taxonomy import FailureTaxonomy
from codebase_engine import TestResult
from error_analyzer import (
    ErrorAnalyzer, ErrorCategory, RecoveryAction,
    FailureAnalysis, StackFrame
)


def test_stack_trace_parsing() -> bool:
    """Test 1: Stack trace parsing extracts structured frames."""

    taxonomy = FailureTaxonomy()
    knowledge = KnowledgeCore()
    analyzer = ErrorAnalyzer(taxonomy, knowledge)

    traceback_text = '''Traceback (most recent call last):
  File "/app/src/handler.py", line 42, in process_request
    result = validate_input(data)
  File "/app/src/validator.py", line 17, in validate_input
    raise ValueError("Invalid email format")
ValueError: Invalid email format'''

    frames = analyzer._parse_stack_trace(traceback_text)

    # Must extract exactly 2 frames
    if len(frames) != 2:
        print(f"  FAIL: Expected 2 frames, got {len(frames)}")
        return False

    # First frame
    if frames[0].file_path != "/app/src/handler.py":
        print(f"  FAIL: Wrong file path: {frames[0].file_path}")
        return False
    if frames[0].line_number != 42:
        print(f"  FAIL: Wrong line number: {frames[0].line_number}")
        return False
    if frames[0].function_name != "process_request":
        print(f"  FAIL: Wrong function: {frames[0].function_name}")
        return False
    if "validate_input" not in frames[0].code_line:
        print(f"  FAIL: Wrong code line: {frames[0].code_line}")
        return False

    # Second frame
    if frames[1].file_path != "/app/src/validator.py":
        print(f"  FAIL: Wrong file path: {frames[1].file_path}")
        return False
    if frames[1].line_number != 17:
        print(f"  FAIL: Wrong line: {frames[1].line_number}")
        return False
    if frames[1].function_name != "validate_input":
        print(f"  FAIL: Wrong function: {frames[1].function_name}")
        return False

    return True


def test_error_classification() -> bool:
    """Test 2: Errors are classified into correct categories with fixes."""

    taxonomy = FailureTaxonomy()
    knowledge = KnowledgeCore()
    analyzer = ErrorAnalyzer(taxonomy, knowledge)

    ctx = StructuredContext(language="python", problem_type="test_failure")

    test_cases = [
        # (error_text, traceback_text, expected_category)
        (
            "ImportError: No module named 'pandas'",
            "ImportError: No module named 'pandas'",
            ErrorCategory.IMPORT_ERROR,
        ),
        (
            "TypeError: unsupported operand type(s) for +: 'int' and 'str'",
            "TypeError: unsupported operand type(s) for +: 'int' and 'str'",
            ErrorCategory.TYPE_ERROR,
        ),
        (
            "KeyError: 'missing_key'",
            "KeyError: 'missing_key'",
            ErrorCategory.KEY_ERROR,
        ),
        (
            "AttributeError: 'NoneType' object has no attribute 'name'",
            "AttributeError: 'NoneType' object has no attribute 'name'",
            ErrorCategory.ATTRIBUTE_ERROR,
        ),
        (
            "FileNotFoundError: [Errno 2] No such file or directory: 'config.yml'",
            "FileNotFoundError: [Errno 2] No such file or directory: 'config.yml'",
            ErrorCategory.FILE_NOT_FOUND,
        ),
    ]

    for error_text, traceback_text, expected_category in test_cases:
        test_result = TestResult(
            total_tests=10,
            passed=9,
            failed=1,
            skipped=0,
            duration_seconds=1.0,
            failures=[{
                'name': 'test_something',
                'error': error_text,
                'traceback': traceback_text,
            }],
        )

        analyses = analyzer.analyze_test_failure(test_result, ctx)

        if not analyses:
            print(f"  FAIL: No analysis produced for: {error_text}")
            return False

        analysis = analyses[0]
        if analysis.category != expected_category:
            print(f"  FAIL: Expected {expected_category.value}, got {analysis.category.value}")
            print(f"    Error: {error_text}")
            return False

        # Must have suggested fixes
        if not analysis.suggested_fixes:
            print(f"  FAIL: No suggested fixes for {error_text}")
            return False

        # Must have a violated assumption
        if not analysis.violated_assumption:
            print(f"  FAIL: No violated assumption for {error_text}")
            return False

    return True


def test_recovery_strategies() -> bool:
    """Test 3: Recovery strategies are appropriate for each category."""

    taxonomy = FailureTaxonomy()
    knowledge = KnowledgeCore()
    analyzer = ErrorAnalyzer(taxonomy, knowledge)

    ctx = StructuredContext(language="python", problem_type="test_failure")

    # Test 1: Severe failure should suggest rollback first
    test_result = TestResult(
        total_tests=10,
        passed=2,
        failed=8,
        skipped=0,
        duration_seconds=1.0,
        failures=[
            {'name': f'test_{i}', 'error': 'ImportError: No module named x', 'traceback': ''}
            for i in range(8)
        ],
    )

    analyses = analyzer.analyze_test_failure(test_result, ctx)
    if not analyses:
        print("  FAIL: No analysis for severe failure")
        return False

    worst = max(analyses, key=lambda a: a.severity.value)
    strategies = analyzer.suggest_recovery(worst, has_baseline=True, has_backup=True)

    if not strategies:
        print("  FAIL: No recovery strategies suggested")
        return False

    # Best strategy for severe failure with backup should be rollback
    best = strategies[0]
    if best.action != RecoveryAction.ROLLBACK:
        print(f"  FAIL: Expected ROLLBACK as best strategy, got {best.action.value}")
        return False

    if best.confidence < 0.9:
        print(f"  FAIL: Rollback confidence too low: {best.confidence}")
        return False

    # Test 2: Timeout error should include retry strategy
    test_result_timeout = TestResult(
        total_tests=10,
        passed=9,
        failed=1,
        skipped=0,
        duration_seconds=1.0,
        failures=[{
            'name': 'test_api',
            'error': 'TimeoutError: Connection timed out',
            'traceback': 'TimeoutError: Connection timed out',
        }],
    )

    analyses_timeout = analyzer.analyze_test_failure(test_result_timeout, ctx)
    if not analyses_timeout:
        print("  FAIL: No analysis for timeout failure")
        return False

    strategies_timeout = analyzer.suggest_recovery(
        analyses_timeout[0], has_baseline=True, has_backup=False
    )

    retry_found = any(s.action == RecoveryAction.RETRY for s in strategies_timeout)
    if not retry_found:
        print("  FAIL: No RETRY strategy for timeout error")
        return False

    # Every strategy set must include ESCALATE as last resort
    escalate_found = any(s.action == RecoveryAction.ESCALATE for s in strategies)
    if not escalate_found:
        print("  FAIL: No ESCALATE strategy (should always be present)")
        return False

    return True


def test_learning_loop() -> bool:
    """Test 4: Failures feed into taxonomy and knowledge core."""

    taxonomy = FailureTaxonomy()
    knowledge = KnowledgeCore()
    analyzer = ErrorAnalyzer(taxonomy, knowledge)

    ctx = StructuredContext(
        language="python",
        problem_type="concurrency",
        domain="concurrency",
    )

    # Simulate multiple similar failures to trigger archetype formation
    for i in range(5):
        test_result = TestResult(
            total_tests=10,
            passed=9,
            failed=1,
            skipped=0,
            duration_seconds=1.0,
            failures=[{
                'name': f'test_concurrent_{i}',
                'error': f'RuntimeError: race condition in shared counter #{i}',
                'traceback': f'RuntimeError: race condition in shared counter #{i}',
            }],
        )

        analyses = analyzer.analyze_test_failure(test_result, ctx)
        if not analyses:
            print(f"  FAIL: No analysis for failure {i}")
            return False

        analyzer.learn_from_failure(analyses[0], ctx)

    # Check taxonomy got signatures
    if len(taxonomy.signatures) < 5:
        print(f"  FAIL: Expected >= 5 signatures, got {len(taxonomy.signatures)}")
        return False

    # Check knowledge core got concepts
    summary = knowledge.get_summary()
    if summary['total_concepts'] == 0:
        print("  FAIL: No concepts recorded in knowledge core")
        return False

    if summary['total_instances'] == 0:
        print("  FAIL: No instances recorded in knowledge core")
        return False

    # Check failure trend analysis works
    trends = analyzer.analyze_failure_trends()
    if trends['total_failures'] < 5:
        print(f"  FAIL: Expected >= 5 recorded failures, got {trends['total_failures']}")
        return False

    if not trends['category_counts']:
        print("  FAIL: No category counts in trends")
        return False

    return True


def main():
    print("=" * 70)
    print("DAY 5 VALIDATION: Error Recovery & Learning")
    print("=" * 70)
    print()

    tests = [
        ("Stack trace parsing", test_stack_trace_parsing),
        ("Error classification", test_error_classification),
        ("Recovery strategies", test_recovery_strategies),
        ("Learning loop", test_learning_loop),
    ]

    results = []
    for name, test_fn in tests:
        print(f"Testing: {name}...")
        try:
            passed = test_fn()
        except Exception as e:
            print(f"  EXCEPTION: {e}")
            import traceback
            traceback.print_exc()
            passed = False

        symbol = "PASS" if passed else "FAIL"
        print(f"  {symbol}")
        print()
        results.append(passed)

    print("=" * 70)
    passed = sum(results)
    total = len(results)
    print(f"Results: {passed}/{total} tests passed")
    print()

    if all(results):
        print("ALL TESTS PASSED")
    else:
        print("SOME TESTS FAILED")
        for (name, _), result in zip(tests, results):
            if not result:
                print(f"  FAILED: {name}")

    print("=" * 70)

    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
