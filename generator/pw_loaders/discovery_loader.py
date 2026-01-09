"""
Discovery Loader - Load discovery JSON data
Extracted from playwright_generator.py
"""
import json
import logging
from pathlib import Path
from typing import Dict

logger = logging.getLogger(__name__)


def load_discoveries(execution_id: str, discoveries_dir: Path, executions_dir: Path = None) -> Dict:
    """
    Load discovery metadata JSON
    Args:
        execution_id: Execution ID (e.g., 'exec_172351d5')
        discoveries_dir: Directory containing discovery JSON files
        executions_dir: Optional directory containing execution JSON files (to check for embedded discoveries)
    Returns:
        Discovery dictionary with 'discoveries' list (empty if file doesn't exist)
    """
    # First, try to load from separate discovery file
    file_path = discoveries_dir / f'{execution_id}_discoveries.json'
    if file_path.exists():
        with open(file_path, 'r') as f:
            discoveries = json.load(f)
        
        discoveries_list = discoveries.get('discoveries', [])
        logger.info(f"✅ Loaded {len(discoveries_list)} discoveries from discovery file for {execution_id}")
        return discoveries
    
    # If separate discovery file doesn't exist, check execution file
    if executions_dir:
        exec_file_path = executions_dir / f'{execution_id}.json'
        if exec_file_path.exists():
            try:
                with open(exec_file_path, 'r') as f:
                    execution_data = json.load(f)
                
                discoveries_list = execution_data.get('discoveries', [])
                if discoveries_list:
                    logger.info(f"✅ Loaded {len(discoveries_list)} discoveries from execution file for {execution_id}")
                    return {'discoveries': discoveries_list}
            except Exception as e:
                logger.warning(f"⚠️  Failed to load discoveries from execution file: {e}")
    
    logger.info(f"ℹ️  Discovery file not found for {execution_id}, returning empty discoveries")
    return {'discoveries': []}


def validate_discoveries(discoveries: Dict) -> bool:
    """
    Validate discovery data structure
    Args:
        discoveries: Discovery dictionary
    Returns:
        True if valid, False otherwise
    """
    if 'discoveries' not in discoveries:
        logger.warning("⚠️ Discoveries missing 'discoveries' field")
        return False
    
    if not isinstance(discoveries['discoveries'], list):
        logger.warning("⚠️ Discoveries 'discoveries' field is not a list")
        return False
    
    return True


