"""
Playwright Code Generator
Converts AI discoveries into executable Python Playwright test code

REFACTORED: Now delegates to modular structure (pw_core, pw_loaders, pw_matchers, pw_codegen, pw_utils)
Maintains backward compatibility with existing API
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

from generator.pw_loaders.execution_loader import load_execution
from generator.pw_loaders.discovery_loader import load_discoveries
from generator.pw_loaders.registry_loader import detect_registry_files
from generator.pw_core.generator import PlaywrightGeneratorCore
from generator.pw_codegen.code_formatter import generate_test_name

logger = logging.getLogger(__name__)


class PlaywrightGenerator:
    """Generate Python Playwright test code from AI discovery metadata
    
    REFACTORED: Now uses modular structure while maintaining backward compatibility
    All implementation has been moved to:
    - generator/pw_core/generator.py (orchestration)
    - generator/pw_loaders/ (data loading)
    - generator/pw_matchers/ (step/action matching)
    - generator/pw_codegen/ (code generation)
    - generator/pw_utils/ (utilities)
    """
    
    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path(__file__).parent.parent
        self.discoveries_dir = self.project_root / 'storage' / 'discoveries'
        self.executions_dir = self.project_root / 'storage' / 'executions'
        self.generated_tests_dir = self.project_root / 'tests' / 'generated'
        self.generated_tests_metadata_dir = self.project_root / 'storage' / 'generated_tests'
        self.element_maps_dir = self.project_root / 'element_maps'
        self.generated_tests_dir.mkdir(parents=True, exist_ok=True)
        self.generated_tests_metadata_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize core generator
        self.core_generator = PlaywrightGeneratorCore(self.project_root)
    
    def generate(self, execution_id: str, test_name: str = None) -> Dict[str, Any]:
        """
        Generate Playwright test from successful AI execution
        
        Args:
            execution_id: The execution ID (e.g., 'exec_172351d5')
            test_name: Optional custom test name
            
        Returns:
            Dict with 'code', 'filename', 'metadata'
        """
        # Load execution data using new loaders
        execution = load_execution(execution_id, self.executions_dir)
        discoveries = load_discoveries(execution_id, self.discoveries_dir, self.executions_dir)
        
        # Detect all registry files needed (multi-registry support)
        registry_files = detect_registry_files(execution, self.element_maps_dir)
        
        # Generate test name
        if not test_name:
            test_name = generate_test_name(execution['story'])
        
        # Generate code using core generator
        code = self.core_generator.generate_test_code(
            execution, discoveries, test_name, registry_files
        )
        
        # Save to file
        filename = f"{test_name}.py"
        filepath = self.generated_tests_dir / filename
        with open(filepath, 'w') as f:
            f.write(code)
        
        # Save metadata
        metadata = {
            'execution_id': execution_id,
            'test_name': test_name,
            'filename': str(filepath),
            'generated_at': datetime.utcnow().isoformat() + 'Z',
            'story': execution['story'],
            'discoveries_count': len(discoveries.get('discoveries', []))
        }
        
        metadata_file = self.generated_tests_metadata_dir / f'{execution_id}_test.json'
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        return {
            'code': code,
            'filename': filename,
            'filepath': str(filepath),
            'metadata': metadata
        }


# Example usage
if __name__ == '__main__':
    generator = PlaywrightGenerator()
    result = generator.generate('exec_172351d5')
    print(f"Generated: {result['filename']}")
    print(f"Path: {result['filepath']}")
