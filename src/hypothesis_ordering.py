# hypothesis_ordering.py
"""
Hypothesis Ordering: The layer that makes debugging collapse from hours to minutes.

Core insight: Not all hypotheses are equally informative.
A good debugger doesn't guess randomly - they binary search the problem space.

This module implements:
- Information gain calculation
- Hypothesis entropy reduction
- Optimal next test selection
- Stop conditions based on confidence
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict
import math

from failure_taxonomy import DebugSession, RootCauseArchetype, FailureTaxonomy
from knowledge_core import StructuredContext


@dataclass
class Hypothesis:
    """A testable theory about what's wrong"""
    description: str
    assumptions: List[str]
    confirming_signals: List[str]  # What would prove this true
    invalidating_signals: List[str]  # What would prove this false
    prior_probability: float = 0.5  # Before any testing
    posterior_probability: float = 0.5  # After observations
    related_archetypes: List[str] = field(default_factory=list)
    

@dataclass
class DiagnosticTest:
    """A test we can run to gather information"""
    test_id: str
    description: str
    code: str
    expected_if_hypothesis_true: Dict[str, str]  # hypothesis_id -> expected output
    expected_if_hypothesis_false: Dict[str, str]
    information_gain: float = 0.0
    cost: float = 1.0  # Execution time, complexity, etc.


