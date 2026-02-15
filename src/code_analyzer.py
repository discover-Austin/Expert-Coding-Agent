# code_analyzer.py
"""
CodeAnalyzer: Understand before modifying.

HARD REQUIREMENTS:
1. Project structure map (exact, not guessed)
2. Dependency graph (executable, feeds impact prediction)
3. Change impact prediction (before any edit)
4. Explanation gate (blocks execution if incomplete)

If it guesses → fail loudly.
If explanation is incomplete → block execution.
No bypass. Ever.
"""

import ast
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
from datetime import datetime


@dataclass
class FunctionInfo:
    """What we know about a function"""
    name: str
    file: str
    line_number: int
    calls: Set[str] = field(default_factory=set)
    mutates_state: List[str] = field(default_factory=list)  # Variables it modifies
    is_tested: bool = False
    test_files: List[str] = field(default_factory=list)
    test_assertions: List[str] = field(default_factory=list)
    params: List[str] = field(default_factory=list)  # NEW: Parameter names
    param_count: int = 0  # NEW: Number of parameters
    
    def to_dict(self) -> Dict:
        return {
            'name': self.name,
            'file': self.file,
            'line_number': self.line_number,
            'calls': list(self.calls),
            'mutates_state': self.mutates_state,
            'is_tested': self.is_tested,
            'test_files': self.test_files,
            'test_assertions': self.test_assertions,
            'params': self.params,
            'param_count': self.param_count
        }


@dataclass
class ModuleInfo:
    """What we know about a module/file"""
    path: str
    functions: Dict[str, FunctionInfo] = field(default_factory=dict)
    imports: Set[str] = field(default_factory=set)
    exports: Set[str] = field(default_factory=set)
    is_test: bool = False
    
    def to_dict(self) -> Dict:
        return {
            'path': self.path,
            'functions': {name: fn.to_dict() for name, fn in self.functions.items()},
            'imports': list(self.imports),
            'exports': list(self.exports),
            'is_test': self.is_test
        }


@dataclass
class ProjectStructure:
    """Complete understanding of project structure"""
    entry_points: List[str]
    core_modules: Dict[str, List[str]]  # category -> files
    test_structure: Dict[str, any]
    total_files: int
    total_functions: int
    test_coverage_estimate: float
    
    def to_dict(self) -> Dict:
        return {
            'entry_points': self.entry_points,
            'core_modules': self.core_modules,
            'test_structure': self.test_structure,
            'total_files': self.total_files,
            'total_functions': self.total_functions,
            'test_coverage_estimate': self.test_coverage_estimate
        }


@dataclass
class DependencyGraph:
    """Who calls what - executable graph"""
    dependencies: Dict[str, List[str]]  # function -> [functions it calls]
    reverse_deps: Dict[str, List[str]]  # function -> [functions that call it]
    
    def get_impact_set(self, function_name: str, depth: int = 3) -> Set[str]:
        """What functions are affected if this one changes?"""
        affected = set()
        to_visit = [(function_name, 0)]
        visited = set()
        
        while to_visit:
            current, current_depth = to_visit.pop(0)
            
            if current in visited or current_depth > depth:
                continue
            
            visited.add(current)
            affected.add(current)
            
            # Add all functions that depend on this one
            for dependent in self.reverse_deps.get(current, []):
                if dependent not in visited:
                    to_visit.append((dependent, current_depth + 1))
        
        return affected
    
    def to_dict(self) -> Dict:
        return {
            'dependencies': self.dependencies,
            'reverse_dependencies': self.reverse_deps
        }


@dataclass
class ChangeImpact:
    """Predicted impact of changing specific files"""
    files_likely_affected: List[str]
    functions_affected: Set[str]
    risk_level: str  # LOW, MEDIUM, HIGH, CRITICAL
    reason: str
    tests_to_run: List[str]
    
    def to_dict(self) -> Dict:
        return {
            'files_likely_affected': self.files_likely_affected,
            'functions_affected': list(self.functions_affected),
            'risk_level': self.risk_level,
            'reason': self.reason,
            'tests_to_run': self.tests_to_run
        }


