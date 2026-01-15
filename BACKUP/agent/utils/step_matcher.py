"""
Step Matcher - Match actions to story steps by content
Determines which story step an action corresponds to based on content matching
"""
import re
import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class StepMatcher:
    """Match actions to story steps by content"""
    
    def __init__(self, parsed_steps: Dict[str, Dict], story: str):
        """
        Initialize step matcher
        Args:
            parsed_steps: Parsed story steps with identifiers {"1": {...}, "1a": {...}, "2": {...}}
            story: Full story text
        """
        self.parsed_steps = parsed_steps
        self.story = story
        self.completed_step_identifiers = set()  # Track which steps have been matched
        
        # Build story step text lookup
        self.story_lines = story.split('\n')
        self.step_texts = {}  # {step_identifier: step_text}
        for line in self.story_lines:
            line = line.strip()
            if not line.startswith('Step'):
                continue
            
            # Extract step identifier
            step_match = re.match(r'Step\s+(\d+)\s*([a-z])?\s*[\.:)]?\s*(.+)', line, re.IGNORECASE)
            if step_match:
                step_num = step_match.group(1)
                sub_step = step_match.group(2)
                step_text = step_match.group(3).strip()
                
                step_identifier = f"{step_num}{sub_step.lower()}" if sub_step else step_num
                self.step_texts[step_identifier] = step_text
    
    def predict_step_from_input(self, tool: str, tool_input: Dict) -> Optional[str]:
        """
        Predict step identifier BEFORE tool execution (for tool context)
        CRITICAL: MUST follow sequential order - only considers next sequential step(s)
        Args:
            tool: Tool name (browser_click, browser_fill, etc.)
            tool_input: Tool input dict (contains selector, url, text, etc.)
        Returns:
            Predicted step identifier (e.g., "1", "1a", "2") or None if no match
        """
        # Get action content without result (prediction)
        action_content = self._extract_action_content(tool, tool_input, "")
        
        # CRITICAL: Find highest completed step number to enforce sequential order
        highest_completed = 0
        for step_id in self.completed_step_identifiers:
            step_num_match = re.match(r'(\d+)', step_id)
            if step_num_match:
                step_num = int(step_num_match.group(1))
                highest_completed = max(highest_completed, step_num)
        
        # Find best matching story step - ONLY consider steps AFTER highest completed
        best_match = None
        best_score = 0
        
        # Sort steps to process in sequential order
        sorted_steps = sorted(self.step_texts.items(), 
                             key=lambda x: (int(re.match(r'(\d+)', x[0]).group(1)), x[0]))
        
        for step_identifier, step_text in sorted_steps:
            # Get step metadata
            step_metadata = self.parsed_steps.get(step_identifier, {})
            
            # Skip if already matched (unless it's optional and can repeat)
            if step_identifier in self.completed_step_identifiers:
                # Check if step is optional (can appear multiple times)
                if not step_metadata.get('is_optional', False):
                    continue
            
            # CRITICAL: Only consider steps AFTER highest completed step
            step_num_match = re.match(r'(\d+)', step_identifier)
            if step_num_match:
                step_num = int(step_num_match.group(1))
                if step_num <= highest_completed:
                    continue  # Skip steps that are before or equal to highest completed
            
            # Calculate match score
            score = self._calculate_match_score(tool, action_content, step_text, step_metadata)
            
            # CRITICAL: Add sequential priority bonus - next step gets huge boost
            step_num_match = re.match(r'(\d+)', step_identifier)
            if step_num_match:
                step_num = int(step_num_match.group(1))
                # Next sequential step gets +200 bonus (ensures it wins even with lower content match)
                if step_num == highest_completed + 1:
                    score += 200
                    logger.debug(f"  🎯 Sequential priority bonus (+200) for Step {step_identifier} (next step)")
            
            if score > best_score:
                best_score = score
                best_match = step_identifier
        
        # Use lower threshold for prediction (more lenient)
        threshold = 40  # Lower threshold for prediction
        if best_match and best_score >= threshold:
            logger.info(f"  🔮 Predicted step ({tool}) → Step {best_match} (score: {best_score:.1f})")
            return best_match
        else:
            logger.debug(f"  ⚠️  No prediction for action ({tool}), best score: {best_score:.1f}")
            return None
    
    def match_action_to_step(self, tool: str, tool_input: Dict, result: str = "") -> Optional[str]:
        """
        Match an action to a story step by content (AFTER execution)
        CRITICAL: MUST follow sequential order - only considers next sequential step(s)
        Args:
            tool: Tool name (browser_click, browser_fill, etc.)
            tool_input: Tool input dict (contains selector, url, text, etc.)
            result: Tool result text
        Returns:
            Step identifier (e.g., "1", "1a", "2") or None if no match
        """
        # Get action content
        action_content = self._extract_action_content(tool, tool_input, result)
        
        # CRITICAL: Find highest completed step number to enforce sequential order
        highest_completed = 0
        for step_id in self.completed_step_identifiers:
            step_num_match = re.match(r'(\d+)', step_id)
            if step_num_match:
                step_num = int(step_num_match.group(1))
                highest_completed = max(highest_completed, step_num)
        
        # Find best matching story step - ONLY consider steps AFTER highest completed
        best_match = None
        best_score = 0
        
        # Sort steps to process in sequential order
        sorted_steps = sorted(self.step_texts.items(), 
                             key=lambda x: (int(re.match(r'(\d+)', x[0]).group(1)), x[0]))
        
        for step_identifier, step_text in sorted_steps:
            # Get step metadata
            step_metadata = self.parsed_steps.get(step_identifier, {})
            
            # Skip if already matched (unless it's optional and can repeat)
            if step_identifier in self.completed_step_identifiers:
                # Check if step is optional (can appear multiple times)
                if not step_metadata.get('is_optional', False):
                    continue
            
            # CRITICAL: Only consider steps AFTER highest completed step
            step_num_match = re.match(r'(\d+)', step_identifier)
            if step_num_match:
                step_num = int(step_num_match.group(1))
                if step_num <= highest_completed:
                    continue  # Skip steps that are before or equal to highest completed
            
            # Calculate match score
            score = self._calculate_match_score(tool, action_content, step_text, step_metadata)
            
            # CRITICAL: Add sequential priority bonus - next step gets huge boost
            step_num_match = re.match(r'(\d+)', step_identifier)
            if step_num_match:
                step_num = int(step_num_match.group(1))
                # Next sequential step gets +200 bonus (ensures it wins even with lower content match)
                if step_num == highest_completed + 1:
                    score += 200
                    logger.debug(f"  🎯 Sequential priority bonus (+200) for Step {step_identifier} (next step)")
            
            if score > best_score:
                best_score = score
                best_match = step_identifier
        
        # Only match if score is high enough
        threshold = 50  # Minimum score to consider a match
        if best_match and best_score >= threshold:
            logger.info(f"  ✅ Matched action ({tool}) to Step {best_match} (score: {best_score:.1f})")
            self.completed_step_identifiers.add(best_match)
            return best_match
        else:
            logger.debug(f"  ⚠️  No match found for action ({tool}), best score: {best_score:.1f}")
            return None
    
    def _extract_action_content(self, tool: str, tool_input: Dict, result: str) -> Dict:
        """Extract content from action for matching"""
        content = {
            "tool": tool,
            "selector": "",
            "text": "",
            "url": "",
            "result": result.lower() if result else ""
        }
        
        if tool == "browser_click":
            content["selector"] = tool_input.get("selector", "").lower()
            content["text"] = tool_input.get("element_description", "").lower()
            # Extract clicked text from result
            if result and "clicked" in result.lower():
                clicked_match = re.search(r'clicked\s+(.+?)(?:\s+-|\s*$)', result.lower())
                if clicked_match:
                    content["text"] = clicked_match.group(1).strip()
        
        elif tool == "browser_fill":
            content["selector"] = tool_input.get("selector", "").lower()
            content["text"] = tool_input.get("text", "").lower()
        
        elif tool == "browser_navigate":
            content["url"] = tool_input.get("url", "").lower()
        
        elif tool == "browser_evaluate":
            # Wait steps - extract duration
            if "wait" in result.lower():
                wait_match = re.search(r'wait(?:ed)?\s+(\d+)', result.lower())
                if wait_match:
                    content["duration"] = int(wait_match.group(1))
        
        return content
    
    def _calculate_match_score(self, tool: str, action_content: Dict, step_text: str, step_metadata: Dict) -> float:
        """Calculate match score between action and story step"""
        score = 0
        step_lower = step_text.lower()
        
        # PRIORITY 1: Tool type match (REQUIRED - reject mismatches)
        tool_matches = False
        if tool == "browser_navigate" and ("go to" in step_lower or "navigate" in step_lower):
            score += 100
            tool_matches = True
        elif tool == "browser_click" and ("click" in step_lower or "press" in step_lower or "tap" in step_lower):
            score += 100
            tool_matches = True
        elif tool == "browser_fill" and ("enter" in step_lower or "fill" in step_lower or "type" in step_lower or "input" in step_lower):
            score += 100
            tool_matches = True
        elif tool == "browser_evaluate" and "wait" in step_lower:
            score += 100
            tool_matches = True
        elif tool == "browser_verify" and ("verify" in step_lower or "check" in step_lower):
            score += 100
            tool_matches = True
        
        # FIX: Reject tool type mismatches (screenshot ≠ click, click ≠ verify)
        if not tool_matches:
            # Check for explicit mismatches
            if tool == "browser_screenshot" and ("click" in step_lower or "press" in step_lower):
                return 0  # Screenshot cannot match click step
            if tool == "browser_click" and ("verify" in step_lower or "check" in step_lower) and "click" not in step_lower:
                return 0  # Click cannot match verify step (unless it also says click)
            if tool == "browser_fill" and ("verify" in step_lower or "check" in step_lower) and "fill" not in step_lower:
                return 0  # Fill cannot match verify step
            # If no tool match and no explicit mismatch, return low score
            return 10  # Very low score for tool mismatch
        
        # PRIORITY 2: Exact text match (very high score)
        action_text = action_content.get("text", "")
        action_selector = action_content.get("selector", "")
        
        if action_text:
            # Extract text from selector (e.g., "text=Login" → "login")
            if "text=" in action_selector:
                selector_text = action_selector.split("text=")[1].strip().strip("'\"")
                if selector_text.lower() in step_lower or step_lower in selector_text.lower():
                    score += 90
            
            # Direct text match
            if action_text in step_lower:
                score += 90
            elif step_lower in action_text:
                score += 80
        
        # PRIORITY 3: URL match for navigation
        if tool == "browser_navigate":
            url = action_content.get("url", "")
            if url and url in step_lower:
                score += 100
        
        # PRIORITY 4: Wait duration match
        if tool == "browser_evaluate" and "wait" in step_lower:
            duration = action_content.get("duration")
            if duration:
                # Check if step mentions the same duration
                duration_match = re.search(r'(\d+)\s*seconds?', step_lower)
                if duration_match:
                    step_duration = int(duration_match.group(1))
                    if duration == step_duration:
                        score += 90
        
        # PRIORITY 5: Element type match from metadata
        element_type = step_metadata.get("type")
        if element_type:
            if element_type == "link" and ("link" in step_lower or "href" in action_selector):
                score += 50
            elif element_type == "button" and ("button" in step_lower or "button" in action_selector):
                score += 50
            elif element_type == "input" and tool == "browser_fill":
                score += 50
        
        # PRIORITY 6: Keyword overlap
        action_keywords = set(action_text.split() + action_selector.split())
        step_keywords = set(step_lower.split())
        common_keywords = action_keywords.intersection(step_keywords)
        if len(common_keywords) > 0:
            score += len(common_keywords) * 10
        
        # Penalty for tool mismatch
        if tool == "browser_click" and "fill" in step_lower:
            score -= 50
        elif tool == "browser_fill" and "click" in step_lower and "fill" not in step_lower:
            score -= 50
        
        return score
    
    def get_completed_steps(self) -> List[str]:
        """Get list of completed step identifiers"""
        return sorted(list(self.completed_step_identifiers))
    
    def reset(self):
        """Reset completed steps (for testing)"""
        self.completed_step_identifiers.clear()