class HypothesisOrderer:
    """
    Orders hypotheses by information gain, not random guessing.
    
    This is how senior engineers debug:
    1. Generate hypotheses from symptoms + archetypes
    2. Calculate which test eliminates the most uncertainty
    3. Run that test
    4. Update beliefs based on evidence
    5. Repeat until confident
    """
    
    def __init__(self, taxonomy: FailureTaxonomy):
        self.taxonomy = taxonomy
        
    def generate_hypotheses(
        self,
        session: DebugSession,
        context: StructuredContext
    ) -> List[Hypothesis]:
        """
        Generate ranked hypotheses from:
        - Known archetypes (high prior probability)
        - Common failure modes (medium prior)
        - Generic possibilities (low prior)
        """
        
        hypotheses = []
        
        # Get relevant archetypes
        ranked_archetypes = self.taxonomy.rank_archetypes(
            context=context,
            symptom=session.initial_symptom,
            ruled_out=session.ruled_out
        )
        
        # Create hypotheses from archetypes (high prior)
        for archetype, score, reasoning in ranked_archetypes[:5]:
            hypotheses.append(Hypothesis(
                description=archetype.description,
                assumptions=archetype.preconditions,
                confirming_signals=archetype.confirming_signals,
                invalidating_signals=archetype.invalidated_by,
                prior_probability=score,  # Use archetype match score
                posterior_probability=score,
                related_archetypes=[archetype.archetype_id]
            ))
        
        # Add generic hypotheses if we don't have strong archetype matches
        if not ranked_archetypes or ranked_archetypes[0][1] < 0.5:
            generic = self._generic_hypotheses_for_context(context)
            hypotheses.extend(generic)
        
        return hypotheses
    
    def _generic_hypotheses_for_context(
        self,
        context: StructuredContext
    ) -> List[Hypothesis]:
        """Generic hypotheses based on problem type"""
        
        generic_map = {
            'concurrency': [
                Hypothesis(
                    description="Race condition in shared state",
                    assumptions=["Multiple threads/processes", "Shared mutable state"],
                    confirming_signals=["Non-deterministic failures", "Works with single thread"],
                    invalidating_signals=["Deterministic failure", "Fails in single-threaded mode"],
                    prior_probability=0.3
                ),
                Hypothesis(
                    description="Deadlock in resource acquisition",
                    assumptions=["Multiple locks", "Circular dependency"],
                    confirming_signals=["System hangs", "No progress"],
                    invalidating_signals=["System crashes", "Gets wrong result but completes"],
                    prior_probability=0.2
                )
            ],
            'networking': [
                Hypothesis(
                    description="Timeout due to slow upstream",
                    assumptions=["Network dependency", "No local timeout set"],
                    confirming_signals=["Failure after delay", "Works with longer timeout"],
                    invalidating_signals=["Fails immediately", "No network calls observed"],
                    prior_probability=0.3
                ),
                Hypothesis(
                    description="Connection pool exhaustion",
                    assumptions=["Connection pooling", "Connections not released"],
                    confirming_signals=["Fails under load", "Connection count grows"],
                    invalidating_signals=["Fails with single connection", "Connection count stable"],
                    prior_probability=0.2
                )
            ],
            'validation': [
                Hypothesis(
                    description="Input validation missing or incorrect",
                    assumptions=["Accepts user input", "Validation logic exists"],
                    confirming_signals=["Fails with specific input", "Works with sanitized input"],
                    invalidating_signals=["Fails with all inputs", "Validation not reached"],
                    prior_probability=0.4
                )
            ]
        }
        
        return generic_map.get(context.problem_type, [])
    
    def calculate_information_gain(
        self,
        test: DiagnosticTest,
        hypotheses: List[Hypothesis]
    ) -> float:
        """
        Calculate how much uncertainty this test eliminates.
        
        Information gain = Current entropy - Expected entropy after test
        
        Higher is better - we want tests that eliminate the most uncertainty.
        """
        
        # Current entropy (uncertainty about which hypothesis is true)
        current_entropy = self._calculate_entropy(hypotheses)
        
        # Expected entropy after test
        # For each possible outcome, calculate resulting entropy
        
        # Simplified: assume test confirms or refutes each hypothesis
        expected_entropy = 0.0
        
        for hyp in hypotheses:
            # Probability test confirms this hypothesis
            p_confirm = hyp.posterior_probability
            
            # If confirmed, entropy among remaining hypotheses
            if p_confirm > 0:
                remaining_if_confirm = [h for h in hypotheses if h != hyp or h.posterior_probability > 0]
                entropy_if_confirm = self._calculate_entropy(remaining_if_confirm)
                expected_entropy += p_confirm * entropy_if_confirm
            
            # If refuted
            p_refute = 1 - p_confirm
            if p_refute > 0:
                remaining_if_refute = [h for h in hypotheses if h != hyp]
                entropy_if_refute = self._calculate_entropy(remaining_if_refute)
                expected_entropy += p_refute * entropy_if_refute
        
        information_gain = current_entropy - expected_entropy
        
        return max(0, information_gain)
    
    def _calculate_entropy(self, hypotheses: List[Hypothesis]) -> float:
        """Shannon entropy of hypothesis distribution"""
        if not hypotheses:
            return 0.0
        
        # Normalize probabilities
        total_prob = sum(h.posterior_probability for h in hypotheses)
        if total_prob == 0:
            return 0.0
        
        entropy = 0.0
        for hyp in hypotheses:
            p = hyp.posterior_probability / total_prob
            if p > 0:
                entropy -= p * math.log2(p)
        
        return entropy
    
    def select_next_test(
        self,
        session: DebugSession,
        hypotheses: List[Hypothesis],
        available_tests: List[DiagnosticTest]
    ) -> Optional[DiagnosticTest]:
        """
        Select the test with highest information gain / cost ratio.
        
        This is the key decision: what to test next.
        """
        
        if not hypotheses or not available_tests:
            return None
        
        best_test = None
        best_score = -float('inf')
        
        for test in available_tests:
            info_gain = self.calculate_information_gain(test, hypotheses)
            
            # Score = information gain / cost
            # We want high information gain, low cost
            score = info_gain / max(test.cost, 0.1)
            
            if score > best_score:
                best_score = score
                best_test = test
        
        return best_test
    
    def update_beliefs(
        self,
        hypotheses: List[Hypothesis],
        test_result: str,
        test: DiagnosticTest
    ) -> List[Hypothesis]:
        """
        Bayesian update: adjust hypothesis probabilities based on test outcome.
        
        P(H|E) = P(E|H) * P(H) / P(E)
        """
        
        for hyp_id, expected in test.expected_if_hypothesis_true.items():
            # Find matching hypothesis
            matching_hyp = None
            for hyp in hypotheses:
                if hyp.description == hyp_id or any(
                    arch in hyp.related_archetypes for arch in [hyp_id]
                ):
                    matching_hyp = hyp
                    break
            
            if not matching_hyp:
                continue
            
            # Simple likelihood update
            if expected.lower() in test_result.lower():
                # Test confirms this hypothesis
                matching_hyp.posterior_probability *= 1.5
            else:
                # Test refutes this hypothesis
                matching_hyp.posterior_probability *= 0.3
        
        # Normalize probabilities
        total = sum(h.posterior_probability for h in hypotheses)
        if total > 0:
            for hyp in hypotheses:
                hyp.posterior_probability /= total
        
        return hypotheses
    
    def should_stop(
        self,
        hypotheses: List[Hypothesis],
        confidence_threshold: float = 0.8
    ) -> Tuple[bool, Optional[Hypothesis]]:
        """
        Decide if we have enough confidence to stop testing.
        
        Returns: (should_stop, best_hypothesis)
        """
        
        if not hypotheses:
            return True, None
        
        # Find highest confidence hypothesis
        best = max(hypotheses, key=lambda h: h.posterior_probability)
        
        # Stop if we're confident enough
        if best.posterior_probability >= confidence_threshold:
            return True, best
        
        # Also stop if entropy is very low (we're certain, just not super confident)
        entropy = self._calculate_entropy(hypotheses)
        if entropy < 0.5:  # Low uncertainty
            return True, best
        
        return False, None
    
    def debug_session_with_ordering(
        self,
        session: DebugSession,
        context: StructuredContext,
        max_tests: int = 10
    ) -> Tuple[Optional[Hypothesis], List[str]]:
        """
        Complete debugging session with optimal hypothesis ordering.
        
        Returns: (final_hypothesis, reasoning_trace)
        """
        
        reasoning = []
        
        # Generate initial hypotheses
        hypotheses = self.generate_hypotheses(session, context)
        reasoning.append(f"Generated {len(hypotheses)} hypotheses from archetypes and context")
        
        if not hypotheses:
            reasoning.append("No hypotheses generated - insufficient information")
            return None, reasoning
        
        # Show initial state
        reasoning.append(f"Initial entropy: {self._calculate_entropy(hypotheses):.2f}")
        for i, hyp in enumerate(sorted(hypotheses, key=lambda h: h.prior_probability, reverse=True)[:3], 1):
            reasoning.append(f"  {i}. {hyp.description}: {hyp.prior_probability:.1%}")
        
        # Iterative hypothesis testing
        for iteration in range(max_tests):
            # Check if we should stop
            should_stop, best_hyp = self.should_stop(hypotheses)
            if should_stop:
                if best_hyp:
                    reasoning.append(f"\n✓ Confident conclusion after {iteration} tests")
                    reasoning.append(f"  Root cause: {best_hyp.description}")
                    reasoning.append(f"  Confidence: {best_hyp.posterior_probability:.1%}")
                    return best_hyp, reasoning
                else:
                    reasoning.append(f"\n⚠️ No confident hypothesis after {iteration} tests")
                    return None, reasoning
            
            # This would integrate with actual test generation
            # For now, just show what the next optimal test would be
            reasoning.append(f"\nIteration {iteration + 1}:")
            reasoning.append(f"  Current best: {hypotheses[0].description} ({hypotheses[0].posterior_probability:.1%})")
            reasoning.append(f"  Entropy: {self._calculate_entropy(hypotheses):.2f}")
            
            # In real usage, would:
            # 1. Generate diagnostic tests for remaining hypotheses
            # 2. Select test with highest information gain
            # 3. Execute test
            # 4. Update beliefs based on result
            # 5. Repeat
            
            break  # Placeholder - would continue with actual test execution
        
        reasoning.append("\nMax iterations reached")
        best = max(hypotheses, key=lambda h: h.posterior_probability)
        return best, reasoning


