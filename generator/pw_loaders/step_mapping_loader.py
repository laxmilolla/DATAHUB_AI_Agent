"""
Step Mapping Loader - Load execution-specific step_number mappings
HYBRID APPROACH: Loads step_number → element_name mapping per execution
"""
import json
import logging
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


def load_step_mapping(execution_id: str, element_maps_dir: Path) -> Optional[Dict]:
    """
    Load execution-specific step_number mapping
    
    Args:
        execution_id: Execution ID (e.g., 'exec_1768252931')
        element_maps_dir: Base directory for element maps
    Returns:
        Step mapping dictionary or None if not found
    """
    try:
        # Look for step mapping in execution-specific directory
        step_mappings_dir = element_maps_dir / execution_id
        
        if not step_mappings_dir.exists():
            logger.warning(f"⚠️  Step mapping directory not found: {step_mappings_dir}")
            return None
        
        # Find all step mapping files (could be multiple pages)
        mapping_files = list(step_mappings_dir.rglob("*_steps.json"))
        
        if not mapping_files:
            logger.warning(f"⚠️  No step mapping files found in {step_mappings_dir}")
            return None
        
        # Merge all mappings (if multiple pages)
        merged_mapping = {
            "execution_id": execution_id,
            "step_mapping": {},
            "reverse_mapping": {}
        }
        
        for mapping_file in mapping_files:
            try:
                with open(mapping_file, 'r') as f:
                    mapping_data = json.load(f)
                
                # Merge step_mapping
                merged_mapping["step_mapping"].update(mapping_data.get("step_mapping", {}))
                
                # Merge reverse_mapping
                merged_mapping["reverse_mapping"].update(mapping_data.get("reverse_mapping", {}))
                
                logger.info(f"✅ Loaded step mapping from {mapping_file.name}")
            except Exception as e:
                logger.warning(f"⚠️  Failed to load step mapping from {mapping_file}: {e}")
        
        if merged_mapping["step_mapping"]:
            logger.info(f"✅ Loaded step mapping: {len(merged_mapping['step_mapping'])} steps")
            return merged_mapping
        else:
            logger.warning(f"⚠️  Step mapping is empty")
            return None
            
    except Exception as e:
        logger.error(f"❌ Failed to load step mapping: {e}", exc_info=True)
        return None


def get_element_name_for_step(step_num: int, step_mapping: Dict) -> Optional[str]:
    """
    Get element name for a story step number using step mapping
    
    Args:
        step_num: Story step number
        step_mapping: Step mapping dictionary
    Returns:
        Element name or None if not found
    """
    if not step_mapping:
        return None
    
    step_mapping_dict = step_mapping.get("step_mapping", {})
    step_key = str(step_num)
    
    if step_key in step_mapping_dict:
        mapping_entry = step_mapping_dict[step_key]
        
        # Handle optional steps
        if isinstance(mapping_entry, dict):
            element_name = mapping_entry.get("element")
            # Return None if element didn't appear (optional step)
            if element_name is None and mapping_entry.get("is_optional"):
                return None
            return element_name
        else:
            # Simple string mapping (backward compatibility)
            return mapping_entry
    
    return None


def is_optional_step(step_num: int, step_mapping: Dict) -> bool:
    """
    Check if a step is optional
    
    Args:
        step_num: Story step number
        step_mapping: Step mapping dictionary
    Returns:
        True if step is optional, False otherwise
    """
    if not step_mapping:
        return False
    
    step_mapping_dict = step_mapping.get("step_mapping", {})
    step_key = str(step_num)
    
    if step_key in step_mapping_dict:
        mapping_entry = step_mapping_dict[step_key]
        if isinstance(mapping_entry, dict):
            return mapping_entry.get("is_optional", False)
    
    return False

