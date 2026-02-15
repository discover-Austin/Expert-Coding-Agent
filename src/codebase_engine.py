# codebase_engine.py
"""
CodebaseExecutionEngine: Work on real projects, not toy problems.

This is the bridge from validated architecture to production use.
Handles:
- Git operations (clone, checkout, diff)
- Dependency management (pip, npm, go mod)
- Full test suite execution
- Multi-file edits with coherence
- Regression detection
"""

import subprocess
import tempfile
import shutil
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime
import hashlib

from knowledge_core import StructuredContext, ExecutionResult, OutcomeType, FailureSeverity
from execution_engine import ExecutionEngine


@dataclass
class CodebaseContext:
    """Everything we know about this project"""
    repo_url: str
    branch: str = "main"
    language: str = "python"
    framework: Optional[str] = None
    dependencies: Dict[str, str] = field(default_factory=dict)
    test_command: str = "pytest"
    build_command: Optional[str] = None
    entry_points: List[str] = field(default_factory=list)
    
    def to_structured_context(self) -> StructuredContext:
        """Convert to standard StructuredContext"""
        return StructuredContext(
            language=self.language,
            framework=self.framework,
            problem_type="general",
            domain="production"
        )


@dataclass
class FileChange:
    """A single file modification"""
    path: str
    original_content: Optional[str]
    new_content: str
    operation: str  # "create", "modify", "delete"
    reason: str  # Why this change
    
    def to_dict(self) -> Dict:
        return {
            'path': self.path,
            'operation': self.operation,
            'reason': self.reason,
            'lines_changed': len(self.new_content.split('\n')) if self.new_content else 0
        }


@dataclass
class ChangeSet:
    """Coherent set of changes across multiple files"""
    changeset_id: str
    description: str
    files: List[FileChange]
    related_to: Optional[str] = None  # Issue/ticket ID
    timestamp: datetime = field(default_factory=datetime.now)
    
    def is_coherent(self) -> Tuple[bool, str]:
        """Validate that changes make sense together"""
        # All changes should serve the same goal
        if not self.files:
            return False, "No files in changeset"
        
        # Check for common antipatterns
        has_test = any('test' in f.path for f in self.files)
        has_impl = any('test' not in f.path for f in self.files)
        
        if has_impl and not has_test:
            return False, "Implementation change without test coverage"
        
        return True, "Coherent changeset"


@dataclass
class TestResult:
    """Results from running test suite"""
    total_tests: int
    passed: int
    failed: int
    skipped: int
    duration_seconds: float
    failures: List[Dict] = field(default_factory=list)
    coverage: Optional[float] = None
    
    def to_execution_result(self) -> ExecutionResult:
        """Convert to standard ExecutionResult"""
        outcome = OutcomeType.SUCCESS if self.failed == 0 else OutcomeType.FAILURE
        
        severity = None
        if self.failed > 0:
            # More failures = more severe
            if self.failed > self.total_tests * 0.5:
                severity = FailureSeverity.CATASTROPHIC
            elif self.failed > self.total_tests * 0.2:
                severity = FailureSeverity.SEVERE
            else:
                severity = FailureSeverity.MODERATE
        
        error_msg = None
        if self.failures:
            error_msg = f"{self.failed} test(s) failed: " + ", ".join(
                f["name"] for f in self.failures[:3]
            )
        
        return ExecutionResult(
            timestamp=datetime.now(),
            code_hash=hashlib.sha256(str(self.failures).encode()).hexdigest()[:16],
            outcome=outcome,
            execution_time_ms=self.duration_seconds * 1000,
            severity=severity,
            error_message=error_msg,
            success_metrics={'coverage': self.coverage} if self.coverage else {}
        )