def demo_hypothesis_ordering():
    """Demonstrate hypothesis ordering on the race condition domain"""
    
    from failure_taxonomy import FailureTaxonomy
    
    print("="*70)
    print("HYPOTHESIS ORDERING DEMONSTRATION")
    print("="*70)
    print()
    
    taxonomy = FailureTaxonomy()
    orderer = HypothesisOrderer(taxonomy)
    
    # Simulate a debugging session
    context = StructuredContext(
        language="python",
        problem_type="concurrency"
    )
    
    # Create a mock session
    from failure_taxonomy import DebugSession
    session = taxonomy.start_session(
        symptom="Counter returns wrong value under load",
        context=context
    )
    
    # Generate hypotheses
    hypotheses = orderer.generate_hypotheses(session, context)
    
    print("GENERATED HYPOTHESES:")
    for i, hyp in enumerate(hypotheses, 1):
        print(f"\n{i}. {hyp.description}")
        print(f"   Prior probability: {hyp.prior_probability:.1%}")
        print(f"   Assumptions: {', '.join(hyp.assumptions)}")
        if hyp.confirming_signals:
            print(f"   Would be confirmed by: {', '.join(hyp.confirming_signals[:2])}")
    
    print()
    print("="*70)
    print()
    
    # Calculate entropy
    entropy = orderer._calculate_entropy(hypotheses)
    print(f"Current uncertainty (entropy): {entropy:.2f} bits")
    print()
    print("A good test would eliminate ~{:.1f} bits of uncertainty".format(entropy * 0.5))
    print("(Bringing us closer to confident diagnosis)")
    
    print()
    print("="*70)
    print("This is the foundation for systematic debugging.")
    print("Next: Wire this into CodingAgent to make debugging exponentially faster.")
    print("="*70)


if __name__ == "__main__":
    demo_hypothesis_ordering()
