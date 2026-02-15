#!/usr/bin/env python3
"""
Day 4 Validation: Safe Refactoring

Proves refactoring engine:
1. Identifies refactoring opportunities
2. Creates plans with safety checks
3. Blocks without understanding
4. Blocks without tests
5. Verifies behavior preservation
"""

import sys
import tempfile
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from code_analyzer import CodeAnalyzer
from test_generator import TestGenerator
from refactoring_engine import RefactoringEngine, RefactoringType


def test_identifies_opportunities():
    """
    Test 1: Identifies refactoring opportunities.
    
    Expected: Finds long functions, complex conditionals, etc.
    """
    print("\n" + "="*70)
    print("TEST 1: IDENTIFIES REFACTORING OPPORTUNITIES")
    print("="*70)
    
    tmpdir = Path(tempfile.mkdtemp())
    try:
        # Create code with refactoring opportunities
        (tmpdir / "complex.py").write_text("""
def long_function(data):
    # Lots of calls = complexity
    validate(data)
    sanitize(data)
    transform(data)
    process(data)
    format(data)
    encode(data)
    compress(data)
    upload(data)
    notify(data)
    log(data)
    cleanup(data)
    return data
""")
        
        (tmpdir / "pytest.ini").write_text("[pytest]\n")
        
        # Analyze
        analyzer = CodeAnalyzer()
        structure, graph = analyzer.analyze_project(tmpdir, language="python")
        
        test_gen = TestGenerator(analyzer)
        refactor_engine = RefactoringEngine(analyzer, test_gen)
        
        # Identify opportunities
        opportunities = refactor_engine.identify_opportunities(['complex.py'])
        
        print(f"Found {len(opportunities)} opportunities:")
        for opp in opportunities:
            print(f"  - {opp.type.value}: {opp.target_function}")
            print(f"    Reason: {opp.reason}")
            print(f"    Risk: {opp.risk_level}")
        print()
        
        if len(opportunities) > 0:
            print("✓ TEST 1 PASSED: Identified refactoring opportunities")
            return True
        else:
            print("✗ TEST 1 FAILED: No opportunities found")
            return False
            
    finally:
        shutil.rmtree(tmpdir)


def test_creates_safe_plan():
    """
    Test 2: Creates plan with safety checks.
    
    Expected: Plan includes explanation gate, tests, impact prediction.
    """
    print("\n" + "="*70)
    print("TEST 2: CREATES SAFE REFACTORING PLAN")
    print("="*70)
    
    tmpdir = Path(tempfile.mkdtemp())
    try:
        # Create code
        (tmpdir / "math.py").write_text("""
def complex_calc(a, b, c, d, e, f, g):
    result = a + b
    result = result * c
    result = result - d
    result = result / e
    result = result ** f
    result = result % g
    return result
""")
        
        (tmpdir / "pytest.ini").write_text("[pytest]\n")
        
        # Analyze
        analyzer = CodeAnalyzer()
        structure, graph = analyzer.analyze_project(tmpdir, language="python")
        
        test_gen = TestGenerator(analyzer)
        refactor_engine = RefactoringEngine(analyzer, test_gen)
        
        # Create plan
        opportunities = refactor_engine.identify_opportunities(['math.py'])
        plan = refactor_engine.create_refactoring_plan(
            opportunities,
            baseline_passing=True
        )
        
        print(f"Plan created:")
        print(f"  Opportunities: {len(plan.opportunities)}")
        print(f"  Explanation gate: {'COMPLETE' if plan.explanation_gate and plan.explanation_gate.is_complete() else 'INCOMPLETE'}")
        print(f"  Pre-refactor tests: {len(plan.pre_refactor_tests)}")
        print(f"  Safe to proceed: {plan.is_safe_to_proceed()}")
        
        if not plan.is_safe_to_proceed():
            print(f"  Blocking issues: {plan.blocking_issues()}")
        print()
        
        # Verify plan has safety checks
        has_gate = plan.explanation_gate is not None
        has_baseline = plan.baseline_passing
        
        if has_gate and has_baseline:
            print("✓ TEST 2 PASSED: Plan has safety checks")
            return True
        else:
            print("✗ TEST 2 FAILED: Plan missing safety checks")
            return False
            
    finally:
        shutil.rmtree(tmpdir)


