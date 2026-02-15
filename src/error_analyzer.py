# error_analyzer.py
"""
ErrorAnalyzer: Deep analysis of failures with recovery strategies.

Day 5 capability. When things break, learn WHY and HOW to prevent it.

This is not "retry and hope" - it's:
1. Parse the failure (stack trace, error type, context)
2. Classify the root cause (not the symptom)
3. Find similar past failures (via FailureTaxonomy)
4. Suggest fixes based on empirical evidence
5. Execute recovery strategies (rollback, retry, escalate)
6. Learn from every failure (feed into KnowledgeCore)

Deliverable: Agent learns from every error, applies to future work.
"""

import re
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple
from enum import Enum
from pathlib import Path

from knowledge_core import (
    KnowledgeCore, StructuredContext, PatternCategory,
    Decision, OutcomeType, FailureSeverity, ExecutionResult
)
from failure_taxonomy import (
    FailureTaxonomy, DebugSession, DebugResolution,
    FailureSignature, RootCauseArchetype
)
from codebase_engine import TestResult


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ErrorCategory(Enum):
    """Classification of error root causes (not symptoms)."""
    IMPORT_ERROR = "import_error"
    TYPE_ERROR = "type_error"
    ATTRIBUTE_ERROR = "attribute_error"
    VALUE_ERROR = "value_error"
    INDEX_ERROR = "index_error"
    KEY_ERROR = "key_error"
    ASSERTION_ERROR = "assertion_error"
    RUNTIME_ERROR = "runtime_error"
    TIMEOUT = "timeout"
    PERMISSION_ERROR = "permission_error"
    FILE_NOT_FOUND = "file_not_found"
    CONNECTION_ERROR = "connection_error"
    SYNTAX_ERROR = "syntax_error"
    CONCURRENCY_ERROR = "concurrency_error"
    MEMORY_ERROR = "memory_error"
    UNKNOWN = "unknown"


class RecoveryAction(Enum):
    """What can be done to recover."""
    ROLLBACK = "rollback"
    RETRY = "retry"
    FIX_AND_RETRY = "fix_and_retry"
    SKIP = "skip"
    ESCALATE = "escalate"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class StackFrame:
    """A single frame from a parsed stack trace."""
    file_path: str
    line_number: int
    function_name: str
    code_line: str

    def to_dict(self) -> Dict:
        return {
            'file': self.file_path,
            'line': self.line_number,
            'function': self.function_name,
            'code': self.code_line,
        }


@dataclass
class FailureAnalysis:
    """Complete analysis of a single failure — not just WHAT, but WHY."""
    failure_id: str
    error_type: str                       # e.g. "TypeError"
    error_message: str                    # e.g. "unsupported operand type(s)..."
    category: ErrorCategory               # Classified root cause
    stack_frames: List[StackFrame]        # Parsed traceback
    violated_assumption: str              # What the code assumed that was wrong
    root_cause_summary: str               # Human-readable diagnosis
    similar_past_failures: List[Tuple[str, float]]  # (archetype_id, match_score)
    suggested_fixes: List[str]            # Ordered by confidence
    severity: FailureSeverity
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict:
        return {
            'failure_id': self.failure_id,
            'error_type': self.error_type,
            'error_message': self.error_message,
            'category': self.category.value,
            'stack_frames': [f.to_dict() for f in self.stack_frames],
            'violated_assumption': self.violated_assumption,
            'root_cause_summary': self.root_cause_summary,
            'similar_past_failures': [
                {'archetype_id': aid, 'score': s}
                for aid, s in self.similar_past_failures
            ],
            'suggested_fixes': self.suggested_fixes,
            'severity': self.severity.value,
        }


@dataclass
class RecoveryStrategy:
    """How to recover from a failure."""
    action: RecoveryAction
    description: str
    confidence: float         # 0-1, how likely this will work
    preconditions: List[str]  # What must be true for this to work
    steps: List[str]          # Ordered execution steps

    def to_dict(self) -> Dict:
        return {
            'action': self.action.value,
            'description': self.description,
            'confidence': self.confidence,
            'preconditions': self.preconditions,
            'steps': self.steps,
        }


@dataclass
class RecoveryResult:
    """Outcome of executing a recovery strategy."""
    strategy: RecoveryStrategy
    success: bool
    message: str
    tests_after: Optional[TestResult] = None


# ---------------------------------------------------------------------------
# Error classification rules — maps exception names to categories + fixes
# ---------------------------------------------------------------------------

