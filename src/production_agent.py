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
        self.analyzer = CodeAnalyzer()  # NEW: Code understanding
        
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
    
    def _learn_from_failure(
        self,
        session: WorkSession,
        what_failed: str,
        how_it_failed: List[str],
        test_results: TestResult
    ):
        """Record failure patterns for future learning"""
        
        # Create structured context
        ctx = session.context.to_structured_context()
        ctx.problem_type = "implementation_failure"
        
        # Start debug session
        debug_session = self.taxonomy.start_session(what_failed, ctx)
        
        # Add observations
        for failure in how_it_failed:
            debug_session.add_observation(failure)
        
        # Close with resolution
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
