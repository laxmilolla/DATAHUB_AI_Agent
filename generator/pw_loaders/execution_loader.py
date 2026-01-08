"""
Execution Loader - Load execution JSON data
Extracted from playwright_generator.py
"""
import json
import logging
from pathlib import Path
from typing import Dict

logger = logging.getLogger(__name__)


def load_execution(execution_id: str, executions_dir: Path) -> Dict:
    """
    Load execution results JSON
    Args:
        execution_id: Execution ID (e.g., 'exec_172351d5')
        executions_dir: Directory containing execution JSON files
    Returns:
        Execution dictionary
    Raises:
        FileNotFoundError: If execution file doesn't exist
    """
    file_path = executions_dir / f'{execution_id}.json'
    if not file_path.exists():
        raise FileNotFoundError(f"Execution {execution_id} not found at {file_path}")
    
    with open(file_path, 'r') as f:
        execution = json.load(f)
    
    logger.info(f"✅ Loaded execution {execution_id}")
    return execution


def validate_execution(execution: Dict) -> bool:
    """
    Validate execution data structure
    Args:
        execution: Execution dictionary
    Returns:
        True if valid, False otherwise
    """
    required_fields = ['execution_id', 'story', 'actions_taken']
    for field in required_fields:
        if field not in execution:
            logger.warning(f"⚠️ Execution missing required field: {field}")
            return False
    
    return True