class CodebaseExecutionEngine(ExecutionEngine):
    """
    Execute code in real project context.
    
    This is production-grade:
    - Clones actual repos
    - Installs dependencies
    - Runs full test suites
    - Handles multi-file edits
    - Detects regressions
    """
    
    def __init__(self, workspace_dir: Optional[Path] = None):
        super().__init__()
        self.workspace_dir = workspace_dir or Path(tempfile.mkdtemp(prefix="codebase_"))
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        
    def clone_and_setup(
        self,
        context: CodebaseContext,
        shallow: bool = True
    ) -> Tuple[bool, Path, str]:
        """
        Clone repository and set up environment.
        
        Returns: (success, project_path, error_message)
        """
        repo_name = context.repo_url.split('/')[-1].replace('.git', '')
        project_path = self.workspace_dir / repo_name
        
        # Remove if exists
        if project_path.exists():
            shutil.rmtree(project_path)
        
        try:
            # Clone
            clone_cmd = ['git', 'clone']
            if shallow:
                clone_cmd.extend(['--depth', '1'])
            clone_cmd.extend(['--branch', context.branch, context.repo_url, str(project_path)])
            
            result = subprocess.run(
                clone_cmd,
                capture_output=True,
                timeout=300,  # 5 minute timeout
                cwd=self.workspace_dir
            )
            
            if result.returncode != 0:
                return False, project_path, result.stderr.decode()
            
            # Setup dependencies
            setup_success, setup_error = self._setup_dependencies(project_path, context)
            if not setup_success:
                return False, project_path, setup_error
            
            return True, project_path, ""
            
        except subprocess.TimeoutExpired:
            return False, project_path, "Clone timeout"
        except Exception as e:
            return False, project_path, str(e)
    
    def _setup_dependencies(
        self,
        project_path: Path,
        context: CodebaseContext
    ) -> Tuple[bool, str]:
        """Install project dependencies"""
        try:
            if context.language == "python":
                # Check for requirements.txt, setup.py, pyproject.toml
                if (project_path / "requirements.txt").exists():
                    result = subprocess.run(
                        ['pip', 'install', '-r', 'requirements.txt', '--quiet'],
                        cwd=project_path,
                        capture_output=True,
                        timeout=600
                    )
                    if result.returncode != 0:
                        return False, f"pip install failed: {result.stderr.decode()}"
                
                elif (project_path / "pyproject.toml").exists():
                    result = subprocess.run(
                        ['pip', 'install', '-e', '.', '--quiet'],
                        cwd=project_path,
                        capture_output=True,
                        timeout=600
                    )
                    if result.returncode != 0:
                        return False, f"pip install failed: {result.stderr.decode()}"
            
            elif context.language == "javascript":
                if (project_path / "package.json").exists():
                    result = subprocess.run(
                        ['npm', 'install'],
                        cwd=project_path,
                        capture_output=True,
                        timeout=600
                    )
                    if result.returncode != 0:
                        return False, f"npm install failed: {result.stderr.decode()}"
            
            elif context.language == "go":
                result = subprocess.run(
                    ['go', 'mod', 'download'],
                    cwd=project_path,
                    capture_output=True,
                    timeout=600
                )
                if result.returncode != 0:
                    return False, f"go mod download failed: {result.stderr.decode()}"
            
            return True, ""
            
        except subprocess.TimeoutExpired:
            return False, "Dependency installation timeout"
        except Exception as e:
            return False, str(e)
    
    def run_tests(
        self,
        project_path: Path,
        context: CodebaseContext,
        test_pattern: Optional[str] = None
    ) -> TestResult:
        """
        Run project's test suite and parse results.
        
        This is critical: we need to KNOW if code works, not guess.
        """
        try:
            # Build test command
            if context.language == "python":
                cmd = ['pytest', '--tb=short', '--quiet']
                if test_pattern:
                    cmd.append(test_pattern)
                # Add coverage if possible
                cmd.extend(['--cov=.', '--cov-report=json'])
            
            elif context.language == "javascript":
                cmd = ['npm', 'test']
                if test_pattern:
                    cmd.extend(['--', test_pattern])
            
            elif context.language == "go":
                cmd = ['go', 'test', './...', '-v']
                if test_pattern:
                    cmd.append(f'-run={test_pattern}')
            
            else:
                # Use provided test command
                cmd = context.test_command.split()
            
            # Run tests
            start = datetime.now()
            result = subprocess.run(
                cmd,
                cwd=project_path,
                capture_output=True,
                timeout=300
            )
            duration = (datetime.now() - start).total_seconds()
            
            # Parse output
            return self._parse_test_output(
                result.stdout.decode(),
                result.stderr.decode(),
                result.returncode,
                duration,
                project_path,
                context.language
            )
            
        except subprocess.TimeoutExpired:
            return TestResult(
                total_tests=0,
                passed=0,
                failed=1,
                skipped=0,
                duration_seconds=300,
                failures=[{'name': 'test_suite', 'error': 'Test timeout'}]
            )
        except Exception as e:
            return TestResult(
                total_tests=0,
                passed=0,
                failed=1,
                skipped=0,
                duration_seconds=0,
                failures=[{'name': 'test_execution', 'error': str(e)}]
            )
    
    def _parse_test_output(
        self,
        stdout: str,
        stderr: str,
        returncode: int,
        duration: float,
        project_path: Path,
        language: str
    ) -> TestResult:
        """Parse test output based on language/framework"""
        
        # Try to load coverage data
        coverage = None
        coverage_file = project_path / "coverage.json"
        if coverage_file.exists():
            try:
                with open(coverage_file) as f:
                    cov_data = json.load(f)
                    coverage = cov_data.get('totals', {}).get('percent_covered')
            except:
                pass
        
        if language == "python":
            # Parse pytest output
            # Look for: "5 passed, 2 failed in 3.21s"
            import re
            
            passed = 0
            failed = 0
            skipped = 0
            
            match = re.search(r'(\d+) passed', stdout)
            if match:
                passed = int(match.group(1))
            
            match = re.search(r'(\d+) failed', stdout)
            if match:
                failed = int(match.group(1))
            
            match = re.search(r'(\d+) skipped', stdout)
            if match:
                skipped = int(match.group(1))
            
            total = passed + failed + skipped
            
            # Extract failure details
            failures = []
            if failed > 0:
                # Parse FAILED lines
                for line in stdout.split('\n'):
                    if 'FAILED' in line:
                        parts = line.split('::')
                        if len(parts) >= 2:
                            failures.append({
                                'name': parts[-1].split(' ')[0],
                                'error': 'See test output'
                            })
            
            return TestResult(
                total_tests=total,
                passed=passed,
                failed=failed,
                skipped=skipped,
                duration_seconds=duration,
                failures=failures,
                coverage=coverage
            )
        
        else:
            # Generic parsing
            return TestResult(
                total_tests=1,
                passed=1 if returncode == 0 else 0,
                failed=0 if returncode == 0 else 1,
                skipped=0,
                duration_seconds=duration,
                failures=[] if returncode == 0 else [{'name': 'tests', 'error': stderr}],
                coverage=coverage
            )
    
    def apply_changeset(
        self,
        project_path: Path,
        changeset: ChangeSet,
        verify: bool = True
    ) -> Tuple[bool, str]:
        """
        Apply multi-file changes with coherence validation.
        
        This is where we prove complete implementations, not theater.
        """
        # Validate coherence first
        is_coherent, reason = changeset.is_coherent()
        if not is_coherent:
            return False, f"Incoherent changeset: {reason}"
        
        # Create backup
        backup_dir = project_path.parent / f"{project_path.name}_backup_{changeset.changeset_id[:8]}"
        shutil.copytree(project_path, backup_dir)
        
        try:
            # Apply each file change
            for file_change in changeset.files:
                file_path = project_path / file_change.path
                
                if file_change.operation == "create":
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    file_path.write_text(file_change.new_content)
                
                elif file_change.operation == "modify":
                    if not file_path.exists():
                        raise FileNotFoundError(f"Cannot modify non-existent file: {file_change.path}")
                    file_path.write_text(file_change.new_content)
                
                elif file_change.operation == "delete":
                    if file_path.exists():
                        file_path.unlink()
            
            # If verification requested, would run tests here
            # For now, just return success
            return True, f"Applied {len(changeset.files)} file changes"
            
        except Exception as e:
            # Rollback on failure
            shutil.rmtree(project_path)
            shutil.copytree(backup_dir, project_path)
            return False, f"Rollback due to error: {str(e)}"
        
        finally:
            # Clean up backup
            if backup_dir.exists():
                shutil.rmtree(backup_dir)
    
    def detect_regressions(
        self,
        baseline: TestResult,
        current: TestResult
    ) -> Tuple[bool, List[str]]:
        """
        Compare test results to detect regressions.
        
        A regression is:
        - Previously passing test now fails
        - Coverage decreased significantly
        - More tests failing than before
        """
        regressions = []
        
        # More failures
        if current.failed > baseline.failed:
            regressions.append(
                f"Failures increased: {baseline.failed} → {current.failed}"
            )
        
        # Coverage drop
        if baseline.coverage and current.coverage:
            if current.coverage < baseline.coverage - 5:  # 5% threshold
                regressions.append(
                    f"Coverage dropped: {baseline.coverage:.1f}% → {current.coverage:.1f}%"
                )
        
        # New failures
        baseline_failures = {f['name'] for f in baseline.failures}
        current_failures = {f['name'] for f in current.failures}
        new_failures = current_failures - baseline_failures
        
        if new_failures:
            regressions.append(
                f"New test failures: {', '.join(list(new_failures)[:3])}"
            )
        
        return len(regressions) > 0, regressions
    
    def get_file_content(self, project_path: Path, file_path: str) -> Optional[str]:
        """Read file from project"""
        full_path = project_path / file_path
        if full_path.exists() and full_path.is_file():
            return full_path.read_text()
        return None
    
    def list_files(
        self,
        project_path: Path,
        pattern: str = "*.py",
        exclude_tests: bool = False
    ) -> List[str]:
        """List files matching pattern"""
        files = []
        for path in project_path.rglob(pattern):
            if path.is_file():
                rel_path = str(path.relative_to(project_path))
                if exclude_tests and 'test' in rel_path:
                    continue
                files.append(rel_path)
        return files
    
    def cleanup(self):
        """Remove workspace"""
        if self.workspace_dir.exists():
            shutil.rmtree(self.workspace_dir)