_ERROR_RULES: Dict[str, Tuple[ErrorCategory, str, List[str]]] = {
    # --- Import errors ---
    'ImportError': (
        ErrorCategory.IMPORT_ERROR,
        "Code assumed a module or name was importable",
        ["Install missing dependency", "Fix circular import", "Check module path"],
    ),
    'ModuleNotFoundError': (
        ErrorCategory.IMPORT_ERROR,
        "Code assumed a package was installed",
        ["Install missing package", "Check virtual environment", "Fix package name"],
    ),
    # --- Type errors ---
    'TypeError': (
        ErrorCategory.TYPE_ERROR,
        "Code assumed a value had a different type",
        ["Add type check before operation", "Fix function signature", "Convert type explicitly"],
    ),
    # --- Attribute errors ---
    'AttributeError': (
        ErrorCategory.ATTRIBUTE_ERROR,
        "Code assumed an object had an attribute it doesn't",
        ["Check for None before access", "Verify object type", "Fix attribute name typo"],
    ),
    # --- Value errors ---
    'ValueError': (
        ErrorCategory.VALUE_ERROR,
        "Code assumed a value was in an acceptable range or format",
        ["Add input validation", "Handle edge case", "Fix data transformation"],
    ),
    'UnicodeDecodeError': (
        ErrorCategory.VALUE_ERROR,
        "Code assumed text encoding matched actual bytes",
        ["Specify correct encoding", "Use errors='replace' or 'ignore'", "Detect encoding first"],
    ),
    'UnicodeEncodeError': (
        ErrorCategory.VALUE_ERROR,
        "Code assumed text could be encoded in target encoding",
        ["Use UTF-8 encoding", "Handle unencodable characters", "Normalize text first"],
    ),
    # --- Index errors ---
    'IndexError': (
        ErrorCategory.INDEX_ERROR,
        "Code assumed a sequence had enough elements",
        ["Add bounds check", "Handle empty sequence", "Fix off-by-one error"],
    ),
    # --- Key errors ---
    'KeyError': (
        ErrorCategory.KEY_ERROR,
        "Code assumed a key existed in a mapping",
        ["Use .get() with default", "Check key existence first", "Fix key name"],
    ),
    # --- Assertion errors ---
    'AssertionError': (
        ErrorCategory.ASSERTION_ERROR,
        "An explicit assertion was violated",
        ["Fix the condition that violates the assertion", "Update assertion to match new behavior"],
    ),
    'AssertionError': (
        ErrorCategory.ASSERTION_ERROR,
        "An explicit assertion was violated",
        ["Fix the condition that violates the assertion", "Update assertion to match new behavior"],
    ),
    # --- Runtime errors ---
    'RuntimeError': (
        ErrorCategory.RUNTIME_ERROR,
        "Runtime invariant was broken",
        ["Check for recursive calls", "Fix generator/coroutine usage", "Review logic flow"],
    ),
    'RecursionError': (
        ErrorCategory.RUNTIME_ERROR,
        "Code entered infinite recursion",
        ["Add base case to recursive function", "Convert to iterative approach", "Increase recursion limit"],
    ),
    'StopIteration': (
        ErrorCategory.RUNTIME_ERROR,
        "Iterator was exhausted unexpectedly",
        ["Add length check before next()", "Use default value with next(iter, default)", "Handle empty iterators"],
    ),
    'NotImplementedError': (
        ErrorCategory.RUNTIME_ERROR,
        "Code called an unimplemented method",
        ["Implement the abstract method", "Check class hierarchy", "Use correct subclass"],
    ),
    # --- Timeout errors ---
    'TimeoutError': (
        ErrorCategory.TIMEOUT,
        "Operation took longer than expected",
        ["Increase timeout", "Optimize slow operation", "Add early termination"],
    ),
    # --- Permission errors ---
    'PermissionError': (
        ErrorCategory.PERMISSION_ERROR,
        "Code assumed it had access to a resource",
        ["Fix file permissions", "Run with correct privileges", "Check path ownership"],
    ),
    # --- File errors ---
    'FileNotFoundError': (
        ErrorCategory.FILE_NOT_FOUND,
        "Code assumed a file or directory existed",
        ["Create missing file/directory", "Fix file path", "Add existence check"],
    ),
    'FileExistsError': (
        ErrorCategory.FILE_NOT_FOUND,
        "Code assumed a file did not already exist",
        ["Add exist_ok=True", "Check existence before creation", "Remove or rename existing file"],
    ),
    'IsADirectoryError': (
        ErrorCategory.FILE_NOT_FOUND,
        "Code treated a directory as a file",
        ["Check path type before access", "Fix file path", "Handle directories separately"],
    ),
    # --- Connection errors ---
    'ConnectionError': (
        ErrorCategory.CONNECTION_ERROR,
        "Code assumed a network service was reachable",
        ["Check service availability", "Add retry with backoff", "Handle offline gracefully"],
    ),
    'ConnectionRefusedError': (
        ErrorCategory.CONNECTION_ERROR,
        "Target service refused the connection",
        ["Check if service is running", "Verify port number", "Add retry with backoff"],
    ),
    'ConnectionResetError': (
        ErrorCategory.CONNECTION_ERROR,
        "Remote server reset the connection",
        ["Add retry with backoff", "Check for server overload", "Verify request payload size"],
    ),
    'BrokenPipeError': (
        ErrorCategory.CONNECTION_ERROR,
        "Write to a closed pipe or socket",
        ["Handle client disconnect gracefully", "Check connection before writing", "Add signal handling"],
    ),
    # --- Syntax errors ---
    'SyntaxError': (
        ErrorCategory.SYNTAX_ERROR,
        "Code has a syntax error",
        ["Fix syntax at indicated line", "Check for missing brackets/colons"],
    ),
    'IndentationError': (
        ErrorCategory.SYNTAX_ERROR,
        "Code has inconsistent indentation",
        ["Fix indentation at indicated line", "Use consistent tabs or spaces"],
    ),
    'TabError': (
        ErrorCategory.SYNTAX_ERROR,
        "Code mixes tabs and spaces",
        ["Convert all indentation to spaces", "Configure editor for consistent indentation"],
    ),
    # --- Memory errors ---
    'MemoryError': (
        ErrorCategory.MEMORY_ERROR,
        "Operation exceeded available memory",
        ["Process data in chunks", "Reduce data size", "Increase memory limit"],
    ),
    # --- Concurrency errors ---
    'BlockingIOError': (
        ErrorCategory.CONCURRENCY_ERROR,
        "Non-blocking I/O operation would block",
        ["Handle EAGAIN/EWOULDBLOCK", "Use select/poll before I/O", "Switch to async I/O"],
    ),
    # --- OS / environment errors ---
    'OSError': (
        ErrorCategory.RUNTIME_ERROR,
        "Operating system reported an error",
        ["Check system resources", "Verify file descriptors", "Handle OS-specific edge cases"],
    ),
    'EnvironmentError': (
        ErrorCategory.RUNTIME_ERROR,
        "Environment configuration is wrong",
        ["Check environment variables", "Verify system configuration", "Fix path settings"],
    ),
    'OverflowError': (
        ErrorCategory.VALUE_ERROR,
        "Numeric result too large to represent",
        ["Use arbitrary precision (decimal module)", "Clamp input range", "Check for overflow before operation"],
    ),
    'ZeroDivisionError': (
        ErrorCategory.VALUE_ERROR,
        "Code divided by zero",
        ["Add zero check before division", "Handle edge case with default value"],
    ),
    'ArithmeticError': (
        ErrorCategory.VALUE_ERROR,
        "Arithmetic operation failed",
        ["Validate operands before operation", "Handle numeric edge cases"],
    ),
}


