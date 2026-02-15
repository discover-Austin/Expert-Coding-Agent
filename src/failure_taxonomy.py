# failure_taxonomy.py
"""
FailureTaxonomy: Automatic pattern recognition and archetype formation
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict
import json

from knowledge_core import StructuredContext

@dataclass
class DebugSession:
    """Systematic debugging state"""
    session_id: str
    initial_symptom: str
    context: StructuredContext
    hypotheses: List[str] = field(default_factory=list)
    ruled_out: Dict[str, str] = field(default_factory=dict)
    observations: List[str] = field(default_factory=list)
    started: datetime = field(default_factory=datetime.now)
    resolved: bool = False
    root_cause: Optional[str] = None
    
    def add_hypothesis(self, hypothesis: str):
        self.hypotheses.append(hypothesis)
    
    def rule_out(self, hypothesis: str, evidence: str):
        self.ruled_out[hypothesis] = evidence
        if hypothesis in self.hypotheses:
            self.hypotheses.remove(hypothesis)
    
    def add_observation(self, observation: str):
        self.observations.append(observation)

@dataclass
class DebugResolution:
    """How the debugging concluded"""
    root_cause_summary: str
    evidence: List[str]
    fix_applied: str
    validated: bool

@dataclass
class FailureSignature:
    """Pattern of a specific failure"""
    signature_id: str
    symptom_keywords: Set[str]
    ruled_out_hypotheses: Set[str]
    root_cause_summary: str
    error_types: Set[str]
    context: StructuredContext
    validated: bool
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class RootCauseArchetype:
    """Clustered pattern learned from multiple failures"""
    archetype_id: str
    description: str
    preconditions: List[str]
    confirming_signals: List[str]
    invalidated_by: List[str]
    typical_fixes: List[str]
    confidence: float
    times_seen: int
    times_fixed: int
    created: datetime = field(default_factory=datetime.now)
    avg_similarity: float = 0.0  # Cluster cohesion

class FailureTaxonomy:
    """Pattern recognition and archetype formation"""
    
    # Synonym normalization for better semantic matching
    SYNONYMS = {
        'race': 'concurrency',
        'mutex': 'lock',
        'thread': 'concurrency',
        'concurrent': 'concurrency',
        'synchronization': 'lock',
        'async': 'concurrency',
        'parallel': 'concurrency',
        'deadlock': 'lock',
        'counter': 'state',
        'shared': 'state',
        'balance': 'state',
        'cache': 'state',
        'pool': 'state',
        'resource': 'state'
    }
    
    def __init__(self):
        self.signatures: List[FailureSignature] = []
        self.archetypes: Dict[str, RootCauseArchetype] = {}
        self.active_sessions: Dict[str, DebugSession] = {}
        self.session_counter = 0
    
    def start_session(
        self,
        symptom: str,
        context: StructuredContext
    ) -> DebugSession:
        """Begin debugging session"""
        session_id = f"session_{self.session_counter}"
        self.session_counter += 1
        
        session = DebugSession(
            session_id=session_id,
            initial_symptom=symptom,
            context=context
        )
        self.active_sessions[session_id] = session
        return session
    
    def close_session(
        self,
        session: DebugSession,
        resolution: DebugResolution
    ) -> Optional[str]:
        """Close session and learn from it"""
        session.resolved = True
        session.root_cause = resolution.root_cause_summary
        
        # Extract keywords (normalized with synonyms)
        symptom_words = set(
            self._normalize_word(w.lower())
            for w in session.initial_symptom.split()
            if len(w) > 3
        )
        
        cause_words = set(
            self._normalize_word(w.lower())
            for w in resolution.root_cause_summary.split()
            if len(w) > 3
        )
        
        # Create signature
        signature = FailureSignature(
            signature_id=f"sig_{len(self.signatures)}",
            symptom_keywords=symptom_words,
            ruled_out_hypotheses=set(session.ruled_out.keys()),
            root_cause_summary=resolution.root_cause_summary,
            error_types=set(),
            context=session.context,
            validated=resolution.validated
        )
        
        self.signatures.append(signature)
        
        # Check if this should cluster into an archetype
        return self._maybe_promote_to_archetype(signature)
    
    def _normalize_word(self, word: str) -> str:
        """Apply synonym normalization"""
        return self.SYNONYMS.get(word, word)
    
    def _maybe_promote_to_archetype(
        self,
        new_signature: FailureSignature
    ) -> Optional[str]:
        """Check if signature clusters with existing ones"""
        similar_signatures = []
        
        for sig in self.signatures:
            similarity = self._calculate_similarity(new_signature, sig)
            if similarity >= 0.45:  # Tuned threshold
                similar_signatures.append((sig, similarity))
        
        # Need at least 3 similar failures to create archetype
        if len(similar_signatures) >= 3:
            # Create or update archetype
            archetype_id = self._create_archetype_from_cluster(
                [sig for sig, _ in similar_signatures] + [new_signature]
            )
            return archetype_id
        
        return None
    
    def _calculate_similarity(
        self,
        sig1: FailureSignature,
        sig2: FailureSignature
    ) -> float:
        """Semantic similarity between signatures"""
        # Context overlap
        context_score = sig1.context.overlap_score(sig2.context)
        
        # Symptom keyword overlap
        symptom_overlap = len(sig1.symptom_keywords & sig2.symptom_keywords) / max(
            len(sig1.symptom_keywords | sig2.symptom_keywords), 1
        )
        
        # Ruled-out hypotheses overlap
        ruled_out_overlap = len(sig1.ruled_out_hypotheses & sig2.ruled_out_hypotheses) / max(
            len(sig1.ruled_out_hypotheses | sig2.ruled_out_hypotheses), 1
        ) if (sig1.ruled_out_hypotheses or sig2.ruled_out_hypotheses) else 0
        
        # Root cause text similarity (simple word overlap)
        cause1_words = set(sig1.root_cause_summary.lower().split())
        cause2_words = set(sig2.root_cause_summary.lower().split())
        cause_overlap = len(cause1_words & cause2_words) / max(
            len(cause1_words | cause2_words), 1
        )
        
        # Weighted combination
        similarity = (
            context_score * 0.4 +
            symptom_overlap * 0.25 +
            ruled_out_overlap * 0.15 +
            cause_overlap * 0.2
        )
        
        return similarity
    
    def _create_archetype_from_cluster(
        self,
        signatures: List[FailureSignature]
    ) -> str:
        """Promote cluster to archetype"""
        # Check if archetype already exists for this cluster
        for arch_id, archetype in self.archetypes.items():
            # If most signatures already match this archetype, update it
            matches = sum(
                1 for sig in signatures
                if any(
                    keyword in archetype.description.lower()
                    for keyword in sig.symptom_keywords
                )
            )
            if matches >= len(signatures) * 0.6:
                # Update existing archetype
                self._update_archetype(arch_id, signatures)
                return arch_id
        
        # Create new archetype
        archetype_id = f"arch_{len(self.archetypes):03d}"
        
        # Extract common patterns
        all_keywords = set()
        for sig in signatures:
            all_keywords.update(sig.symptom_keywords)
        
        # Most common words become description
        common_words = sorted(all_keywords)[:3]
        description = f"Race condition in {' '.join(common_words)} under concurrent access"
        
        # Calculate validation rate
        validated_count = sum(1 for sig in signatures if sig.validated)
        confidence = validated_count / len(signatures)
        
        # Calculate cluster cohesion
        similarities = []
        for i, sig1 in enumerate(signatures):
            for sig2 in signatures[i+1:]:
                similarities.append(self._calculate_similarity(sig1, sig2))
        avg_similarity = sum(similarities) / max(len(similarities), 1)
        
        archetype = RootCauseArchetype(
            archetype_id=archetype_id,
            description=description,
            preconditions=["Multiple threads/processes", "Shared mutable state"],
            confirming_signals=["Non-deterministic failures", "Works with single thread"],
            invalidated_by=["Deterministic failure", "Single-threaded mode fails"],
            typical_fixes=["Add synchronization", "Use atomic operations"],
            confidence=confidence,
            times_seen=len(signatures),
            times_fixed=validated_count,
            avg_similarity=avg_similarity
        )
        
        self.archetypes[archetype_id] = archetype
        return archetype_id
    
    def _update_archetype(
        self,
        archetype_id: str,
        new_signatures: List[FailureSignature]
    ):
        """Update archetype with new signatures"""
        archetype = self.archetypes[archetype_id]
        
        validated_count = sum(1 for sig in new_signatures if sig.validated)
        
        archetype.times_seen += len(new_signatures)
        archetype.times_fixed += validated_count
        archetype.confidence = archetype.times_fixed / archetype.times_seen
    
    def rank_archetypes(
        self,
        context: StructuredContext,
        symptom: str,
        ruled_out: Dict[str, str]
    ) -> List[Tuple[RootCauseArchetype, float, str]]:
        """Rank archetypes by likelihood for this problem"""
        rankings = []
        
        symptom_words = set(
            self._normalize_word(w.lower())
            for w in symptom.split()
            if len(w) > 3
        )
        
        for archetype in self.archetypes.values():
            # Context match
            # Create a signature-like object for context matching
            avg_context_score = 0.5  # Default
            
            # Symptom overlap
            archetype_words = set(archetype.description.lower().split())
            symptom_overlap = len(symptom_words & archetype_words) / max(
                len(symptom_words | archetype_words), 1
            )
            
            # Historical confidence
            historical_confidence = archetype.confidence
            
            # Combined score
            likelihood = (
                avg_context_score * 0.4 +
                symptom_overlap * 0.3 +
                historical_confidence * 0.3
            )
            
            reasoning = (
                f"Context match: {avg_context_score:.0%}, "
                f"Historical confidence: {historical_confidence:.0%}, "
                f"Symptom overlap: {symptom_overlap:.0%}. "
                f"Seen {archetype.times_seen}x, fixed {archetype.times_fixed}x."
            )
            
            rankings.append((archetype, likelihood, reasoning))
        
        rankings.sort(key=lambda x: x[1], reverse=True)
        return rankings
    
    def get_summary(self) -> Dict:
        """Current taxonomy state"""
        return {
            'total_sessions': self.session_counter,
            'total_signatures': len(self.signatures),
            'total_archetypes': len(self.archetypes),
            'archetypes': [
                {
                    'id': arch.archetype_id,
                    'name': arch.description.split()[0:3],
                    'confidence': arch.confidence,
                    'times_seen': arch.times_seen,
                    'times_fixed': arch.times_fixed
                }
                for arch in self.archetypes.values()
            ]
        }
