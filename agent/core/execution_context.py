"""
Execution Context - Manage execution state
Extracted from bedrock_playwright_agent.py lines 44-63, 3248-3255, 3318-3330
"""
import time
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class ExecutionContext:
    """Manage execution state"""
    
    def __init__(self, execution_id: str):
        """
        Initialize execution context
        Args:
            execution_id: Unique execution ID
        """
        self.execution_id = execution_id
        self.current_step_number = 0
        self.current_step_identifier = None  # Track current step identifier ("1", "1a", "2", etc.)
        self.parsed_steps: Dict[str, Dict] = {}  # Changed to string keys for identifiers like "1", "1a"
        self.story: str = ""
        self.actions_taken: List[Dict] = []
        self.screenshots: List[str] = []
        self.status: str = "running"
        self.started_at: float = time.time()
        self.completed_at: Optional[float] = None
        self.duration: Optional[float] = None
        self.error: Optional[str] = None
        self.summary: Optional[str] = None
    
    def increment_step(self) -> None:
        """Increment current step number"""
        self.current_step_number += 1
    
    def get_current_step_metadata(self) -> Dict:
        """Get metadata for current step"""
        # Try step_identifier first, then fall back to step_number as string
        if self.current_step_identifier:
            return self.parsed_steps.get(self.current_step_identifier, {})
        return self.parsed_steps.get(str(self.current_step_number), {})
    
    def add_action(self, action: Dict) -> None:
        """Add action to results"""
        self.actions_taken.append(action)
    
    def add_screenshot(self, screenshot: str) -> None:
        """Add screenshot to results"""
        self.screenshots.append(screenshot)
    
    def set_story(self, story: str) -> None:
        """Set story for context"""
        self.story = story
    
    def set_parsed_steps(self, parsed_steps: Dict[str, Dict]) -> None:
        """Set parsed steps (now uses string identifiers like '1', '1a', '2')"""
        self.parsed_steps = parsed_steps
    
    def mark_completed(self, summary: str = None) -> None:
        """Mark execution as completed"""
        self.status = "completed"
        self.completed_at = time.time()
        self.duration = self.completed_at - self.started_at
        if summary:
            self.summary = summary
    
    def mark_error(self, error: str) -> None:
        """Mark execution as error"""
        self.status = "error"
        self.error = error
    
    def get_results(self) -> Dict[str, Any]:
        """Get final results dict"""
        return {
            "execution_id": self.execution_id,
            "story": self.story,
            "parsed_steps": self.parsed_steps,  # FIX: Include parsed_steps for TOTP detection
            "actions_taken": self.actions_taken,
            "screenshots": self.screenshots,
            "discoveries": getattr(self, 'discoveries', []),  # Include discoveries if set
            "status": self.status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration": self.duration,
            "error": self.error,
            "summary": self.summary
        }