# ---------------------------------------------------------------------------
# Extensible error rules — users can register custom exception types
# ---------------------------------------------------------------------------

_CUSTOM_ERROR_RULES: Dict[str, Tuple[ErrorCategory, str, List[str]]] = {}


def register_error_rule(
    error_name: str,
    category: ErrorCategory,
    violated_assumption: str,
    suggested_fixes: List[str],
) -> None:
    """
    Register a custom error classification rule.

    Allows extending the analyzer for project-specific or framework-specific
    exceptions (e.g. Django's Http404, SQLAlchemy's IntegrityError).
    """
    _CUSTOM_ERROR_RULES[error_name] = (category, violated_assumption, suggested_fixes)


# ---------------------------------------------------------------------------
# ErrorAnalyzer
# ---------------------------------------------------------------------------

class ErrorAnalyzer:
    """
    Deep analysis of failures. Not just WHAT failed, but WHY.

    Integrates with:
    - FailureTaxonomy: find similar past failures, feed new patterns
    - KnowledgeCore: record failure patterns with empirical confidence
    - TestResult: consume test failures from CodebaseExecutionEngine
    """

    def __init__(
        self,
        taxonomy: FailureTaxonomy,
        knowledge: KnowledgeCore,
    ):
        self.taxonomy = taxonomy
        self.knowledge = knowledge
        self._analysis_counter = 0
        # Track all analyses for clustering
        self._analyses: List[FailureAnalysis] = []

    # ------------------------------------------------------------------
    # Core analysis
    # ------------------------------------------------------------------

    def analyze_test_failure(
        self,
        test_result: TestResult,
        context: StructuredContext,
        source_code: Optional[str] = None,
    ) -> List[FailureAnalysis]:
        """
        Analyze every failure in a TestResult.

        Returns one FailureAnalysis per individual test failure.
        Each analysis includes: parsed stack trace, classified error,
        violated assumption, similar past failures, and suggested fixes.
        """
        if test_result.failed == 0:
            return []

        analyses = []

        for failure_info in test_result.failures:
            analysis = self._analyze_single_failure(
                failure_info, context, test_result
            )
            analyses.append(analysis)
            self._analyses.append(analysis)

        return analyses

    def _analyze_single_failure(
        self,
        failure_info: Dict,
        context: StructuredContext,
        test_result: TestResult,
    ) -> FailureAnalysis:
        """Analyze one test failure dict from TestResult.failures."""

        self._analysis_counter += 1
        failure_id = f"fail_{self._analysis_counter:04d}"

        test_name = failure_info.get('name', 'unknown_test')
        error_text = failure_info.get('error', '')
        traceback_text = failure_info.get('traceback', '')

        # 1. Parse stack trace
        stack_frames = self._parse_stack_trace(traceback_text)

        # 2. Extract error type and message
        error_type, error_message = self._extract_error_info(
            error_text, traceback_text
        )

        # 3. Classify into category
        category, violated_assumption, default_fixes = self._classify_error(
            error_type, error_message
        )

        # 4. Determine severity
        severity = self._assess_severity(
            category, test_result, stack_frames
        )

        # 5. Build root cause summary
        root_cause = self._build_root_cause_summary(
            test_name, error_type, error_message, category, stack_frames
        )

        # 6. Find similar past failures via taxonomy
        similar = self._find_similar_failures(
            context, root_cause, error_type
        )

        # 7. Build suggested fixes (taxonomy-informed + defaults)
        suggested_fixes = self._build_fix_suggestions(
            similar, default_fixes, category, error_message
        )

        return FailureAnalysis(
            failure_id=failure_id,
            error_type=error_type,
            error_message=error_message,
            category=category,
            stack_frames=stack_frames,
            violated_assumption=violated_assumption,
            root_cause_summary=root_cause,
            similar_past_failures=similar,
            suggested_fixes=suggested_fixes,
            severity=severity,
        )

    # ------------------------------------------------------------------
    # Stack trace parsing
    # ------------------------------------------------------------------

    def _parse_stack_trace(self, traceback_text: str) -> List[StackFrame]:
        """Parse a Python traceback into structured StackFrame objects."""
        if not traceback_text:
            return []

        frames = []
        # Match:  File "path", line N, in func_name
        pattern = re.compile(
            r'File "([^"]+)", line (\d+), in (\S+)'
        )

        lines = traceback_text.split('\n')
        for i, line in enumerate(lines):
            match = pattern.search(line)
            if match:
                file_path = match.group(1)
                line_number = int(match.group(2))
                function_name = match.group(3)

                # Next line (if exists) is usually the code
                code_line = ''
                if i + 1 < len(lines):
                    candidate = lines[i + 1].strip()
                    # Skip if it looks like another File line or the error line
                    if candidate and not candidate.startswith('File ') and not pattern.search(candidate):
                        code_line = candidate

                frames.append(StackFrame(
                    file_path=file_path,
                    line_number=line_number,
                    function_name=function_name,
                    code_line=code_line,
                ))

        return frames

    # ------------------------------------------------------------------
    # Error extraction & classification
    # ------------------------------------------------------------------

    def _extract_error_info(
        self, error_text: str, traceback_text: str
    ) -> Tuple[str, str]:
        """Extract (error_type, error_message) from raw text."""

        # Try traceback last line: "TypeError: ..."
        if traceback_text:
            for line in reversed(traceback_text.strip().split('\n')):
                line = line.strip()
                if ':' in line and not line.startswith('File '):
                    parts = line.split(':', 1)
                    candidate = parts[0].strip()
                    # Valid Python exception names are PascalCase words
                    if re.match(r'^[A-Z]\w*Error$|^[A-Z]\w*Exception$|^[A-Z]\w*Warning$', candidate):
                        return candidate, parts[1].strip()

        # Fallback: try error_text itself
        if error_text:
            for known in _ERROR_RULES:
                if known in error_text:
                    # Extract message after the error name
                    idx = error_text.index(known)
                    after = error_text[idx + len(known):]
                    msg = after.lstrip(':').strip() if after else error_text
                    return known, msg

        return 'UnknownError', error_text or 'No error details available'

    def _classify_error(
        self,
        error_type: str,
        error_message: str,
    ) -> Tuple[ErrorCategory, str, List[str]]:
        """
        Classify error into category.

        Checks custom rules first (project-specific), then built-in rules,
        then heuristic fallback.

        Returns (category, violated_assumption, default_fixes).
        """
        # Custom rules take priority (project-specific overrides)
        if error_type in _CUSTOM_ERROR_RULES:
            cat, assumption, fixes = _CUSTOM_ERROR_RULES[error_type]
            return cat, assumption, list(fixes)

        if error_type in _ERROR_RULES:
            cat, assumption, fixes = _ERROR_RULES[error_type]
            return cat, assumption, list(fixes)

        # Heuristic fallback for unknown error types
        msg_lower = error_message.lower()
        if 'timeout' in msg_lower or 'timed out' in msg_lower:
            return (
                ErrorCategory.TIMEOUT,
                "Operation took longer than expected",
                ["Increase timeout", "Optimize slow operation"],
            )
        if 'permission' in msg_lower or 'denied' in msg_lower:
            return (
                ErrorCategory.PERMISSION_ERROR,
                "Insufficient permissions",
                ["Fix permissions", "Run with correct privileges"],
            )
        if 'connect' in msg_lower or 'refused' in msg_lower:
            return (
                ErrorCategory.CONNECTION_ERROR,
                "Network service unreachable",
                ["Check service", "Add retry logic"],
            )
        if 'lock' in msg_lower or 'deadlock' in msg_lower or 'race' in msg_lower:
            return (
                ErrorCategory.CONCURRENCY_ERROR,
                "Concurrent access caused inconsistency",
                ["Add synchronization", "Use atomic operations"],
            )

        return (
            ErrorCategory.UNKNOWN,
            "Unknown assumption violated",
            ["Inspect error details", "Add defensive checks"],
        )

    # ------------------------------------------------------------------
    # Severity assessment
    # ------------------------------------------------------------------

    def _assess_severity(
        self,
        category: ErrorCategory,
        test_result: TestResult,
        stack_frames: List[StackFrame],
    ) -> FailureSeverity:
        """Assess severity from observable signals."""

        # More than half the suite failing → catastrophic
        if test_result.total_tests > 0:
            failure_ratio = test_result.failed / test_result.total_tests
            if failure_ratio > 0.5:
                return FailureSeverity.CATASTROPHIC
            if failure_ratio > 0.2:
                return FailureSeverity.SEVERE

        # Deep stack traces often indicate systemic issues
        if len(stack_frames) > 10:
            return FailureSeverity.SEVERE

        # Import and syntax errors block everything
        if category in (ErrorCategory.IMPORT_ERROR, ErrorCategory.SYNTAX_ERROR):
            return FailureSeverity.SEVERE

        # Concurrency and memory errors are hard to reproduce
        if category in (ErrorCategory.CONCURRENCY_ERROR, ErrorCategory.MEMORY_ERROR):
            return FailureSeverity.SEVERE

        return FailureSeverity.MODERATE

    # ------------------------------------------------------------------
    # Root cause summary
    # ------------------------------------------------------------------

    def _build_root_cause_summary(
        self,
        test_name: str,
        error_type: str,
        error_message: str,
        category: ErrorCategory,
        stack_frames: List[StackFrame],
    ) -> str:
        """Build a human-readable root cause summary."""
        location = ""
        if stack_frames:
            frame = stack_frames[-1]  # Deepest frame is usually the cause
            location = f" in {frame.function_name} ({frame.file_path}:{frame.line_number})"

        return (
            f"{error_type}{location}: {error_message}. "
            f"Category: {category.value}. Test: {test_name}."
        )

    # ------------------------------------------------------------------
    # Similar past failures
    # ------------------------------------------------------------------

    def _find_similar_failures(
        self,
        context: StructuredContext,
        root_cause: str,
        error_type: str,
    ) -> List[Tuple[str, float]]:
        """Query taxonomy for similar past failures."""

        # Build symptom from error info
        symptom = f"{error_type} {root_cause}"

        rankings = self.taxonomy.rank_archetypes(
            context=context,
            symptom=symptom,
            ruled_out={},
        )

        # Return (archetype_id, likelihood) pairs
        return [
            (arch.archetype_id, likelihood)
            for arch, likelihood, _reasoning in rankings
        ]

    # ------------------------------------------------------------------
    # Fix suggestions
    # ------------------------------------------------------------------

    def _build_fix_suggestions(
        self,
        similar: List[Tuple[str, float]],
        default_fixes: List[str],
        category: ErrorCategory,
        error_message: str,
    ) -> List[str]:
        """
        Build ordered fix suggestions.

        Taxonomy-based fixes first (empirically validated),
        then rule-based defaults.
        """
        suggestions = []

        # Taxonomy-informed fixes (from archetypes with high match)
        for arch_id, score in similar:
            if score < 0.3:
                continue
            archetype = self.taxonomy.archetypes.get(arch_id)
            if archetype and archetype.typical_fixes:
                for fix in archetype.typical_fixes:
                    if fix not in suggestions:
                        suggestions.append(fix)

        # Rule-based defaults (only add new ones)
        for fix in default_fixes:
            if fix not in suggestions:
                suggestions.append(fix)

        return suggestions

    # ------------------------------------------------------------------
    # Failure clustering (build_failure_taxonomy from spec)
    # ------------------------------------------------------------------

    def build_failure_taxonomy(
        self,
        analyses: List[FailureAnalysis],
        deduplicate: bool = True,
    ) -> Dict[str, List[FailureAnalysis]]:
        """
        Cluster failures by root cause category with deduplication.

        When deduplicate=True, failures with identical (error_type, error_message)
        are collapsed into a single representative. This prevents N identical
        failures from inflating cluster sizes and producing false archetype
        promotions.

        Returns {category_name: [deduplicated analyses in that category]}.
        """
        clusters: Dict[str, List[FailureAnalysis]] = {}

        if deduplicate:
            # Deduplicate by (error_type, error_message) within each category
            seen: Dict[str, Set[Tuple[str, str]]] = {}
            for analysis in analyses:
                key = analysis.category.value
                sig = (analysis.error_type, analysis.error_message)

                if key not in seen:
                    seen[key] = set()
                    clusters[key] = []

                if sig not in seen[key]:
                    seen[key].add(sig)
                    clusters[key].append(analysis)
        else:
            for analysis in analyses:
                key = analysis.category.value
                if key not in clusters:
                    clusters[key] = []
                clusters[key].append(analysis)

        return clusters

    def deduplicate_analyses(
        self,
        analyses: List[FailureAnalysis],
    ) -> List[FailureAnalysis]:
        """
        Remove duplicate failure analyses.

        Two analyses are duplicates if they share the same
        (error_type, error_message, category). Keeps the first occurrence.
        This prevents the same error triggered by multiple test cases from
        bloating the knowledge base.
        """
        seen: Set[Tuple[str, str, str]] = set()
        unique = []

        for analysis in analyses:
            sig = (analysis.error_type, analysis.error_message, analysis.category.value)
            if sig not in seen:
                seen.add(sig)
                unique.append(analysis)

        return unique

    # ------------------------------------------------------------------
    # Recovery strategies
    # ------------------------------------------------------------------

    def suggest_recovery(
        self,
        analysis: FailureAnalysis,
        has_baseline: bool = True,
        has_backup: bool = True,
    ) -> List[RecoveryStrategy]:
        """
        Suggest recovery strategies for a failure, ordered by confidence.

        Uses error category, severity, and available recovery options.
        """
        strategies = []

        # Strategy 1: Rollback (if we have a backup)
        if has_backup and analysis.severity.value >= FailureSeverity.MODERATE.value:
            strategies.append(RecoveryStrategy(
                action=RecoveryAction.ROLLBACK,
                description="Revert to last known good state",
                confidence=0.95,
                preconditions=["Backup exists", "Baseline tests passed"],
                steps=[
                    "Restore original file contents from backup",
                    "Re-run baseline tests to verify restoration",
                    "Record failure pattern for future avoidance",
                ],
            ))

        # Strategy 2: Fix and retry (category-specific)
        fix_strategies = self._category_recovery(analysis)
        strategies.extend(fix_strategies)

        # Strategy 3: Retry (for transient failures)
        if analysis.category in (
            ErrorCategory.TIMEOUT,
            ErrorCategory.CONNECTION_ERROR,
        ):
            strategies.append(RecoveryStrategy(
                action=RecoveryAction.RETRY,
                description="Retry the operation (transient failure likely)",
                confidence=0.6,
                preconditions=["Failure appears transient"],
                steps=[
                    "Wait briefly before retry",
                    "Retry the failed operation",
                    "If still failing, escalate",
                ],
            ))

        # Strategy 4: Skip (for non-critical failures)
        if analysis.severity == FailureSeverity.MINOR:
            strategies.append(RecoveryStrategy(
                action=RecoveryAction.SKIP,
                description="Skip this failure and continue",
                confidence=0.4,
                preconditions=["Failure is non-critical", "Other tests still pass"],
                steps=[
                    "Log the failure for later investigation",
                    "Continue with remaining work",
                ],
            ))

        # Strategy 5: Escalate (always available as last resort)
        strategies.append(RecoveryStrategy(
            action=RecoveryAction.ESCALATE,
            description="Escalate: failure requires human investigation",
            confidence=0.3,
            preconditions=[],
            steps=[
                "Document the failure analysis",
                "Save all context (stack trace, error, affected files)",
                "Report to user for investigation",
            ],
        ))

        # Sort by confidence descending
        strategies.sort(key=lambda s: s.confidence, reverse=True)
        return strategies

    def _category_recovery(
        self,
        analysis: FailureAnalysis,
    ) -> List[RecoveryStrategy]:
        """Generate fix-and-retry strategies based on error category."""
        strategies = []

        if analysis.category == ErrorCategory.IMPORT_ERROR:
            strategies.append(RecoveryStrategy(
                action=RecoveryAction.FIX_AND_RETRY,
                description="Fix import: install missing dependency or fix path",
                confidence=0.7,
                preconditions=["Missing module name is identifiable"],
                steps=[
                    "Parse error message for missing module name",
                    "Attempt pip install <module>",
                    "Re-run tests",
                ],
            ))

        elif analysis.category == ErrorCategory.TYPE_ERROR:
            strategies.append(RecoveryStrategy(
                action=RecoveryAction.FIX_AND_RETRY,
                description="Fix type mismatch at the call site",
                confidence=0.5,
                preconditions=["Error location is identified"],
                steps=[
                    "Identify the type mismatch from the error message",
                    "Add type conversion or fix the calling code",
                    "Re-run tests",
                ],
            ))

        elif analysis.category == ErrorCategory.ATTRIBUTE_ERROR:
            strategies.append(RecoveryStrategy(
                action=RecoveryAction.FIX_AND_RETRY,
                description="Fix attribute access: add None check or fix name",
                confidence=0.6,
                preconditions=["Object and attribute are identifiable"],
                steps=[
                    "Check if the object is None (add guard)",
                    "Or fix the attribute name if it's a typo",
                    "Re-run tests",
                ],
            ))

        elif analysis.category == ErrorCategory.KEY_ERROR:
            strategies.append(RecoveryStrategy(
                action=RecoveryAction.FIX_AND_RETRY,
                description="Fix key access: use .get() or check existence",
                confidence=0.65,
                preconditions=["Missing key is identifiable"],
                steps=[
                    "Replace dict[key] with dict.get(key, default)",
                    "Or ensure the key is set before access",
                    "Re-run tests",
                ],
            ))

        elif analysis.category == ErrorCategory.ASSERTION_ERROR:
            strategies.append(RecoveryStrategy(
                action=RecoveryAction.FIX_AND_RETRY,
                description="Fix logic that violates the assertion",
                confidence=0.5,
                preconditions=["Assertion location is identified"],
                steps=[
                    "Understand what the assertion expects",
                    "Fix the code that produces the wrong value",
                    "Re-run tests",
                ],
            ))

        return strategies

    # ------------------------------------------------------------------
    # Execute recovery
    # ------------------------------------------------------------------

    def validate_fix_safety(
        self,
        strategy: RecoveryStrategy,
        analysis: FailureAnalysis,
        explanation_gate_complete: bool = False,
        affected_tests_exist: bool = False,
    ) -> Tuple[bool, List[str]]:
        """
        Validate that a FIX_AND_RETRY strategy is safe to execute.

        Safety requirements for automatic code changes:
        1. Error location must be identified (stack frames present)
        2. Explanation gate must be complete (understand before modifying)
        3. Affected functions must have test coverage
        4. Severity must not be CATASTROPHIC (too risky for auto-fix)

        Returns (is_safe, blocking_reasons).
        """
        if strategy.action != RecoveryAction.FIX_AND_RETRY:
            return True, []

        blockers = []

        # Must have error location
        if not analysis.stack_frames:
            blockers.append("No stack trace: cannot identify fix location")

        # Must understand the code first (Day 2 explanation gate)
        if not explanation_gate_complete:
            blockers.append("Explanation gate incomplete: must understand code before modifying")

        # Must have test coverage for affected code (Day 3 test enforcement)
        if not affected_tests_exist:
            blockers.append("No test coverage for affected functions: fix cannot be validated")

        # Cannot auto-fix catastrophic failures (too much blast radius)
        if analysis.severity == FailureSeverity.CATASTROPHIC:
            blockers.append("Catastrophic severity: auto-fix too risky, escalate instead")

        return len(blockers) == 0, blockers

    def execute_recovery(
        self,
        strategy: RecoveryStrategy,
        original_content: Optional[Dict[str, str]],
        project_path: Optional[Path],
        explanation_gate_complete: bool = False,
        affected_tests_exist: bool = False,
        analysis: Optional[FailureAnalysis] = None,
    ) -> RecoveryResult:
        """
        Execute a recovery strategy with safety validation.

        For ROLLBACK: restores original file contents.
        For FIX_AND_RETRY: validates safety before returning plan.
        For others: returns instructions (actual code changes are
        handled by ProductionCodingAgent).
        """
        # Safety gate for FIX_AND_RETRY
        if strategy.action == RecoveryAction.FIX_AND_RETRY and analysis:
            is_safe, blockers = self.validate_fix_safety(
                strategy, analysis,
                explanation_gate_complete, affected_tests_exist,
            )
            if not is_safe:
                return RecoveryResult(
                    strategy=strategy,
                    success=False,
                    message=f"Fix blocked by safety gate: {'; '.join(blockers)}",
                )

        if strategy.action == RecoveryAction.ROLLBACK:
            if original_content and project_path:
                restored = 0
                for rel_path, content in original_content.items():
                    target = project_path / rel_path
                    if target.exists() or target.parent.exists():
                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_text(content)
                        restored += 1

                return RecoveryResult(
                    strategy=strategy,
                    success=restored > 0,
                    message=f"Rolled back {restored} file(s) to original state",
                )

            return RecoveryResult(
                strategy=strategy,
                success=False,
                message="Cannot rollback: no original content available",
            )

        # For non-rollback strategies, return the plan
        return RecoveryResult(
            strategy=strategy,
            success=True,
            message=f"Recovery plan ready: {strategy.description}",
        )

    # ------------------------------------------------------------------
    # Learning: feed failures into taxonomy + knowledge
    # ------------------------------------------------------------------

    def learn_from_failure(
        self,
        analysis: FailureAnalysis,
        context: StructuredContext,
        fix_applied: Optional[str] = None,
        fix_validated: bool = False,
    ) -> Optional[str]:
        """
        Feed a failure analysis into FailureTaxonomy and KnowledgeCore.

        Returns archetype_id if the failure promoted to an archetype.
        """
        # 1. Create debug session in taxonomy
        debug_session = self.taxonomy.start_session(
            symptom=f"{analysis.error_type}: {analysis.error_message}",
            context=context,
        )

        # Add observations from the analysis
        debug_session.add_observation(
            f"Category: {analysis.category.value}"
        )
        debug_session.add_observation(
            f"Violated assumption: {analysis.violated_assumption}"
        )
        if analysis.stack_frames:
            deepest = analysis.stack_frames[-1]
            debug_session.add_observation(
                f"Location: {deepest.function_name} in {deepest.file_path}:{deepest.line_number}"
            )

        # Close with resolution
        resolution = DebugResolution(
            root_cause_summary=analysis.root_cause_summary,
            evidence=[
                f"Error: {analysis.error_type}: {analysis.error_message}",
                f"Category: {analysis.category.value}",
                f"Severity: {analysis.severity.value}",
            ],
            fix_applied=fix_applied or "No fix applied yet",
            validated=fix_validated,
        )

        archetype_id = self.taxonomy.close_session(debug_session, resolution)

        # 2. Record in KnowledgeCore
        concept_id = f"error_{analysis.category.value}"
        concept = self.knowledge.create_concept(
            concept_id=concept_id,
            category=PatternCategory.ERROR_HANDLING,
            description=f"Error pattern: {analysis.category.value}",
        )

        outcome = OutcomeType.SUCCESS if fix_validated else OutcomeType.FAILURE
        self.knowledge.record_execution(
            concept_id=concept_id,
            code=analysis.root_cause_summary,
            context=context,
            outcome=outcome,
            execution_time_ms=0,
            decision=Decision(
                hypothesis=analysis.violated_assumption,
                assumptions=[analysis.violated_assumption],
                alternatives_considered=analysis.suggested_fixes[:3],
                rejected_because={},
            ),
            severity=analysis.severity,
            error_message=analysis.error_message,
        )

        return archetype_id

    def learn_from_recovery(
        self,
        analysis: FailureAnalysis,
        recovery_result: RecoveryResult,
        context: StructuredContext,
    ) -> None:
        """
        Learn whether a recovery strategy worked.

        Updates KnowledgeCore confidence for the recovery approach.
        """
        concept_id = f"recovery_{analysis.category.value}"
        self.knowledge.create_concept(
            concept_id=concept_id,
            category=PatternCategory.ERROR_HANDLING,
            description=f"Recovery for {analysis.category.value} errors",
        )

        outcome = OutcomeType.SUCCESS if recovery_result.success else OutcomeType.FAILURE
        self.knowledge.record_execution(
            concept_id=concept_id,
            code=recovery_result.strategy.description,
            context=context,
            outcome=outcome,
            execution_time_ms=0,
            decision=Decision(
                hypothesis=recovery_result.strategy.description,
                assumptions=recovery_result.strategy.preconditions,
                alternatives_considered=[],
                rejected_because={},
            ),
            severity=analysis.severity if not recovery_result.success else None,
            error_message=recovery_result.message if not recovery_result.success else None,
        )

    # ------------------------------------------------------------------
    # Aggregate analysis
    # ------------------------------------------------------------------

    def analyze_failure_trends(self) -> Dict[str, any]:
        """
        Analyze trends across all recorded failures.

        Returns summary of:
        - Most common error categories
        - Most frequent violated assumptions
        - Severity distribution
        - Unique vs total failure count (deduplication ratio)
        - Cluster quality metrics
        """
        if not self._analyses:
            return {
                'total_failures': 0,
                'unique_failures': 0,
                'dedup_ratio': 1.0,
                'category_counts': {},
                'severity_distribution': {},
                'top_violated_assumptions': [],
                'cluster_quality': {},
            }

        category_counts: Dict[str, int] = {}
        severity_counts: Dict[int, int] = {}
        assumptions: Dict[str, int] = {}

        for analysis in self._analyses:
            cat = analysis.category.value
            category_counts[cat] = category_counts.get(cat, 0) + 1

            sev = analysis.severity.value
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

            assumption = analysis.violated_assumption
            assumptions[assumption] = assumptions.get(assumption, 0) + 1

        # Deduplication stats
        unique = self.deduplicate_analyses(self._analyses)
        dedup_ratio = len(unique) / len(self._analyses) if self._analyses else 1.0

        # Cluster quality: for each category, measure how many unique
        # error signatures exist. A category with many identical errors
        # has low diversity (good clustering). A category with all unique
        # errors might be a junk drawer.
        cluster_quality = {}
        for cat, count in category_counts.items():
            cat_analyses = [a for a in self._analyses if a.category.value == cat]
            cat_unique = self.deduplicate_analyses(cat_analyses)
            diversity = len(cat_unique) / len(cat_analyses) if cat_analyses else 1.0
            cluster_quality[cat] = {
                'total': count,
                'unique': len(cat_unique),
                'diversity': round(diversity, 2),
                'is_coherent': diversity < 0.8,  # Low diversity = good clustering
            }

        top_assumptions = sorted(
            assumptions.items(), key=lambda x: x[1], reverse=True
        )[:5]

        return {
            'total_failures': len(self._analyses),
            'unique_failures': len(unique),
            'dedup_ratio': round(dedup_ratio, 2),
            'category_counts': category_counts,
            'severity_distribution': severity_counts,
            'top_violated_assumptions': [
                {'assumption': a, 'count': c}
                for a, c in top_assumptions
            ],
            'cluster_quality': cluster_quality,
        }

    def get_summary(self) -> Dict:
        """Current error analyzer state."""
        return {
            'total_analyses': len(self._analyses),
            'trends': self.analyze_failure_trends(),
        }