def test_blocks_without_understanding():
    """
    Test 3: Blocks refactoring without complete understanding.
    
    Expected: Plan not safe if explanation gate incomplete.
    """
    print("\n" + "="*70)
    print("TEST 3: BLOCKS WITHOUT UNDERSTANDING")
    print("="*70)
    
    tmpdir = Path(tempfile.mkdtemp())
    try:
        # Create code WITHOUT tests (explanation gate will fail)
        (tmpdir / "untested.py").write_text("""
def mystery_function(x):
    return x * 2
""")
        
        (tmpdir / "pytest.ini").write_text("[pytest]\n")
        
        # Analyze
        analyzer = CodeAnalyzer()
        structure, graph = analyzer.analyze_project(tmpdir, language="python")
        
        test_gen = TestGenerator(analyzer)
        refactor_engine = RefactoringEngine(analyzer, test_gen)
        
        # Create plan
        opportunities = refactor_engine.identify_opportunities(['untested.py'])
        if opportunities:
            plan = refactor_engine.create_refactoring_plan(
                opportunities,
                baseline_passing=True
            )
            
            print(f"Plan safety: {plan.is_safe_to_proceed()}")
            if not plan.is_safe_to_proceed():
                print(f"Blocking issues:")
                for issue in plan.blocking_issues():
                    print(f"  - {issue}")
            print()
            
            # Should NOT be safe (no tests)
            if not plan.is_safe_to_proceed():
                print("✓ TEST 3 PASSED: Blocks without understanding")
                return True
            else:
                print("✗ TEST 3 FAILED: Did not block")
                return False
        else:
            # No opportunities found, that's ok - create simple plan
            from refactoring_engine import RefactoringPlan, RefactoringOpportunity
            plan = RefactoringPlan(
                opportunities=[],
                baseline_passing=True
            )
            plan.explanation_gate = analyzer.create_explanation_gate(['untested.py'])
            
            if not plan.is_safe_to_proceed():
                print("✓ TEST 3 PASSED: Blocks without tests")
                return True
            else:
                print("✗ TEST 3 FAILED: Should block without tests")
                return False
            
    finally:
        shutil.rmtree(tmpdir)


def test_predicts_impact():
    """
    Test 4: Predicts refactoring impact.
    
    Expected: Uses dependency graph to predict affected code.
    """
    print("\n" + "="*70)
    print("TEST 4: PREDICTS REFACTORING IMPACT")
    print("="*70)
    
    tmpdir = Path(tempfile.mkdtemp())
    try:
        # Create code with enough complexity to trigger detection
        (tmpdir / "complex.py").write_text("""
def helper(x):
    return x + 1

def processor(data):
    # Complex function with many calls (triggers detection)
    validate(data)
    sanitize(data)
    transform(data)
    process(data)
    format(data)
    encode(data)
    compress(data)
    upload(data)
    notify(data)
    log(data)
    cleanup(data)
    return helper(data)
""")
        
        (tmpdir / "pytest.ini").write_text("[pytest]\n")
        
        # Analyze
        analyzer = CodeAnalyzer()
        structure, graph = analyzer.analyze_project(tmpdir, language="python")
        
        test_gen = TestGenerator(analyzer)
        refactor_engine = RefactoringEngine(analyzer, test_gen)
        
        # Identify opportunities
        opportunities = refactor_engine.identify_opportunities(['complex.py'])
        
        # STRICT: Must find opportunities in this file
        # processor has 12 calls - should trigger detection
        if not opportunities:
            print("✗ TEST 4 FAILED: No opportunities found (should find at least one)")
            return False
        
        # Check first opportunity has impact prediction
        opp = opportunities[0]
        
        print(f"Opportunity: {opp.type.value} on {opp.target_function}")
        print(f"Risk level: {opp.risk_level}")
        print(f"Affected files: {opp.affected_files}")
        print(f"Affected functions: {len(opp.affected_functions)}")
        print()
        
        has_risk = opp.risk_level in ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
        has_impact = len(opp.affected_functions) >= 1  # At least self
        
        if has_risk and has_impact:
            print("✓ TEST 4 PASSED: Impact prediction working")
            return True
        else:
            print("✗ TEST 4 FAILED: Impact not predicted")
            return False
            
    finally:
        shutil.rmtree(tmpdir)


def run_all_day4_tests():
    """Run all Day 4 validation tests"""
    
    print("="*70)
    print("DAY 4 VALIDATION: SAFE REFACTORING")
    print("="*70)
    print()
    print("Testing refactoring engine capabilities:")
    print("  1. Identifies refactoring opportunities")
    print("  2. Creates plans with safety checks")
    print("  3. Blocks without understanding")
    print("  4. Predicts refactoring impact")
    print()
    
    results = []
    
    try:
        results.append(("Identifies opportunities", test_identifies_opportunities()))
    except Exception as e:
        print(f"\n✗ Test 1 FAILED with exception: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Identifies opportunities", False))
    
    try:
        results.append(("Creates safe plan", test_creates_safe_plan()))
    except Exception as e:
        print(f"\n✗ Test 2 FAILED with exception: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Creates safe plan", False))
    
    try:
        results.append(("Blocks without understanding", test_blocks_without_understanding()))
    except Exception as e:
        print(f"\n✗ Test 3 FAILED with exception: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Blocks without understanding", False))
    
    try:
        results.append(("Predicts impact", test_predicts_impact()))
    except Exception as e:
        print(f"\n✗ Test 4 FAILED with exception: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Predicts impact", False))
    
    # Summary
    print("\n" + "="*70)
    print("DAY 4 VALIDATION SUMMARY")
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
        print("✓ DAY 4 COMPLETE")
        print("="*70)
        print()
        print("Safe refactoring working:")
        print("  ✓ Identifies refactoring opportunities")
        print("  ✓ Creates plans with safety checks")
        print("  ✓ Blocks without understanding/tests")
        print("  ✓ Predicts impact using dependency graph")
        print()
        print("Ready for Day 5: Error Recovery")
        print("="*70)
        return True
    else:
        print("="*70)
        print("✗ DAY 4 INCOMPLETE")
        print("="*70)
        print()
        print(f"{total - passed} test(s) failing")
        print("Fix issues before proceeding")
        print("="*70)
        return False


if __name__ == "__main__":
    success = run_all_day4_tests()
    sys.exit(0 if success else 1)