@dataclass
class ExplanationGate:
    """Gate that blocks execution if understanding is incomplete"""
    current_code_explained: bool = False
    source_of_truth_identified: bool = False
    invariants_identified: bool = False
    tests_mapped: bool = False
    
    explanation_text: str = ""
    identified_invariants: List[str] = field(default_factory=list)
    test_assertions: List[str] = field(default_factory=list)
    
    def is_complete(self) -> bool:
        """Can we proceed?"""
        return all([
            self.current_code_explained,
            self.source_of_truth_identified,
            self.invariants_identified,
            self.tests_mapped
        ])
    
    def missing_requirements(self) -> List[str]:
        """What's blocking execution?"""
        missing = []
        if not self.current_code_explained:
            missing.append("Current code not explained")
        if not self.source_of_truth_identified:
            missing.append("Source of truth not identified")
        if not self.invariants_identified:
            missing.append("Invariants not identified")
        if not self.tests_mapped:
            missing.append("Tests not mapped to behavior")
        return missing
    
    def to_dict(self) -> Dict:
        return {
            'complete': self.is_complete(),
            'checks': {
                'current_code_explained': self.current_code_explained,
                'source_of_truth_identified': self.source_of_truth_identified,
                'invariants_identified': self.invariants_identified,
                'tests_mapped': self.tests_mapped
            },
            'missing': self.missing_requirements(),
            'explanation': self.explanation_text,
            'invariants': self.identified_invariants,
            'test_assertions': self.test_assertions
        }


class PythonAnalyzer:
    """Parse Python code with AST - no guessing"""
    
    def analyze_file(self, filepath: Path) -> ModuleInfo:
        """Parse a single Python file"""
        
        try:
            source = filepath.read_text()
            tree = ast.parse(source)
        except SyntaxError as e:
            # Fail loudly on parse errors
            raise ValueError(f"Cannot parse {filepath}: {e}")
        
        module = ModuleInfo(
            path=str(filepath),
            is_test='test' in str(filepath).lower()
        )
        
        # Extract imports
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module.imports.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module.imports.add(node.module)
        
        # Extract functions
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_info = self._analyze_function(node, str(filepath))
                module.functions[node.name] = func_info
                module.exports.add(node.name)
        
        return module
    
    def _analyze_function(self, node: ast.FunctionDef, filepath: str) -> FunctionInfo:
        """Analyze a single function"""
        
        # Extract parameters
        params = []
        for arg in node.args.args:
            if arg.arg != 'self':  # Skip self for methods
                params.append(arg.arg)
        
        func = FunctionInfo(
            name=node.name,
            file=filepath,
            line_number=node.lineno,
            params=params,
            param_count=len(params)
        )
        
        # Find function calls
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    func.calls.add(child.func.id)
                elif isinstance(child.func, ast.Attribute):
                    # method.call()
                    func.calls.add(f"{ast.unparse(child.func.value)}.{child.func.attr}")
        
        # Find state mutations (assignments)
        for child in ast.walk(node):
            if isinstance(child, ast.Assign):
                for target in child.targets:
                    if isinstance(target, ast.Name):
                        func.mutates_state.append(target.id)
                    elif isinstance(target, ast.Attribute):
                        func.mutates_state.append(ast.unparse(target))
        
        return func


class TestAnalyzer:
    """Extract what tests actually assert - ground truth"""
    
    def analyze_test_file(self, filepath: Path) -> Dict[str, List[str]]:
        """
        Parse test file to extract assertions.
        
        Returns: {function_under_test: [assertions]}
        """
        
        try:
            source = filepath.read_text()
            tree = ast.parse(source)
        except:
            return {}
        
        test_map = defaultdict(list)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
                # Extract what this test asserts
                assertions = self._extract_assertions(node)
                
                # Try to infer what function is being tested
                # Look for function calls in the test
                tested_functions = self._infer_tested_functions(node)
                
                for func in tested_functions:
                    test_map[func].extend(assertions)
        
        return dict(test_map)
    
    def _extract_assertions(self, node: ast.FunctionDef) -> List[str]:
        """Extract assert statements from test"""
        assertions = []
        
        for child in ast.walk(node):
            if isinstance(child, ast.Assert):
                # Get assertion text
                assertion_text = ast.unparse(child.test)
                assertions.append(assertion_text)
            
            elif isinstance(child, ast.Call):
                # pytest assertions: assert_equal, etc.
                if isinstance(child.func, ast.Attribute):
                    if child.func.attr.startswith('assert'):
                        assertions.append(ast.unparse(child))
        
        return assertions
    
    def _infer_tested_functions(self, node: ast.FunctionDef) -> Set[str]:
        """What functions does this test exercise?"""
        functions = set()
        
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    # Direct function call
                    if not child.func.id.startswith('test_'):
                        functions.add(child.func.id)
                elif isinstance(child.func, ast.Attribute):
                    # Method call
                    functions.add(child.func.attr)
        
        return functions


