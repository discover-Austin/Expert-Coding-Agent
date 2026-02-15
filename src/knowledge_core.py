# knowledge_core.py
"""
KnowledgeCore: Pattern concepts vs instances with empirical confidence
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any, Tuple
from enum import Enum
import json
import hashlib

class OutcomeType(Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    UNKNOWN = "unknown"

class FailureSeverity(Enum):
    CATASTROPHIC = 4
    SEVERE = 3
    MODERATE = 2
    MINOR = 1

class PatternCategory(Enum):
    ARCHITECTURE = "architecture"
    BUG_FIX = "bug_fix"
    OPTIMIZATION = "optimization"
    ERROR_HANDLING = "error_handling"
    EDGE_CASE = "edge_case"
    CONCURRENCY = "concurrency"
    DATA_VALIDATION = "data_validation"

@dataclass
class StructuredContext:
    """No substring matching - explicit overlap scoring"""
    language: str
    framework: Optional[str] = None
    problem_type: str = "general"
    failure_mode: Optional[str] = None
    domain: str = "general"
    version_info: Dict[str, str] = field(default_factory=dict)
    
    def overlap_score(self, other: 'StructuredContext') -> float:
        """Calculate similarity between contexts"""
        score = 0.0
        weights = {
            'language': 3.0,
            'framework': 2.0,
            'problem_type': 2.5,
            'failure_mode': 1.5,
            'domain': 1.0
        }
        
        if self.language == other.language:
            score += weights['language']
        if self.framework and self.framework == other.framework:
            score += weights['framework']
        if self.problem_type == other.problem_type:
            score += weights['problem_type']
        if self.failure_mode and self.failure_mode == other.failure_mode:
            score += weights['failure_mode']
        if self.domain == other.domain:
            score += weights['domain']
        
        return score / sum(weights.values())
    
    def to_dict(self) -> Dict:
        return {
            'language': self.language,
            'framework': self.framework,
            'problem_type': self.problem_type,
            'failure_mode': self.failure_mode,
            'domain': self.domain,
            'version_info': self.version_info
        }

@dataclass
class Decision:
    """Why this approach, what alternatives were considered"""
    hypothesis: str
    assumptions: List[str]
    alternatives_considered: List[str]
    rejected_because: Dict[str, str]
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class ExecutionResult:
    """What actually happened when code ran"""
    timestamp: datetime
    code_hash: str
    outcome: OutcomeType
    execution_time_ms: float
    severity: Optional[FailureSeverity] = None
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    success_metrics: Dict[str, Any] = field(default_factory=dict)
    blast_radius: int = 0

@dataclass
class PatternInstance:
    """A specific implementation of a concept"""
    instance_id: str
    code: str
    context: StructuredContext
    outcomes: List[ExecutionResult] = field(default_factory=list)
    decisions: List[Decision] = field(default_factory=list)
    created: datetime = field(default_factory=datetime.now)
    last_used: datetime = field(default_factory=datetime.now)
    
    def get_confidence(self) -> float:
        """Empirical confidence: recency + validation rate + sample size"""
        if not self.outcomes:
            return 0.0
        
        now = datetime.now()
        weighted_success = 0.0
        total_weight = 0.0
        
        for outcome in self.outcomes:
            age_days = (now - outcome.timestamp).days
            recency_weight = 2.71828 ** (-age_days / 30.0)
            
            if outcome.outcome == OutcomeType.SUCCESS:
                weighted_success += recency_weight
            elif outcome.outcome == OutcomeType.FAILURE:
                severity_penalty = outcome.severity.value if outcome.severity else 1
                weighted_success -= recency_weight * severity_penalty
            
            total_weight += recency_weight
        
        if total_weight == 0:
            return 0.0
        
        raw_score = (weighted_success / total_weight + 1) / 2
        sample_confidence = min(1.0, len(self.outcomes) / 10.0)
        
        return raw_score * sample_confidence
    
    def should_decay(self) -> bool:
        """Should this instance be forgotten?"""
        age = (datetime.now() - self.last_used).days
        confidence = self.get_confidence()
        return (age > 90 and confidence < 0.3) or age > 365

@dataclass
class PatternConcept:
    """The abstract idea, language-independent"""
    concept_id: str
    category: PatternCategory
    description: str
    instances: Dict[str, PatternInstance] = field(default_factory=dict)
    related_concepts: Set[str] = field(default_factory=set)
    
    def add_instance(self, instance: PatternInstance):
        self.instances[instance.instance_id] = instance
    
    def best_instance_for_context(
        self,
        context: StructuredContext
    ) -> Optional[Tuple[PatternInstance, float]]:
        """Find best proven implementation for this context"""
        candidates = []
        
        for instance in self.instances.values():
            context_score = instance.context.overlap_score(context)
            if context_score < 0.3:
                continue
            
            confidence = instance.get_confidence()
            score = context_score * 0.4 + confidence * 0.6
            candidates.append((instance, score))
        
        if not candidates:
            return None
        
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0]
    
    def consolidate(self):
        """Forget low-value instances"""
        to_remove = [
            iid for iid, inst in self.instances.items()
            if inst.should_decay()
        ]
        for iid in to_remove:
            del self.instances[iid]

class KnowledgeCore:
    """Persistent expertise that compounds"""
    
    def __init__(self):
        self.concepts: Dict[str, PatternConcept] = {}
    
    def create_concept(
        self,
        concept_id: str,
        category: PatternCategory,
        description: str
    ) -> PatternConcept:
        if concept_id in self.concepts:
            return self.concepts[concept_id]
        
        concept = PatternConcept(
            concept_id=concept_id,
            category=category,
            description=description
        )
        self.concepts[concept_id] = concept
        return concept
    
    def record_execution(
        self,
        concept_id: str,
        code: str,
        context: StructuredContext,
        outcome: OutcomeType,
        execution_time_ms: float,
        decision: Decision,
        severity: Optional[FailureSeverity] = None,
        error_message: Optional[str] = None
    ) -> str:
        """Record what happened when code was executed"""
        if concept_id not in self.concepts:
            raise ValueError(f"Concept {concept_id} not found")
        
        concept = self.concepts[concept_id]
        code_hash = hashlib.sha256(code.encode()).hexdigest()[:16]
        instance_id = f"{concept_id}_{code_hash[:8]}"
        
        if instance_id not in concept.instances:
            instance = PatternInstance(
                instance_id=instance_id,
                code=code,
                context=context
            )
            concept.add_instance(instance)
        else:
            instance = concept.instances[instance_id]
        
        result = ExecutionResult(
            timestamp=datetime.now(),
            code_hash=code_hash,
            outcome=outcome,
            execution_time_ms=execution_time_ms,
            severity=severity,
            error_message=error_message
        )
        
        instance.outcomes.append(result)
        instance.decisions.append(decision)
        instance.last_used = datetime.now()
        
        return instance_id
    
    def get_summary(self) -> Dict[str, Any]:
        """Current expertise state"""
        total_instances = sum(len(c.instances) for c in self.concepts.values())
        total_outcomes = sum(
            len(inst.outcomes)
            for c in self.concepts.values()
            for inst in c.instances.values()
        )
        
        return {
            'total_concepts': len(self.concepts),
            'total_instances': total_instances,
            'total_outcomes': total_outcomes
        }
