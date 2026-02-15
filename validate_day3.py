#!/usr/bin/env python3
"""
Day 3 Validation: Test Generation

Proves test generator:
1. Identifies untested code
2. Generates meaningful tests (not smoke tests)
3. Creates unit + edge case + integration tests
4. Validates quality (no trivial assertions)
"""

import sys
import tempfile
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from code_analyzer import CodeAnalyzer
from test_generator import TestGenerator, TestCase


def test_identifies_untested_code():
    """
    Test 1: Identifies functions without proper tests.
    
    Expected: Finds functions with no tests or only trivial assertions.
    """
    print("\n" + "="*70)
    print("TEST 1: IDENTIFIES UNTESTED CODE")
    print("="*70)
    
    tmpdir = Path(tempfile.mkdtemp())
    try:
        # Create module with untested function
        (tmpdir / "calculator.py").write_text("""
def add(a, b):
    return a + b

def subtract(a, b):
    return a - b

def multiply(a, b):
    return a * b
""")
        
        # Create test file with only one function tested
        (tmpdir / "test_calculator.py").write_text("""
import pytest
from calculator import add

def test_add():
    result = add(2, 3)
    assert result == 5
    assert result > 0
""")
        
        # Create pytest.ini
        (tmpdir / "pytest.ini").write_text("[pytest]\n")
        
        # Analyze
        analyzer = CodeAnalyzer()
        structure, graph = analyzer.analyze_project(tmpdir, language="python")
        
        # Generate tests
        test_gen = TestGenerator(analyzer)
        gaps = test_gen.find_coverage_gaps(structure, target_coverage=0.8)
        
        print(f"Coverage gaps found: {len(gaps)} files")
        for file, funcs in gaps.items():
            print(f"  {file}: {funcs}")
        
        # Verify we found the untested functions
        if 'calculator.py' in gaps:
            untested = set(gaps['calculator.py'])
            # subtract and multiply should be in gaps
            # add might or might not be (depends on "well tested" threshold)
            
            if 'subtract' in untested and 'multiply' in untested:
                print("\n✓ TEST 1 PASSED: Correctly identified untested functions")
                return True
            else:
                print(f"\n✗ TEST 1 FAILED: Expected subtract/multiply in gaps, got {untested}")
                return False
        else:
            print("\n✗ TEST 1 FAILED: No gaps found in calculator.py")
            return False
            
    finally:
        shutil.rmtree(tmpdir)


def test_generates_meaningful_tests():
    """
    Test 2: Generates tests with non-trivial assertions.
    
    Expected: No "assert True", real behavior checks.
    """
    print("\n" + "="*70)
    print("TEST 2: GENERATES MEANINGFUL TESTS")
    print("="*70)
    
    tmpdir = Path(tempfile.mkdtemp())
    try:
        # Create module
        (tmpdir / "auth.py").write_text("""
def login(username, password):
    if username == "admin" and password == "secret":
        return True
    return False
""")
        
        # No tests yet
        (tmpdir / "pytest.ini").write_text("[pytest]\n")
        
        # Analyze
        analyzer = CodeAnalyzer()
        structure, graph = analyzer.analyze_project(tmpdir, language="python")
        
        # Generate tests
        test_gen = TestGenerator(analyzer)
        suite = test_gen.generate_tests_for_module('auth.py')
        
        print(f"Generated {len(suite.test_cases)} tests")
        print()
        
        # Check test quality
        trivial_count = 0
        for test_case in suite.test_cases:
            print(f"Test: {test_case.name}")
            print(f"  Type: {test_case.test_type}")
            print(f"  Assertions: {test_case.assertions}")
            
            # Check for trivial assertions
            for assertion in test_case.assertions:
                if analyzer._is_trivial_assertion(assertion):
                    trivial_count += 1
                    print(f"  ⚠️  TRIVIAL: {assertion}")
        
        print()
        
        if trivial_count == 0:
            print("✓ TEST 2 PASSED: No trivial assertions generated")
            return True
        else:
            print(f"✗ TEST 2 FAILED: Found {trivial_count} trivial assertions")
            return False
            
    finally:
        shutil.rmtree(tmpdir)


