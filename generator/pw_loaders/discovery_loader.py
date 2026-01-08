"""
Discovery Loader - Load discovery JSON data
Extracted from playwright_generator.py
"""
import json
import logging
from pathlib import Path
from typing import Dict

logger = logging.getLogger(__name__)


def load_discoveries(execution_id: str, discoveries_dir: Path) -> Dict:
    """
    Load discovery metadata JSON
    Args:
        execution_id: Execution ID (e.g., 'exec_172351d5')
        discoveries_dir: Directory containing discovery JSON files
    Returns:
        Discovery dictionary with 'discoveries' list (empty if file doesn't exist)
    """
    file_path = discoveries_dir / f'{execution_id}_discoveries.json'
    if not file_path.exists():
        logger.info(f"ℹ️  Discovery file not found for {execution_id}, returning empty discoveries")
        return {'discoveries': []}
    
    with open(file_path, 'r') as f:
        discoveries = json.load(f)
    
    discoveries_list = discoveries.get('discoveries', [])
    logger.info(f"✅ Loaded {len(discoveries_list)} discoveries for {execution_id}")
    return discoveries


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

