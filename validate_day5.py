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
    FailureAnalysis, StackFrame, register_error_rule,
    _CUSTOM_ERROR_RULES
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


def test_expanded_classification() -> bool:
    """Test 5: Expanded exception coverage and custom rule registration."""

    taxonomy = FailureTaxonomy()
    knowledge = KnowledgeCore()
    analyzer = ErrorAnalyzer(taxonomy, knowledge)

    ctx = StructuredContext(language="python", problem_type="test_failure")

    # Test new built-in exception types
    new_exceptions = [
        ("RecursionError: maximum recursion depth exceeded",
         "RecursionError: maximum recursion depth exceeded",
         ErrorCategory.RUNTIME_ERROR),
        ("ZeroDivisionError: division by zero",
         "ZeroDivisionError: division by zero",
         ErrorCategory.VALUE_ERROR),
        ("ConnectionRefusedError: [Errno 111] Connection refused",
         "ConnectionRefusedError: [Errno 111] Connection refused",
         ErrorCategory.CONNECTION_ERROR),
        ("IndentationError: unexpected indent",
         "IndentationError: unexpected indent",
         ErrorCategory.SYNTAX_ERROR),
        ("UnicodeDecodeError: 'utf-8' codec can't decode byte",
         "UnicodeDecodeError: 'utf-8' codec can't decode byte",
         ErrorCategory.VALUE_ERROR),
    ]

    for error_text, traceback_text, expected_cat in new_exceptions:
        test_result = TestResult(
            total_tests=5, passed=4, failed=1, skipped=0,
            duration_seconds=0.5,
            failures=[{'name': 'test_x', 'error': error_text, 'traceback': traceback_text}],
        )
        analyses = analyzer.analyze_test_failure(test_result, ctx)
        if not analyses:
            print(f"  FAIL: No analysis for {error_text}")
            return False
        if analyses[0].category != expected_cat:
            print(f"  FAIL: {error_text} -> {analyses[0].category.value}, expected {expected_cat.value}")
            return False

    # Test custom rule registration
    register_error_rule(
        'DjangoHttp404',
        ErrorCategory.FILE_NOT_FOUND,
        "Requested URL does not map to any view",
        ["Check URL patterns", "Verify view exists"],
    )

    # Custom rule should take effect
    cat, assumption, fixes = analyzer._classify_error('DjangoHttp404', 'Not Found')
    if cat != ErrorCategory.FILE_NOT_FOUND:
        print(f"  FAIL: Custom rule not applied: got {cat.value}")
        return False
    if "URL" not in assumption:
        print(f"  FAIL: Custom assumption not used: {assumption}")
        return False

    # Clean up custom rules for other tests
    _CUSTOM_ERROR_RULES.clear()

    return True


def test_fix_safety_guards() -> bool:
    """Test 6: FIX_AND_RETRY is blocked without safety preconditions."""

    taxonomy = FailureTaxonomy()
    knowledge = KnowledgeCore()
    analyzer = ErrorAnalyzer(taxonomy, knowledge)

    ctx = StructuredContext(language="python", problem_type="test_failure")

    # Create an analysis with stack frames
    test_result = TestResult(
        total_tests=10, passed=9, failed=1, skipped=0,
        duration_seconds=1.0,
        failures=[{
            'name': 'test_auth',
            'error': 'TypeError: expected str, got int',
            'traceback': '''Traceback (most recent call last):
  File "auth.py", line 10, in validate
    return name.upper()
TypeError: expected str, got int''',
        }],
    )
    analyses = analyzer.analyze_test_failure(test_result, ctx)
    analysis = analyses[0]

    # Get FIX_AND_RETRY strategy
    strategies = analyzer.suggest_recovery(analysis, has_baseline=True, has_backup=True)
    fix_strategy = None
    for s in strategies:
        if s.action == RecoveryAction.FIX_AND_RETRY:
            fix_strategy = s
            break

    if not fix_strategy:
        print("  FAIL: No FIX_AND_RETRY strategy generated for TypeError")
        return False

    # Test 1: Should be BLOCKED without explanation gate or test coverage
    is_safe, blockers = analyzer.validate_fix_safety(
        fix_strategy, analysis,
        explanation_gate_complete=False,
        affected_tests_exist=False,
    )
    if is_safe:
        print("  FAIL: FIX_AND_RETRY should be blocked without safety preconditions")
        return False
    if len(blockers) < 2:
        print(f"  FAIL: Expected >= 2 blockers, got {len(blockers)}: {blockers}")
        return False

    # Test 2: Should be ALLOWED with all preconditions met
    is_safe, blockers = analyzer.validate_fix_safety(
        fix_strategy, analysis,
        explanation_gate_complete=True,
        affected_tests_exist=True,
    )
    if not is_safe:
        print(f"  FAIL: FIX_AND_RETRY should be allowed with all preconditions: {blockers}")
        return False

    # Test 3: execute_recovery should block when safety fails
    result = analyzer.execute_recovery(
        fix_strategy, None, None,
        explanation_gate_complete=False,
        affected_tests_exist=False,
        analysis=analysis,
    )
    if result.success:
        print("  FAIL: execute_recovery should fail when safety gate blocks")
        return False
    if "safety gate" not in result.message:
        print(f"  FAIL: Expected safety gate message, got: {result.message}")
        return False

    # Test 4: Catastrophic severity should always block FIX_AND_RETRY
    catastrophic_result = TestResult(
        total_tests=10, passed=1, failed=9, skipped=0,
        duration_seconds=1.0,
        failures=[
            {'name': f'test_{i}', 'error': 'TypeError: bad', 'traceback': ''}
            for i in range(9)
        ],
    )
    cat_analyses = analyzer.analyze_test_failure(catastrophic_result, ctx)
    cat_worst = max(cat_analyses, key=lambda a: a.severity.value)

    is_safe, blockers = analyzer.validate_fix_safety(
        fix_strategy, cat_worst,
        explanation_gate_complete=True,
        affected_tests_exist=True,
    )
    if is_safe:
        print("  FAIL: FIX_AND_RETRY should be blocked for catastrophic severity")
        return False

    return True


