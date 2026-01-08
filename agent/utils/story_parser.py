"""
Story Parser - Parse story into steps with metadata
Extracted from bedrock_playwright_agent.py lines 64-136
"""
import re
import logging
from typing import Dict

logger = logging.getLogger(__name__)


class StoryParser:
    """Parse story into steps with metadata"""
    
    def parse(self, story: str) -> Dict[int, Dict]:
        """
        Parse story and extract metadata for each step
        Returns: {step_number: {metadata}}
        """
        logger.info("📖 Parsing story metadata...")
        parsed_steps = {}
        
        # Split into steps
        lines = story.split('\n')
        for line in lines:
            line = line.strip()
            if not line or not line.startswith('Step'):
                continue
            
            # Extract step number: "Step 4:" or "4."
            step_match = re.match(r'Step\s+(\d+)[\.:)]?\s*(.+)', line, re.IGNORECASE)
            if not step_match:
                continue
            
            step_num = int(step_match.group(1))
            step_text = step_match.group(2).lower()
            
            # Extract metadata from step text
            metadata = self._extract_step_metadata(step_text)
            parsed_steps[step_num] = metadata
            logger.info(f"  Step {step_num}: {metadata}")
        
        logger.info(f"✅ Parsed {len(parsed_steps)} steps with metadata")
        return parsed_steps
    
    def _extract_step_metadata(self, step_text: str) -> Dict:
        """
        Extract metadata from step text
        Returns: {type, location, parent_hint, etc.}
        """
        metadata = {"text": step_text}
        
        # Detect TYPE
        element_type = self._detect_element_type(step_text)
        if element_type:
            metadata["type"] = element_type
        
        # Detect LOCATION
        if "sidebar" in step_text or "filter panel" in step_text or "left" in step_text:
            metadata["location"] = "sidebar"
        elif "table" in step_text or "bottom" in step_text or "main" in step_text or "content" in step_text:
            metadata["location"] = "table"
        
        # Detect PARENT/NESTED
        if "nested" in step_text or "inner" in step_text or "within" in step_text or "inside" in step_text:
            metadata["nested"] = True
            
        # Extract PARENT HINT from context (e.g., "in the Diagnosis section")
        parent_hint = self._extract_parent_hint(step_text)
        if parent_hint:
            metadata["parent_hint"] = parent_hint
        
        # Detect DEPTH preference
        if "top" in step_text or "main" in step_text or "primary" in step_text:
            metadata["prefer_depth"] = 0  # Top-level
        elif "first level" in step_text:
            metadata["prefer_depth"] = 1
        elif "second level" in step_text:
            metadata["prefer_depth"] = 2
        
        return metadata
    
    def _detect_element_type(self, step_text: str) -> str:
        """
        Detect element type (tab, accordion, checkbox)
        """
        if "tab" in step_text:
            return "tab"
        elif "accordion" in step_text or "expand" in step_text:
            return "accordion"
        elif "checkbox" in step_text or "check box" in step_text:
            return "checkbox"
        return None
    
    def _extract_parent_hint(self, step_text: str) -> str:
        """
        Extract parent hint from step text
        """
        parent_patterns = [
            r'in (?:the )?(\w+)(?: section| accordion| area)?',
            r'inside (?:the )?(\w+)',
            r'within (?:the )?(\w+)',
            r'under (?:the )?(\w+)'
        ]
        for pattern in parent_patterns:
            match = re.search(pattern, step_text)
            if match:
                parent_hint = match.group(1).lower()
                # Exclude common words
                if parent_hint not in ['the', 'a', 'an', 'this', 'that', 'expanded', 'collapsed']:
                    return parent_hint
        return None