def test_generates_multiple_test_types():
    """
    Test 3: Generates unit, edge case, and integration tests.
    
    Expected: Different test types for comprehensive coverage.
    """
    print("\n" + "="*70)
    print("TEST 3: GENERATES MULTIPLE TEST TYPES")
    print("="*70)
    
    tmpdir = Path(tempfile.mkdtemp())
    try:
        # Create module with dependencies
        (tmpdir / "service.py").write_text("""
def validate(data):
    if not data:
        return False
    return True

def process(data):
    if validate(data):
        return transform(data)
    return None

def transform(data):
    return data.upper()
""")
        
        (tmpdir / "pytest.ini").write_text("[pytest]\n")
        
        # Analyze
        analyzer = CodeAnalyzer()
        structure, graph = analyzer.analyze_project(tmpdir, language="python")
        
        # Generate tests
        test_gen = TestGenerator(analyzer)
        suite = test_gen.generate_tests_for_module('service.py')
        
        # Count test types
        test_types = {}
        for test_case in suite.test_cases:
            test_types[test_case.test_type] = test_types.get(test_case.test_type, 0) + 1
        
        print(f"Test types generated:")
        for test_type, count in test_types.items():
            print(f"  {test_type}: {count}")
        print()
        
        # Verify we have multiple types
        if len(test_types) >= 2:
            print("✓ TEST 3 PASSED: Multiple test types generated")
            return True
        else:
            print("✗ TEST 3 FAILED: Only one test type generated")
            return False
            
    finally:
        shutil.rmtree(tmpdir)


def test_validates_test_quality():
    """
    Test 4: Validation catches quality issues.
    
    Expected: Validation detects trivial assertions and missing rationale.
    """
    print("\n" + "="*70)
    print("TEST 4: VALIDATES TEST QUALITY")
    print("="*70)
    
    tmpdir = Path(tempfile.mkdtemp())
    try:
        (tmpdir / "dummy.py").write_text("def dummy(): pass")
        (tmpdir / "pytest.ini").write_text("[pytest]\n")
        
        analyzer = CodeAnalyzer()
        structure, graph = analyzer.analyze_project(tmpdir, language="python")
        
        test_gen = TestGenerator(analyzer)
        
        # Create a bad test manually
        from test_generator import TestSuite
        bad_suite = TestSuite(
            module_path="dummy.py",
            test_cases=[
                TestCase(
                    name="test_bad",
                    target_function="dummy",
                    test_type="unit",
                    assertions=["True"],  # Trivial
                    rationale=""  # Missing
                )
            ]
        )
        
        # Validate
        valid, issues = test_gen.validate_generated_tests(bad_suite)
        
        print(f"Validation result: {'PASS' if valid else 'FAIL'}")
        print(f"Issues found: {len(issues)}")
        for issue in issues:
            print(f"  - {issue}")
        print()
        
        # Should fail validation
        if not valid and len(issues) >= 2:  # Trivial assertion + missing rationale
            print("✓ TEST 4 PASSED: Validation catches quality issues")
            return True
        else:
            print("✗ TEST 4 FAILED: Validation should have caught issues")
            return False
            
    finally:
        shutil.rmtree(tmpdir)


def run_all_day3_tests():
    """Run all Day 3 validation tests"""
    
    print("="*70)
    print("DAY 3 VALIDATION: TEST GENERATION")
    print("="*70)
    print()
    print("Testing test generation capabilities:")
    print("  1. Identifies untested code")
    print("  2. Generates meaningful tests")
    print("  3. Creates multiple test types")
    print("  4. Validates test quality")
    print()
    
    results = []
    
    try:
        results.append(("Identifies untested code", test_identifies_untested_code()))
    except Exception as e:
        print(f"\n✗ Test 1 FAILED with exception: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Identifies untested code", False))
    
    try:
        results.append(("Generates meaningful tests", test_generates_meaningful_tests()))
    except Exception as e:
        print(f"\n✗ Test 2 FAILED with exception: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Generates meaningful tests", False))
    
    try:
        results.append(("Multiple test types", test_generates_multiple_test_types()))
    except Exception as e:
        print(f"\n✗ Test 3 FAILED with exception: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Multiple test types", False))
    
    try:
        results.append(("Validates quality", test_validates_test_quality()))
    except Exception as e:
        print(f"\n✗ Test 4 FAILED with exception: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Validates quality", False))
    
    # Summary
    print("\n" + "="*70)
    print("DAY 3 VALIDATION SUMMARY")
    print("="*70)
    print()
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        symbol = "✓" if result else "✗"
        print(f"{symbol} {name}")
    
    print()
    print(f"Results: {passed}/{total} tests passed")
    print()
    
    if passed == total:
        print("="*70)
        print("✓ DAY 3 COMPLETE")
        print("="*70)
        print()
        print("Test generation working:")
        print("  ✓ Identifies coverage gaps")
        print("  ✓ Generates meaningful tests")
        print("  ✓ Creates comprehensive test types")
        print("  ✓ Validates quality standards")
        print()
        print("Ready for Day 4: Refactoring")
        print("="*70)
        return True
    else:
        print("="*70)
        print("✗ DAY 3 INCOMPLETE")
        print("="*70)
        print()
        print(f"{total - passed} test(s) failing")
        print("Fix issues before proceeding")
        print("="*70)
        return False


if __name__ == "__main__":
    success = run_all_day3_tests()
    sys.exit(0 if success else 1)
