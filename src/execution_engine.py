# execution_engine.py
"""
ExecutionEngine: Run code and capture evidence
"""

import subprocess
import tempfile
import time
from pathlib import Path
from typing import Tuple
from datetime import datetime
import hashlib

from knowledge_core import OutcomeType, FailureSeverity, StructuredContext

class ExecutionEngine:
    """Execute code and capture observable results"""
    
    def run_simple(self, code: str, language: str = "python") -> Tuple[bool, str, float]:
        """
        Simplified execution for testing.
        Returns: (success, output, time_ms)
        """
        start = time.time()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / self._get_filename(language)
            filepath.write_text(code)
            
            try:
                result = subprocess.run(
                    self._get_command(language, str(filepath)),
                    capture_output=True,
                    timeout=5,
                    cwd=tmpdir
                )
                
                elapsed = (time.time() - start) * 1000
                output = result.stdout.decode() + result.stderr.decode()
                success = result.returncode == 0
                
                return success, output, elapsed
                
            except subprocess.TimeoutExpired:
                elapsed = (time.time() - start) * 1000
                return False, "Timeout", elapsed
            except Exception as e:
                elapsed = (time.time() - start) * 1000
                return False, str(e), elapsed
    
    def _get_filename(self, language: str) -> str:
        extensions = {
            'python': 'test.py',
            'javascript': 'test.js',
            'go': 'test.go'
        }
        return extensions.get(language.lower(), 'test.txt')
    
    def _get_command(self, language: str, filepath: str):
        commands = {
            'python': ['python', filepath],
            'javascript': ['node', filepath],
            'go': ['go', 'run', filepath]
        }
        return commands.get(language.lower(), ['cat', filepath])