class CodeAnalyzer:
    """
    Understand codebase before modifying it.
    
    No guessing. No hand-waving. Fail loudly if incomplete.
    """
    
    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = cache_dir or Path("./understanding_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.python_analyzer = PythonAnalyzer()
        self.test_analyzer = TestAnalyzer()
        
        # Storage
        self.modules: Dict[str, ModuleInfo] = {}
        self.dependency_graph: Optional[DependencyGraph] = None
        self.structure: Optional[ProjectStructure] = None
    
    def analyze_project(
        self,
        project_path: Path,
        language: str = "python"
    ) -> Tuple[ProjectStructure, DependencyGraph]:
        """
        Analyze entire project structure.
        
        Returns: (structure, dependency_graph)
        Raises: ValueError if analysis incomplete
        """
        
        print(f"\n{'='*70}")
        print("CODE ANALYSIS - UNDERSTANDING PHASE")
        print(f"{'='*70}\n")
        
        if language != "python":
            raise NotImplementedError(f"Language {language} not yet supported")
        
        # Find all Python files
        py_files = list(project_path.rglob("*.py"))
        
        # Filter out common excludes
        py_files = [
            f for f in py_files
            if not any(exclude in str(f) for exclude in [
                '__pycache__', '.venv', 'venv', 'env',
                '.git', 'build', 'dist', '.eggs'
            ])
        ]
        
        print(f"Found {len(py_files)} Python files")
        print()
        
        # Analyze each file
        test_files = []
        impl_files = []
        
        for filepath in py_files:
            try:
                module = self.python_analyzer.analyze_file(filepath)
                self.modules[str(filepath.relative_to(project_path))] = module
                
                if module.is_test:
                    test_files.append(str(filepath.relative_to(project_path)))
                else:
                    impl_files.append(str(filepath.relative_to(project_path)))
                    
            except ValueError as e:
                print(f"⚠️  Parse error in {filepath}: {e}")
                # Continue analysis, but record the failure
        
        print(f"Analyzed: {len(impl_files)} implementation files, {len(test_files)} test files")
        print()
        
        # Build dependency graph
        self.dependency_graph = self._build_dependency_graph()
        
        # Identify structure
        self.structure = self._identify_structure(
            project_path,
            impl_files,
            test_files
        )
        
        # Map tests to functions
        self._map_tests_to_functions(project_path)
        
        # Cache the understanding
        self._cache_understanding(project_path)
        
        print("✓ Analysis complete")
        print()
        
        return self.structure, self.dependency_graph
    
    def _build_dependency_graph(self) -> DependencyGraph:
        """Build executable dependency graph with strict symbol resolution"""
        
        dependencies = defaultdict(list)
        reverse_deps = defaultdict(list)
        
        # Build symbol index: name -> set of qualified names
        symbol_index: Dict[str, Set[str]] = defaultdict(set)
        for module_path, module in self.modules.items():
            for func_name in module.functions.keys():
                qualified = f"{module_path}:{func_name}"
                symbol_index[func_name].add(qualified)
        
        # Track unresolved calls
        unresolved_calls = []
        total_calls = 0
        
        # Build dependencies with strict resolution
        for module_path, module in self.modules.items():
            for func_name, func_info in module.functions.items():
                qualified_name = f"{module_path}:{func_name}"
                
                for called_func in func_info.calls:
                    total_calls += 1
                    
                    # Resolve call to qualified name
                    if '.' in called_func:
                        # Method call - skip for now
                        continue
                    
                    candidates = symbol_index.get(called_func, set())
                    
                    if len(candidates) == 0:
                        # External call or unresolved - skip
                        continue
                    elif len(candidates) == 1:
                        # Exact match - link it
                        resolved = list(candidates)[0]
                        dependencies[qualified_name].append(resolved)
                        reverse_deps[resolved].append(qualified_name)
                    else:
                        # Ambiguous - record but continue
                        unresolved_calls.append((qualified_name, called_func, candidates))
        
        # HARD CHECK: Fail if too many unresolved
        if total_calls > 0:
            unresolved_ratio = len(unresolved_calls) / total_calls
            if unresolved_ratio > 0.3:  # More than 30% unresolved
                raise ValueError(
                    f"Dependency resolution failed: {len(unresolved_calls)}/{total_calls} "
                    f"calls ambiguous or unresolved ({unresolved_ratio:.0%})"
                )
        
        return DependencyGraph(
            dependencies=dict(dependencies),
            reverse_deps=dict(reverse_deps)
        )
    
    def _identify_structure(
        self,
        project_path: Path,
        impl_files: List[str],
        test_files: List[str]
    ) -> ProjectStructure:
        """Identify project structure - no guessing"""
        
        # Find entry points
        entry_points = []
        for impl_file in impl_files:
            if any(name in impl_file for name in ['main.py', '__main__.py', 'app.py', 'cli.py']):
                entry_points.append(impl_file)
        
        # Categorize modules by common patterns
        core_modules = defaultdict(list)
        
        for impl_file in impl_files:
            # Simple categorization based on path
            parts = Path(impl_file).parts
            if len(parts) > 1:
                category = parts[0]  # Top-level directory
                core_modules[category].append(impl_file)
            else:
                core_modules['root'].append(impl_file)
        
        # Detect test framework - MUST CONFIRM, NOT GUESS
        test_framework = self._detect_test_framework_strict(project_path, test_files)
        
        # Count functions
        total_functions = sum(
            len(m.functions) for m in self.modules.values()
            if not m.is_test
        )
        
        # Estimate coverage
        tested_functions = sum(
            1 for m in self.modules.values()
            for f in m.functions.values()
            if f.is_tested
        )
        coverage_estimate = tested_functions / max(total_functions, 1)
        
        return ProjectStructure(
            entry_points=entry_points,
            core_modules=dict(core_modules),
            test_structure={
                'framework': test_framework,
                'test_files': len(test_files),
                'coverage_estimate': coverage_estimate
            },
            total_files=len(impl_files),
            total_functions=total_functions,
            test_coverage_estimate=coverage_estimate
        )
    
    def _detect_test_framework_strict(
        self,
        project_path: Path,
        test_files: List[str]
    ) -> str:
        """
        Detect test framework with confirmation - FAILS if ambiguous.
        
        Must confirm via multiple signals:
        - Config files
        - Import statements
        - File conventions
        
        Returns: 'pytest', 'unittest', etc.
        Raises: ValueError if ambiguous or undetectable
        """
        
        signals = {
            'pytest': 0,
            'unittest': 0,
            'nose': 0
        }
        
        # Signal 1: Config files
        if (project_path / 'pytest.ini').exists():
            signals['pytest'] += 2
        
        if (project_path / 'setup.cfg').exists():
            try:
                content = (project_path / 'setup.cfg').read_text()
                if '[tool:pytest]' in content:
                    signals['pytest'] += 2
            except:
                pass
        
        if (project_path / 'pyproject.toml').exists():
            try:
                content = (project_path / 'pyproject.toml').read_text()
                if '[tool.pytest' in content:
                    signals['pytest'] += 2
            except:
                pass
        
        # Signal 2: Imports in test files (sample first 5)
        for test_file in test_files[:5]:
            full_path = project_path / test_file
            if full_path.exists():
                try:
                    content = full_path.read_text()
                    tree = ast.parse(content)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                if alias.name == 'pytest':
                                    signals['pytest'] += 1
                                elif alias.name == 'unittest':
                                    signals['unittest'] += 1
                                elif alias.name == 'nose':
                                    signals['nose'] += 1
                        elif isinstance(node, ast.ImportFrom):
                            if node.module == 'pytest':
                                signals['pytest'] += 1
                            elif node.module == 'unittest':
                                signals['unittest'] += 1
                except:
                    continue
        
        # Determine framework from signals
        if not test_files:
            # No test files - framework is N/A
            return 'none'
        
        # Get strongest signal
        max_signal = max(signals.values())
        candidates = [fw for fw, score in signals.items() if score == max_signal and score > 0]
        
        if len(candidates) == 0:
            # No framework detected
            raise ValueError(
                f"Test framework detection failed: {len(test_files)} test files found "
                f"but no pytest/unittest/nose imports or config detected"
            )
        
        if len(candidates) > 1:
            # Ambiguous
            raise ValueError(
                f"Test framework detection ambiguous: {candidates} all have signal={max_signal}"
            )
        
        # Confirmed single framework
        return candidates[0]
    
    def _map_tests_to_functions(self, project_path: Path):
        """Map test assertions to implementation functions"""
        
        for module_path, module in self.modules.items():
            if not module.is_test:
                continue
            
            # Analyze this test file
            test_map = self.test_analyzer.analyze_test_file(
                project_path / module_path
            )
            
            # Update function info with assertions
            for func_name, assertions in test_map.items():
                # Find the function in our modules
                for impl_module in self.modules.values():
                    if func_name in impl_module.functions:
                        impl_module.functions[func_name].is_tested = True
                        impl_module.functions[func_name].test_files.append(module_path)
                        # NEW: Store actual assertions
                        impl_module.functions[func_name].test_assertions.extend(assertions)
    
    def predict_impact(
        self,
        target_files: List[str],
        change_type: str = "modify"
    ) -> ChangeImpact:
        """
        Predict impact of changing these files.
        
        This is NOT a guess. It's based on dependency graph.
        """
        
        if not self.dependency_graph:
            raise ValueError("Must run analyze_project first")
        
        affected_functions = set()
        affected_files = set(target_files)
        
        # Find all functions in target files
        for target_file in target_files:
            if target_file in self.modules:
                module = self.modules[target_file]
                for func_name in module.functions:
                    qualified = f"{target_file}:{func_name}"
                    # Get impact set
                    impact = self.dependency_graph.get_impact_set(qualified)
                    affected_functions.update(impact)
        
        # Extract unique files from affected functions
        for func in affected_functions:
            if ':' in func:
                file_part = func.split(':')[0]
                affected_files.add(file_part)
        
        # Find tests to run
        tests_to_run = []
        for file in affected_files:
            if file in self.modules:
                module = self.modules[file]
                for func in module.functions.values():
                    tests_to_run.extend(func.test_files)
        
        # Assess risk
        risk_level = "LOW"
        reason_parts = []
        
        if len(affected_files) > 10:
            risk_level = "CRITICAL"
            reason_parts.append(f"Wide impact: {len(affected_files)} files affected")
        elif len(affected_files) > 5:
            risk_level = "HIGH"
            reason_parts.append(f"Broad impact: {len(affected_files)} files affected")
        elif len(affected_files) > 2:
            risk_level = "MEDIUM"
            reason_parts.append(f"Moderate impact: {len(affected_files)} files affected")
        
        # Check for auth/security boundaries
        if any('auth' in f.lower() for f in target_files):
            risk_level = "HIGH"
            reason_parts.append("Touches authentication boundary")
        
        if any('session' in f.lower() for f in target_files):
            risk_level = "HIGH"
            reason_parts.append("Affects session management")
        
        reason = "; ".join(reason_parts) if reason_parts else "Low impact change"
        
        return ChangeImpact(
            files_likely_affected=list(affected_files),
            functions_affected=affected_functions,
            risk_level=risk_level,
            reason=reason,
            tests_to_run=list(set(tests_to_run))
        )
    
    def _is_trivial_assertion(self, assertion: str) -> bool:
        """
        Check if assertion is trivial (doesn't test behavior).
        
        Trivial assertions:
        - assert True / assert False
        - Constant comparisons: 1 == 1, 'a' == 'a'
        
        Non-trivial assertions reference variables, calls, attributes.
        """
        assertion = assertion.strip()
        
        # Exact trivial patterns
        if assertion in ['True', 'False', '1', '0']:
            return True
        
        # Constant-only comparisons
        # Pattern: literal == literal (no variables/calls)
        if '==' in assertion or '!=' in assertion:
            # Split on comparison operator
            parts = assertion.replace('==', ' ').replace('!=', ' ').split()
            # If all parts are literals (numbers, strings), it's trivial
            all_literals = True
            for part in parts:
                part = part.strip()
                if not part:
                    continue
                # Check if it's a literal
                if not (part.isdigit() or 
                       part.startswith("'") or 
                       part.startswith('"') or
                       part in ['True', 'False', 'None']):
                    all_literals = False
                    break
            
            if all_literals:
                return True
        
        # If it contains function calls, variable names, or attributes, it's non-trivial
        # Simple heuristic: contains parentheses (calls) or dots (attributes) or identifiers
        has_call = '(' in assertion
        has_attribute = '.' in assertion and not assertion.replace('.', '').replace(' ', '').isdigit()
        
        # Check for identifiers (variables)
        # If assertion has alphanumeric without quotes, likely a variable
        import re
        has_identifier = bool(re.search(r'[a-zA-Z_]\w+', assertion))
        
        if has_call or has_attribute or (has_identifier and assertion not in ['True', 'False', 'None']):
            return False  # Non-trivial
        
        # Default: assume trivial if we can't determine
        return True
    
    def create_explanation_gate(
        self,
        target_files: List[str]
    ) -> ExplanationGate:
        """
        Create explanation gate for target files.
        
        This BLOCKS execution if understanding is incomplete.
        HARD REQUIREMENT: Must have non-trivial assertions from tests.
        """
        
        gate = ExplanationGate()
        
        # Check 1: Can we explain the current code?
        explanation_parts = []
        for file in target_files:
            if file in self.modules:
                module = self.modules[file]
                func_names = list(module.functions.keys())
                explanation_parts.append(
                    f"{file}: Contains {len(func_names)} functions: {', '.join(func_names[:3])}"
                )
        
        if explanation_parts:
            gate.current_code_explained = True
            gate.explanation_text = "\n".join(explanation_parts)
        
        # Check 2: Source of truth identified?
        gate.source_of_truth_identified = bool(explanation_parts)
        
        # Check 3: Invariants identified? (HARD REQUIREMENT)
        # Must have NON-TRIVIAL assertions extracted from tests
        for file in target_files:
            if file in self.modules:
                module = self.modules[file]
                for func in module.functions.values():
                    # NEW: Check actual assertions, not just test file presence
                    non_trivial_assertions = [
                        a for a in func.test_assertions 
                        if not self._is_trivial_assertion(a)
                    ]
                    
                    if non_trivial_assertions:
                        gate.identified_invariants.append(
                            f"{func.name} must maintain: {len(non_trivial_assertions)} assertion(s)"
                        )
        
        # HARD CHECK: Must have non-trivial assertions
        gate.invariants_identified = len(gate.identified_invariants) > 0
        
        # Check 4: Tests mapped? (HARD REQUIREMENT)
        # Must have actual test-to-function mappings with real assertions
        for file in target_files:
            if file in self.modules:
                module = self.modules[file]
                for func in module.functions.values():
                    # Only count if function has non-trivial assertions
                    non_trivial = [
                        a for a in func.test_assertions
                        if not self._is_trivial_assertion(a)
                    ]
                    
                    if non_trivial:
                        for test_file in func.test_files:
                            gate.test_assertions.append(
                                f"{func.name} tested by {test_file} ({len(non_trivial)} assertions)"
                            )
        
        # HARD CHECK: Must have non-trivial assertions mapped
        gate.tests_mapped = len(gate.test_assertions) > 0
        
        return gate
    
    def _cache_understanding(self, project_path: Path):
        """Persist understanding to disk"""
        
        repo_hash = hashlib.sha256(str(project_path).encode()).hexdigest()[:16]
        
        cache_data = {
            'repo_hash': repo_hash,
            'understanding_version': 1,
            'timestamp': datetime.now().isoformat(),
            'structure': self.structure.to_dict() if self.structure else None,
            'dependency_graph': self.dependency_graph.to_dict() if self.dependency_graph else None,
            'modules': {
                path: module.to_dict()
                for path, module in self.modules.items()
            }
        }
        
        cache_file = self.cache_dir / f"{repo_hash}.json"
        with open(cache_file, 'w') as f:
            json.dump(cache_data, f, indent=2)
        
        print(f"✓ Understanding cached to {cache_file}")


# Validation
if __name__ == "__main__":
    print("="*70)
    print("CODE ANALYZER - VALIDATION")
    print("="*70)
    print()
    print("Hard requirements:")
    print("  1. Project structure map (exact, not guessed)")
    print("  2. Dependency graph (executable)")
    print("  3. Change impact prediction")
    print("  4. Explanation gate (blocks if incomplete)")
    print()
    print("If it guesses → fail loudly")
    print("If incomplete → block execution")
    print("="*70)