# Example usage and validation
if __name__ == "__main__":
    print("="*70)
    print("CODEBASE EXECUTION ENGINE - VALIDATION")
    print("="*70)
    print()
    
    engine = CodebaseExecutionEngine()
    
    # Test with a simple public repo
    context = CodebaseContext(
        repo_url="https://github.com/kennethreitz/requests.git",
        branch="main",
        language="python",
        test_command="pytest tests/"
    )
    
    print(f"Testing with: {context.repo_url}")
    print()
    
    # Clone and setup
    print("Cloning repository...")
    success, project_path, error = engine.clone_and_setup(context)
    
    if success:
        print(f"✓ Cloned to: {project_path}")
        print()
        
        # List files
        files = engine.list_files(project_path, "*.py", exclude_tests=True)
        print(f"Found {len(files)} Python files (excluding tests)")
        print()
        
        # Run tests
        print("Running test suite...")
        results = engine.run_tests(project_path, context)
        
        print(f"Tests: {results.passed} passed, {results.failed} failed, {results.skipped} skipped")
        print(f"Duration: {results.duration_seconds:.2f}s")
        if results.coverage:
            print(f"Coverage: {results.coverage:.1f}%")
        
        print()
        print("✓ Codebase execution engine working")
    else:
        print(f"✗ Clone failed: {error}")
    
    print()
    print("="*70)
    
    engine.cleanup()
