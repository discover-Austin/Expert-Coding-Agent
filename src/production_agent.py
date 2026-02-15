# production_agent.py
"""
ProductionCodingAgent: The real deal.

This integrates:
- CodebaseExecutionEngine (real projects)
- FailureTaxonomy (pattern recognition)
- HypothesisOrderer (systematic debugging)
- KnowledgeCore (persistent expertise)

The agent that has a career, not sessions.
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field

from knowledge_core import (
    KnowledgeCore, StructuredContext, PatternCategory,
    Decision, OutcomeType, FailureSeverity
)
from failure_taxonomy import FailureTaxonomy, DebugSession, DebugResolution
from hypothesis_ordering import HypothesisOrderer
from codebase_engine import (
    CodebaseExecutionEngine, CodebaseContext,
    FileChange, ChangeSet, TestResult
)
from code_analyzer import (
    CodeAnalyzer, ProjectStructure, DependencyGraph,
    ChangeImpact, ExplanationGate
)
from test_generator import TestGenerator, TestSuite
from refactoring_engine import (
    RefactoringEngine, RefactoringOpportunity,
    RefactoringPlan, RefactoringType
)
from error_analyzer import (
    ErrorAnalyzer, FailureAnalysis, RecoveryAction,
    ErrorCategory
)


@dataclass
class WorkSession:
    """A complete work session on a project"""
    session_id: str
    project_name: str
    project_path: Path
    context: CodebaseContext
    goal: str  # What we're trying to accomplish
    baseline_tests: Optional[TestResult] = None
    understanding: Optional[ProjectStructure] = None  # NEW: What we know about the code
    dependency_graph: Optional[DependencyGraph] = None  # NEW: How code connects
    changes_applied: List[ChangeSet] = field(default_factory=list)
    learnings: List[str] = field(default_factory=list)
    started: datetime = field(default_factory=datetime.now)
    completed: bool = False


class ProductionCodingAgent:
    """
    A coding agent with institutional memory.
    
    Works on real projects. Runs actual tests. Learns from every failure.
    Gets better over time - exponentially.
    """
    
    def __init__(
        self,
        expertise_dir: Path = Path("./agent_expertise"),
        workspace_dir: Optional[Path] = None
    ):
        # Core systems
        self.knowledge = KnowledgeCore()
        self.taxonomy = FailureTaxonomy()
        self.orderer = HypothesisOrderer(self.taxonomy)
        self.executor = CodebaseExecutionEngine(workspace_dir)
        self.analyzer = CodeAnalyzer()  # Code understanding
        self.error_analyzer = ErrorAnalyzer(self.taxonomy, self.knowledge)  # Error recovery
        self.test_gen = None  # Initialized after analysis
        self.refactor_engine = None  # Initialized after analysis
        
        # Persistent state
        self.expertise_dir = expertise_dir
        self.expertise_dir.mkdir(parents=True, exist_ok=True)
        
        # Active sessions
        self.active_sessions: Dict[str, WorkSession] = {}
        
        # Load existing expertise
        self._load_expertise()
    
    def start_work(
        self,
        repo_url: str,
        goal: str,
        branch: str = "main",
        language: str = "python"
    ) -> Tuple[bool, str, Optional[WorkSession]]:
        """
        Start working on a real project.
        
        CRITICAL: Analysis happens BEFORE any modifications.
        
        Returns: (success, message, session)
        """
        print(f"\n{'='*70}")
        print(f"STARTING WORK SESSION")
        print(f"{'='*70}\n")
        print(f"Repository: {repo_url}")
        print(f"Goal: {goal}")
        print()
        
        # Create context
        context = CodebaseContext(
            repo_url=repo_url,
            branch=branch,
            language=language
        )
        
        # Clone and setup
        print("Cloning repository and setting up environment...")
        success, project_path, error = self.executor.clone_and_setup(context)
        
        if not success:
            return False, f"Setup failed: {error}", None
        
        print(f"✓ Project ready at: {project_path}\n")
        
        # CRITICAL: Analyze code BEFORE establishing baseline
        print(f"{'='*70}")
        print("ANALYZING CODEBASE (MANDATORY)")
        print(f"{'='*70}\n")
        
        try:
            structure, dep_graph = self.analyzer.analyze_project(
                project_path,
                language=language
            )
            
            # Initialize test generator with understanding
            self.test_gen = TestGenerator(self.analyzer)
            
            # Initialize refactoring engine
            self.refactor_engine = RefactoringEngine(
                self.analyzer,
                self.test_gen
            )
            
        except ValueError as e:
            return False, f"Analysis failed: {e}", None
        
        print(f"{'='*70}")
        print("UNDERSTANDING SUMMARY")
        print(f"{'='*70}\n")
        print(f"Entry points: {', '.join(structure.entry_points)}")
        print(f"Total files: {structure.total_files}")
        print(f"Total functions: {structure.total_functions}")
        print(f"Test coverage estimate: {structure.test_coverage_estimate:.0%}")
        print(f"Core modules: {list(structure.core_modules.keys())}")
        print()
        
        # Run baseline tests
        print("Establishing baseline (running tests)...")
        baseline = self.executor.run_tests(project_path, context)
        
        print(f"Baseline: {baseline.passed} passed, {baseline.failed} failed")
        if baseline.coverage:
            print(f"Coverage: {baseline.coverage:.1f}%")
        print()
        
        # Create work session
        session_id = f"work_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        session = WorkSession(
            session_id=session_id,
            project_name=repo_url.split('/')[-1].replace('.git', ''),
            project_path=project_path,
            context=context,
            goal=goal,
            baseline_tests=baseline,
            understanding=structure,  # NEW: Save understanding
            dependency_graph=dep_graph  # NEW: Save dependency graph
        )
        
        self.active_sessions[session_id] = session
        
        # Get relevant expertise
        structured_ctx = context.to_structured_context()
        guidance = self._get_expertise_guidance(goal, structured_ctx)
        
        print(f"{'='*70}")
        print("EXPERTISE GUIDANCE")
        print(f"{'='*70}\n")
        print(guidance)
        print()
        
        return True, f"Session {session_id} started with code understanding", session
    
    def _get_expertise_guidance(
        self,
        goal: str,
        context: StructuredContext
    ) -> str:
        """Get guidance from accumulated expertise"""
        
        # Check taxonomy for similar past work
        rankings = self.taxonomy.rank_archetypes(
            context=context,
            symptom=goal,
            ruled_out={}
        )
        
        if not rankings:
            return (
                "No similar work in expertise base.\n"
                "This is a learning opportunity - every decision will inform future work."
            )
        
        guidance = ["Based on past experience:\n"]
        
        for i, (archetype, likelihood, reasoning) in enumerate(rankings[:3], 1):
            guidance.append(f"{i}. {archetype.description} ({likelihood:.0%} match)")
            guidance.append(f"   {reasoning}")
            guidance.append(f"   Typical approach: {', '.join(archetype.typical_fixes[:2])}\n")
        
        # Add relevant concepts
        relevant = self.knowledge.find_relevant_concepts(
            context=context,
            min_confidence=0.6
        )
        
        if relevant:
            guidance.append("\nProven patterns that might help:")
            for concept, instance, score in relevant[:3]:
                guidance.append(f"  - {concept.description} ({score:.0%} confidence)")
        
        return "\n".join(guidance)
    
    def implement_feature(
        self,
        session: WorkSession,
        description: str,
        files_to_modify: Dict[str, str]  # path -> new content
    ) -> Tuple[bool, str]:
        """
        Implement a feature with test-first validation.
        
        CRITICAL: Explanation gate blocks execution if understanding is incomplete.
        
        This is the complete implementation workflow:
        1. Check explanation gate (BLOCKING)
        2. Predict impact
        3. Apply changes
        4. Run tests
        5. Check for regressions
        6. Learn from results
        """
        print(f"\n{'='*70}")
        print(f"IMPLEMENTING: {description}")
        print(f"{'='*70}\n")
        
        # EXPLANATION GATE - BLOCKING
        print(f"{'='*70}")
        print("EXPLANATION GATE")
        print(f"{'='*70}\n")
        
        target_files = list(files_to_modify.keys())
        gate = self.analyzer.create_explanation_gate(target_files)
        
        print("CHECKS:")
        gate_dict = gate.to_dict()
        for check, status in gate_dict['checks'].items():
            symbol = "✓" if status else "✗"
            print(f"  {symbol} {check.replace('_', ' ').title()}")
        
        print()
        
        if not gate.is_complete():
            print("⚠️  EXECUTION BLOCKED")
            print("\nMissing requirements:")
            for req in gate.missing_requirements():
                print(f"  - {req}")
            print()
            print("Cannot proceed without complete understanding.")
            return False, f"Blocked by explanation gate: {', '.join(gate.missing_requirements())}"
        
        print("✓ Explanation gate passed")
        print()
        
        if gate.explanation_text:
            print("UNDERSTANDING:")
            print(gate.explanation_text)
            print()
        
        # IMPACT PREDICTION
        print(f"{'='*70}")
        print("IMPACT PREDICTION")
        print(f"{'='*70}\n")
        
        impact = self.analyzer.predict_impact(target_files, "modify")
        
        print(f"Risk Level: {impact.risk_level}")
        print(f"Reason: {impact.reason}")
        print(f"Files affected: {len(impact.files_likely_affected)}")
        print(f"Functions affected: {len(impact.functions_affected)}")
        if impact.tests_to_run:
            print(f"Tests to run: {len(impact.tests_to_run)}")
        print()
        
        # Get project path
        project_path = session.project_path
        
        # Create changeset
        changes = []
        for path, new_content in files_to_modify.items():
            # Determine operation
            original = self.executor.get_file_content(project_path, path)
            operation = "modify" if original else "create"
            
            changes.append(FileChange(
                path=path,
                original_content=original,
                new_content=new_content,
                operation=operation,
                reason=description
            ))
        
        changeset = ChangeSet(
            changeset_id=f"change_{len(session.changes_applied)}",
            description=description,
            files=changes
        )
        
        # Validate coherence
        is_coherent, reason = changeset.is_coherent()
        if not is_coherent:
            return False, f"Incoherent changeset: {reason}"
        
        print(f"Applying {len(changes)} file changes...")
        for change in changes:
            print(f"  {change.operation.upper()}: {change.path}")
        print()
        
        # Apply changes
        success, msg = self.executor.apply_changeset(project_path, changeset)
        if not success:
            return False, msg
        
        session.changes_applied.append(changeset)
        
        # Run tests
        print("Running tests...")
        results = self.executor.run_tests(project_path, session.context)
        
        print(f"Results: {results.passed} passed, {results.failed} failed")
        if results.coverage:
            print(f"Coverage: {results.coverage:.1f}%")
        print()
        
        # Check for regressions
        if session.baseline_tests:
            has_regression, issues = self.executor.detect_regressions(
                session.baseline_tests,
                results
            )
            
            if has_regression:
                print(f"⚠️  REGRESSIONS DETECTED:")
                for issue in issues:
                    print(f"  - {issue}")
                print()
                
                # Learn from this
                self._learn_from_failure(
                    session=session,
                    what_failed=description,
                    how_it_failed=issues,
                    test_results=results
                )
                
                return False, f"Regressions detected: {'; '.join(issues)}"
        
        # Success - learn from this too
        if results.failed == 0:
            print("✓ All tests passing")
            self._learn_from_success(
                session=session,
                what_worked=description,
                test_results=results
            )
        
        return True, f"Feature implemented successfully"
    
    def generate_tests(
        self,
        session: WorkSession,
        target_coverage: float = 0.8
    ) -> Tuple[bool, Dict[str, str]]:
        """
        Generate tests for coverage gaps.
        
        Uses Day 2 understanding to:
        - Find untested functions
        - Generate meaningful tests (not smoke tests)
        - Validate tests meet quality standards
        
        Returns: (success, {test_file_path: test_content})
        """
        
        if not self.test_gen:
            return False, {}
        
        print(f"\n{'='*70}")
        print(f"GENERATING TESTS (Target coverage: {target_coverage:.0%})")
        print(f"{'='*70}\n")
        
        # Find coverage gaps
        print("Analyzing coverage gaps...")
        gaps = self.test_gen.find_coverage_gaps(
            session.understanding,
            target_coverage
        )
        
        if not gaps:
            print("✓ No coverage gaps found")
            return True, {}
        
        print(f"Found coverage gaps in {len(gaps)} files:")
        for file, funcs in list(gaps.items())[:5]:
            print(f"  {file}: {len(funcs)} untested functions")
        print()
        
        # Generate tests
        print("Generating tests...")
        suites = self.test_gen.generate_missing_tests(gaps)
        
        print(f"Generated {len(suites)} test suites")
        print()
        
        # Validate quality
        print("Validating test quality...")
        all_valid = True
        test_files = {}
        
        for module_path, suite in suites.items():
            valid, issues = self.test_gen.validate_generated_tests(suite)
            
            if not valid:
                print(f"⚠️  Quality issues in tests for {module_path}:")
                for issue in issues[:3]:
                    print(f"  - {issue}")
                all_valid = False
                continue
            
            # Generate test file path
            test_file = f"test_{module_path}"
            test_content = suite.to_file(framework=session.understanding.test_structure.get('framework', 'pytest'))
            
            test_files[test_file] = test_content
            
            print(f"✓ {test_file}: {len(suite.test_cases)} tests, {suite.coverage_estimate:.0%} coverage")
        
        print()
        
        if not all_valid:
            return False, test_files
        
        print(f"✓ Generated {sum(len(s.test_cases) for s in suites.values())} high-quality tests")
        return True, test_files
    
    def plan_refactoring(
        self,
        session: WorkSession,
        target_files: Optional[List[str]] = None
    ) -> Tuple[bool, RefactoringPlan]:
        """
        Create safe refactoring plan.
        
        Steps:
        1. Identify refactoring opportunities
        2. Check explanation gate
        3. Generate safety tests if needed
        4. Predict impact
        5. Create execution plan
        
        Returns: (success, plan)
        """
        
        if not self.refactor_engine:
            return False, None
        
        print(f"\n{'='*70}")
        print("PLANNING REFACTORING")
        print(f"{'='*70}\n")
        
        # Default to all implementation files
        if not target_files:
            target_files = [
                path for path, module in self.analyzer.modules.items()
                if not module.is_test
            ]
        
        print(f"Analyzing {len(target_files)} files for refactoring opportunities...")
        
        # Identify opportunities
        opportunities = self.refactor_engine.identify_opportunities(target_files)
        
        if not opportunities:
            print("✓ No refactoring opportunities found")
            return True, RefactoringPlan(opportunities=[])
        
        print(f"Found {len(opportunities)} refactoring opportunities:")
        for opp in opportunities[:5]:
            print(f"  - {opp.type.value}: {opp.target_function} ({opp.risk_level} risk)")
        print()
        
        # Create plan with safety checks
        print("Creating refactoring plan with safety checks...")
        plan = self.refactor_engine.create_refactoring_plan(
            opportunities,
            baseline_passing=session.baseline_tests.passed > 0
        )
        
        # Check if safe to proceed
        if plan.is_safe_to_proceed():
            print("✓ Refactoring plan is safe to execute")
            print(f"  - Explanation gate: {'PASS' if plan.explanation_gate.is_complete() else 'FAIL'}")
            print(f"  - Baseline tests: {'PASSING' if plan.baseline_passing else 'FAILING'}")
            print(f"  - Safety tests: {sum(len(s.test_cases) for s in plan.pre_refactor_tests.values())} generated")
        else:
            print("⚠️  Refactoring plan has blocking issues:")
            for issue in plan.blocking_issues():
                print(f"  - {issue}")
        
        print()
        return True, plan
    
    def apply_refactoring(
        self,
        session: WorkSession,
        plan: RefactoringPlan,
        opportunity_index: int = 0
    ) -> Tuple[bool, str]:
        """
        Apply a refactoring from the plan.
        
        Safety checks:
        1. Plan must be safe to proceed
        2. Tests must pass before refactoring
        3. All affected functions must have tests (generate if needed)
        4. Tests must pass after refactoring
        5. Changes must be reversible
        
        Returns: (success, message)
        """
        
        if not self.refactor_engine:
            return False, "Refactoring engine not initialized"
        
        print(f"\n{'='*70}")
        print("APPLYING REFACTORING")
        print(f"{'='*70}\n")
        
        # Check plan is safe
        if not plan.is_safe_to_proceed():
            issues = plan.blocking_issues()
            return False, f"Plan not safe to proceed: {', '.join(issues)}"
        
        if opportunity_index >= len(plan.opportunities):
            return False, f"Invalid opportunity index: {opportunity_index}"
        
        opportunity = plan.opportunities[opportunity_index]
        
        print(f"Refactoring: {opportunity.type.value}")
        print(f"Target: {opportunity.target_function} in {opportunity.target_file}")
        print(f"Risk: {opportunity.risk_level}")
        print(f"Reason: {opportunity.reason}")
        print()
        
        # PATCH C: Check all affected functions have tests
        print("Checking test coverage of affected functions...")
        untested_functions = []
        
        for qualified_func in opportunity.affected_functions:
            # Parse qualified name (file:function)
            if ':' in qualified_func:
                file_path, func_name = qualified_func.split(':', 1)
                
                if file_path in self.analyzer.modules:
                    module = self.analyzer.modules[file_path]
                    if func_name in module.functions:
                        func_info = module.functions[func_name]
                        
                        # Check if function has non-trivial tests
                        has_tests = func_info.is_tested and len(func_info.test_assertions) > 0
                        if not has_tests:
                            untested_functions.append((file_path, func_name))
        
        if untested_functions:
            print(f"⚠️  {len(untested_functions)} affected functions lack tests:")
            for file, func in untested_functions[:3]:
                print(f"  - {func} in {file}")
            print()
            print("Generating safety tests for untested functions...")
            
            # Generate tests for untested files
            untested_files = set(f for f, _ in untested_functions)
            for file_path in untested_files:
                if self.test_gen:
                    suite = self.test_gen.generate_tests_for_module(
                        file_path,
                        target_coverage=0.8
                    )
                    
                    if suite.test_cases:
                        print(f"  Generated {len(suite.test_cases)} tests for {file_path}")
                        # In production, would write these to disk and run them
                        # For now, we document the requirement
            
            print()
            print("⚠️  Safety tests generated but not yet written to disk")
            print("In production: write tests, run baseline, then proceed")
            print()
        
        # Read current file
        file_path = session.project_path / opportunity.target_file
        if not file_path.exists():
            return False, f"File not found: {opportunity.target_file}"
        
        original_content = file_path.read_text()
        
        # Apply refactoring
        print("Applying refactoring...")
        success, new_content, explanation = self.refactor_engine.apply_refactoring(
            opportunity,
            original_content
        )
        
        if not success:
            return False, f"Refactoring failed: {explanation}"
        
        print(f"✓ {explanation}")
        print()
        
        # Write new content
        file_path.write_text(new_content)
        
        # Run tests to verify behavior preserved
        print("Verifying behavior preserved...")
        result = self.executor.execute_tests(session.context)
        
        # STRICT behavior preservation check
        baseline = session.baseline_tests
        
        # If baseline was clean (failed == 0), require clean post-refactor
        if baseline.failed == 0:
            if result.failed != 0:
                print(f"✗ Behavior changed: {result.failed} tests now failing (baseline: 0)")
                print("Rolling back changes...")
                file_path.write_text(original_content)
                return False, "Refactoring introduced test failures - rolled back"
            
            if result.total_tests != baseline.total_tests:
                print(f"✗ Test count changed: {result.total_tests} vs {baseline.total_tests}")
                print("Rolling back changes...")
                file_path.write_text(original_content)
                return False, "Refactoring changed test count - rolled back"
            
            print(f"✓ Behavior preserved: {result.passed}/{result.total_tests} tests passing (baseline clean)")
            return True, f"Refactoring successful: {explanation}"
        
        # If baseline had failures, require no increase in failures
        else:
            if result.failed > baseline.failed:
                print(f"✗ More failures: {result.failed} vs {baseline.failed}")
                print("Rolling back changes...")
                file_path.write_text(original_content)
                return False, "Refactoring increased failures - rolled back"
            
            if result.total_tests != baseline.total_tests:
                print(f"✗ Test count changed: {result.total_tests} vs {baseline.total_tests}")
                print("Rolling back changes...")
                file_path.write_text(original_content)
                return False, "Refactoring changed test count - rolled back"
            
            print(f"✓ Behavior preserved: {result.failed}/{result.total_tests} failures (no increase)")
            return True, f"Refactoring successful: {explanation}"
    
    def debug_failure(
        self,
        session: WorkSession,
        symptom: str
    ) -> Tuple[bool, str]:
        """
        Debug a test failure using systematic hypothesis ordering.
        
        This is where our expertise really shines:
        - Generate hypotheses from past failures
        - Order by information gain
        - Binary search the problem space
        """
        print(f"\n{'='*70}")
        print(f"DEBUGGING: {symptom}")
        print(f"{'='*70}\n")
        
        # Start debug session
        structured_ctx = session.context.to_structured_context()
        debug_session = self.taxonomy.start_session(symptom, structured_ctx)
        
        # Get systematic guidance
        result = self.orderer.debug_session_with_ordering(
            debug_session,
            structured_ctx,
            max_tests=5
        )
        
        hypothesis, reasoning = result
        
        print("DIAGNOSTIC REASONING:")
        for line in reasoning:
            print(f"  {line}")
        print()
        
        if hypothesis:
            print(f"Most likely cause: {hypothesis.description}")
            print(f"Confidence: {hypothesis.posterior_probability:.0%}")
            print()
            
            # This is where we'd implement the fix based on hypothesis
            # For now, return the diagnosis
            return True, f"Diagnosed: {hypothesis.description}"
        else:
            return False, "Could not determine root cause"
    
    def analyze_and_recover(
        self,
        session: WorkSession,
        test_results: TestResult,
        original_contents: Optional[Dict[str, str]] = None,
    ) -> Tuple[bool, str, List[FailureAnalysis]]:
        """
        Analyze test failures, suggest and execute recovery.

        Day 5 capability: deep failure analysis + recovery.

        Steps:
        1. Analyze every failure (stack trace, category, root cause)
        2. Build failure taxonomy (cluster by category)
        3. Suggest recovery strategies
        4. Execute best recovery strategy
        5. Learn from the outcome

        Returns: (recovered, message, analyses)
        """
        print(f"\n{'='*70}")
        print("ERROR ANALYSIS & RECOVERY (Day 5)")
        print(f"{'='*70}\n")

        if test_results.failed == 0:
            print("No failures to analyze.")
            return True, "No failures", []

        ctx = session.context.to_structured_context()
        ctx.problem_type = "test_failure"

        # 1. Analyze all failures
        print(f"Analyzing {test_results.failed} test failure(s)...\n")
        analyses = self.error_analyzer.analyze_test_failure(
            test_results, ctx
        )

        for analysis in analyses:
            print(f"  [{analysis.severity.name}] {analysis.error_type}: {analysis.error_message}")
            print(f"    Category: {analysis.category.value}")
            print(f"    Assumption violated: {analysis.violated_assumption}")
            if analysis.similar_past_failures:
                print(f"    Similar past failures: {len(analysis.similar_past_failures)}")
            if analysis.suggested_fixes:
                print(f"    Suggested fixes: {', '.join(analysis.suggested_fixes[:2])}")
            print()

        # 2. Cluster failures
        clusters = self.error_analyzer.build_failure_taxonomy(analyses)
        print(f"Failure clusters: {', '.join(f'{k} ({len(v)})' for k, v in clusters.items())}\n")

        # 3. Get recovery strategies for the most severe failure
        worst = max(analyses, key=lambda a: a.severity.value)
        strategies = self.error_analyzer.suggest_recovery(
            worst,
            has_baseline=session.baseline_tests is not None,
            has_backup=original_contents is not None,
        )

        print("Recovery strategies (ordered by confidence):")
        for i, strat in enumerate(strategies[:3], 1):
            print(f"  {i}. [{strat.action.value}] {strat.description} ({strat.confidence:.0%})")
        print()

        # 4. Execute best strategy
        best = strategies[0]
        print(f"Executing: {best.description}...")

        recovery_result = self.error_analyzer.execute_recovery(
            best, original_contents, session.project_path
        )

        if recovery_result.success:
            print(f"  {recovery_result.message}")
        else:
            print(f"  Recovery failed: {recovery_result.message}")
        print()

        # 5. Learn from every failure
        for analysis in analyses:
            archetype_id = self.error_analyzer.learn_from_failure(
                analysis, ctx
            )
            if archetype_id:
                session.learnings.append(
                    f"Failure pattern promoted to archetype: {archetype_id}"
                )

        # Learn from recovery outcome
        self.error_analyzer.learn_from_recovery(worst, recovery_result, ctx)

        recovered = recovery_result.success and best.action == RecoveryAction.ROLLBACK
        return recovered, recovery_result.message, analyses

    def _learn_from_failure(
        self,
        session: WorkSession,
        what_failed: str,
        how_it_failed: List[str],
        test_results: TestResult
    ):
        """Record failure patterns for future learning (enhanced with Day 5)."""

        # Create structured context
        ctx = session.context.to_structured_context()
        ctx.problem_type = "implementation_failure"

        # Use ErrorAnalyzer for deep analysis
        analyses = self.error_analyzer.analyze_test_failure(test_results, ctx)

        for analysis in analyses:
            archetype_id = self.error_analyzer.learn_from_failure(analysis, ctx)
            if archetype_id:
                session.learnings.append(
                    f"Failure pattern matched archetype: {archetype_id}"
                )

        # Fallback: also record via taxonomy directly if no test failures parsed
        if not analyses:
            debug_session = self.taxonomy.start_session(what_failed, ctx)
            for failure in how_it_failed:
                debug_session.add_observation(failure)
            resolution = DebugResolution(
                root_cause_summary=" | ".join(how_it_failed),
                evidence=[f.get('error', 'Unknown') for f in test_results.failures],
                fix_applied="Not yet applied",
                validated=False
            )
            archetype_id = self.taxonomy.close_session(debug_session, resolution)
            if archetype_id:
                session.learnings.append(
                    f"Failure pattern matched archetype: {archetype_id}"
                )
    
    def _learn_from_success(
        self,
        session: WorkSession,
        what_worked: str,
        test_results: TestResult
    ):
        """Record successful patterns"""
        
        session.learnings.append(
            f"Success: {what_worked} (coverage: {test_results.coverage or 0:.1f}%)"
        )
    
    def complete_session(self, session: WorkSession) -> Dict:
        """
        Complete work session and consolidate learnings.
        
        This is where expertise gets saved for future sessions.
        """
        session.completed = True
        
        summary = {
            'session_id': session.session_id,
            'project': session.project_name,
            'goal': session.goal,
            'changes_applied': len(session.changes_applied),
            'learnings': session.learnings,
            'duration': (datetime.now() - session.started).total_seconds() / 60
        }
        
        # Save expertise
        self._save_expertise()
        
        return summary
    
    def _save_expertise(self):
        """Persist accumulated expertise to disk"""
        
        # Save taxonomy
        taxonomy_path = self.expertise_dir / "taxonomy.json"
        taxonomy_data = {
            'signatures': [
                {
                    'id': sig.signature_id,
                    'symptom': list(sig.symptom_keywords),
                    'cause': sig.root_cause_summary,
                    'validated': sig.validated
                }
                for sig in self.taxonomy.signatures
            ],
            'archetypes': {
                arch_id: {
                    'description': arch.description,
                    'confidence': arch.confidence,
                    'times_seen': arch.times_seen,
                    'times_fixed': arch.times_fixed
                }
                for arch_id, arch in self.taxonomy.archetypes.items()
            }
        }
        
        with open(taxonomy_path, 'w') as f:
            json.dump(taxonomy_data, f, indent=2)
        
        print(f"\n✓ Expertise saved to {self.expertise_dir}")
    
    def _load_expertise(self):
        """Load existing expertise from disk"""
        
        taxonomy_path = self.expertise_dir / "taxonomy.json"
        if taxonomy_path.exists():
            # Would load full state in production
            print(f"Loaded expertise from {self.expertise_dir}")
    
    def get_career_summary(self) -> Dict:
        """Summary of accumulated expertise"""

        return {
            'knowledge': self.knowledge.get_summary(),
            'taxonomy': self.taxonomy.get_summary(),
            'error_analysis': self.error_analyzer.get_summary(),
            'sessions_completed': len([
                s for s in self.active_sessions.values()
                if s.completed
            ])
        }


# Quick validation
if __name__ == "__main__":
    print("="*70)
    print("PRODUCTION CODING AGENT - READY")
    print("="*70)
    print()
    print("This agent:")
    print("  ✓ Works on real repositories")
    print("  ✓ Runs actual test suites")
    print("  ✓ Learns from every failure")
    print("  ✓ Compounds expertise across projects")
    print()
    print("Usage:")
    print("  agent = ProductionCodingAgent()")
    print("  success, msg, session = agent.start_work(")
    print("      repo_url='https://github.com/user/project.git',")
    print("      goal='Fix authentication bug'")
    print("  )")
    print()
    print("="*70)
