#!/usr/bin/env python3
"""
Verify Day 3 Patches: Real assertions, no comments, proper calls.

Tests Austin's audit points:
1. Assertions are executable (not comments)
2. Validator rejects comments
3. Function calls use proper args (not always func())
"""

import sys
import tempfile
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from code_analyzer import CodeAnalyzer
from test_generator import TestGenerator


def test_patch1_real_assertions():
    """
    Patch 1: Assertions must be executable.
    
    Verify generated tests have real assertions, not comments.
    """
    print("\n" + "="*70)
    print("PATCH 1: REAL ASSERTIONS (NO COMMENTS)")
    print("="*70)
    
    tmpdir = Path(tempfile.mkdtemp())
    try:
        # Create function
        (tmpdir / "math_ops.py").write_text("""
def add(a, b):
    return a + b
""")
        
        (tmpdir / "pytest.ini").write_text("[pytest]\n")
        
        # Analyze
        analyzer = CodeAnalyzer()
        structure, graph = analyzer.analyze_project(tmpdir, language="python")
        
        # Generate tests
        test_gen = TestGenerator(analyzer)
        suite = test_gen.generate_tests_for_module('math_ops.py')
        
        print(f"Generated {len(suite.test_cases)} tests\n")
        
        # Check: NO comments in assertions
        has_comments = False
        for test_case in suite.test_cases:
            print(f"Test: {test_case.name}")
            print(f"  Code: {test_case.test_code[:60]}...")
            print(f"  Assertions: {test_case.assertions}")
            
            for assertion in test_case.assertions:
                if assertion.strip().startswith('#'):
                    print(f"  ✗ COMMENT FOUND: {assertion}")
                    has_comments = True
        
        print()
        
        if has_comments:
            print("✗ PATCH 1 FAILED: Still generating comment assertions")
            return False
        else:
            print("✓ PATCH 1 VERIFIED: No comment assertions")
            return True
            
    finally:
        shutil.rmtree(tmpdir)


def test_patch2_validator_rejects_comments():
    """
    Patch 2: Validator must reject comments.
    
    Verify validation fails if assertions are comments.
    """
    print("\n" + "="*70)
    print("PATCH 2: VALIDATOR REJECTS COMMENTS")
    print("="*70)
    
    tmpdir = Path(tempfile.mkdtemp())
    try:
        (tmpdir / "dummy.py").write_text("def dummy(): pass")
        (tmpdir / "pytest.ini").write_text("[pytest]\n")
        
        analyzer = CodeAnalyzer()
        structure, graph = analyzer.analyze_project(tmpdir, language="python")
        test_gen = TestGenerator(analyzer)
        
        # Create test with comment assertion
        from test_generator import TestSuite, TestCase
        bad_suite = TestSuite(
            module_path="dummy.py",
            test_cases=[
                TestCase(
                    name="test_comment_assertion",
                    target_function="dummy",
                    test_type="unit",
                    test_code="dummy()",
                    assertions=["# Should work"],  # Comment!
                    rationale="Test with comment"
                )
            ]
        )
        
        # Validate
        valid, issues = test_gen.validate_generated_tests(bad_suite)
        
        print(f"Validation: {'PASS' if valid else 'FAIL (correct)'}")
        print(f"Issues: {len(issues)}")
        for issue in issues:
            print(f"  - {issue}")
        print()
        
        if valid:
            print("✗ PATCH 2 FAILED: Validator accepted comments")
            return False
        else:
            # Check that comment was specifically flagged
            comment_flagged = any('Comment instead of assertion' in issue for issue in issues)
            if comment_flagged:
                print("✓ PATCH 2 VERIFIED: Validator rejects comments")
                return True
            else:
                print("✗ PATCH 2 FAILED: Comment not specifically detected")
                return False
            
    finally:
        shutil.rmtree(tmpdir)


def test_patch3_proper_function_calls():
    """
    Patch 3: Function calls use proper args.
    
    Verify generated tests call functions with args, not always func().
    """
    print("\n" + "="*70)
    print("PATCH 3: PROPER FUNCTION CALLS")
    print("="*70)
    
    tmpdir = Path(tempfile.mkdtemp())
    try:
        # Create function WITH PARAMETERS
        (tmpdir / "user.py").write_text("""
def create_user(username, email, age):
    return {'username': username, 'email': email, 'age': age}
""")
        
        (tmpdir / "pytest.ini").write_text("[pytest]\n")
        
        # Analyze
        analyzer = CodeAnalyzer()
        structure, graph = analyzer.analyze_project(tmpdir, language="python")
        
        # Generate tests
        test_gen = TestGenerator(analyzer)
        suite = test_gen.generate_tests_for_module('user.py')
        
        print(f"Generated {len(suite.test_cases)} tests\n")
        
        # Check: Function calls should have args
        uses_proper_args = False
        for test_case in suite.test_cases:
            print(f"Test: {test_case.name}")
            print(f"  Code: {test_case.test_code}")
            
            # Check if it calls create_user with args
            if 'create_user(' in test_case.test_code:
                if 'create_user()' in test_case.test_code:
                    print("  ✗ NO ARGS: Still calling create_user()")
                else:
                    print("  ✓ HAS ARGS: Calling with parameters")
                    uses_proper_args = True
        
        print()
        
        if uses_proper_args:
            print("✓ PATCH 3 VERIFIED: Generates calls with args")
            return True
        else:
            print("✗ PATCH 3 FAILED: Still calling func() without args")
            return False
            
    finally:
        shutil.rmtree(tmpdir)


def run_patch_verification():
    """Run all patch verification tests"""
    
    print("="*70)
    print("DAY 3 PATCH VERIFICATION")
    print("="*70)
    print()
    print("Verifying Austin's required patches:")
    print("  1. Assertions are executable (not comments)")
    print("  2. Validator rejects comments")
    print("  3. Function calls use proper args")
    print()
    
    results = []
    
    try:
        results.append(("Patch 1: Real assertions", test_patch1_real_assertions()))
    except Exception as e:
        print(f"\n✗ Patch 1 FAILED with exception: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Patch 1: Real assertions", False))
    
    try:
        results.append(("Patch 2: Validator rejects comments", test_patch2_validator_rejects_comments()))
    except Exception as e:
        print(f"\n✗ Patch 2 FAILED with exception: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Patch 2: Validator rejects comments", False))
    
    try:
        results.append(("Patch 3: Proper function calls", test_patch3_proper_function_calls()))
    except Exception as e:
        print(f"\n✗ Patch 3 FAILED with exception: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Patch 3: Proper function calls", False))
    
    # Summary
    print("\n" + "="*70)
    print("PATCH VERIFICATION SUMMARY")
    print("="*70)
    print()
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        symbol = "✓" if result else "✗"
        print(f"{symbol} {name}")
    
    print()
    print(f"Results: {passed}/{total} patches verified")
    print()
    
    if passed == total:
        print("="*70)
        print("✓ ALL PATCHES VERIFIED")
        print("="*70)
        print()
        print("Day 3 fixes complete:")
        print("  ✓ No comment assertions")
        print("  ✓ Validator rejects comments")
        print("  ✓ Proper function calls with args")
        print()
        print("Ready to ship.")
        print("="*70)
        return True
    else:
        print("="*70)
        print("✗ PATCHES INCOMPLETE")
        print("="*70)
        print()
        print(f"{total - passed} patch(es) not working")
        print("Fix before shipping")
        print("="*70)
        return False


if __name__ == "__main__":
    success = run_patch_verification()
    sys.exit(0 if success else 1)