def test_deduplication() -> bool:
    """Test 7: Clustering deduplication prevents false positives."""

    taxonomy = FailureTaxonomy()
    knowledge = KnowledgeCore()
    analyzer = ErrorAnalyzer(taxonomy, knowledge)

    ctx = StructuredContext(language="python", problem_type="test_failure")

    # Generate 10 failures: 5 identical TypeErrors + 5 identical KeyErrors
    failures = []
    for i in range(5):
        failures.append({
            'name': f'test_type_{i}',
            'error': 'TypeError: expected str, got int',
            'traceback': 'TypeError: expected str, got int',
        })
        failures.append({
            'name': f'test_key_{i}',
            'error': "KeyError: 'user_id'",
            'traceback': "KeyError: 'user_id'",
        })

    test_result = TestResult(
        total_tests=20, passed=10, failed=10, skipped=0,
        duration_seconds=2.0, failures=failures,
    )

    analyses = analyzer.analyze_test_failure(test_result, ctx)

    if len(analyses) != 10:
        print(f"  FAIL: Expected 10 analyses, got {len(analyses)}")
        return False

    # Deduplication should collapse to 2 unique failures
    unique = analyzer.deduplicate_analyses(analyses)
    if len(unique) != 2:
        print(f"  FAIL: Expected 2 unique after dedup, got {len(unique)}")
        return False

    # build_failure_taxonomy with deduplicate=True should have 1 per cluster
    clusters_dedup = analyzer.build_failure_taxonomy(analyses, deduplicate=True)
    for cat, items in clusters_dedup.items():
        if len(items) != 1:
            print(f"  FAIL: Cluster '{cat}' should have 1 unique, got {len(items)}")
            return False

    # Without dedup, should have all 5 per cluster
    clusters_raw = analyzer.build_failure_taxonomy(analyses, deduplicate=False)
    for cat, items in clusters_raw.items():
        if len(items) != 5:
            print(f"  FAIL: Raw cluster '{cat}' should have 5, got {len(items)}")
            return False

    # Trend analysis should report cluster quality
    trends = analyzer.analyze_failure_trends()
    if 'cluster_quality' not in trends:
        print("  FAIL: No cluster_quality in trends")
        return False

    # Each cluster should be marked as coherent (low diversity = identical errors)
    for cat, quality in trends['cluster_quality'].items():
        if not quality['is_coherent']:
            print(f"  FAIL: Cluster '{cat}' should be coherent (identical errors)")
            return False
        if quality['unique'] != 1:
            print(f"  FAIL: Cluster '{cat}' should have 1 unique, got {quality['unique']}")
            return False

    # Dedup ratio should be 0.2 (2 unique / 10 total)
    if trends['dedup_ratio'] != 0.2:
        print(f"  FAIL: Expected dedup_ratio 0.2, got {trends['dedup_ratio']}")
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
        ("Expanded classification + custom rules", test_expanded_classification),
        ("FIX_AND_RETRY safety guards", test_fix_safety_guards),
        ("Clustering deduplication", test_deduplication),
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
