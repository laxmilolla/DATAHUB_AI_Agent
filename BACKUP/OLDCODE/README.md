# Old Code Archive

This folder contains deprecated code files that are no longer used in the refactored codebase.

## Files Moved:
- `bedrock_playwright_agent.py` - Original monolithic agent (replaced by modular structure in `agent/core/`, `agent/tools/`, etc.)
- `bedrock_playwright_agent.py.backup_*` - Backup files
- `bedrock_playwright_agent.py.bak2` - Backup file
- `temp_method.py` - Temporary methods file (if present)

## Do NOT import from these files
The refactored codebase uses:
- `agent.core.agent` - Main agent orchestrator
- `agent.tools.*` - Tool handlers
- `agent.browser.*` - Browser management
- `agent.discovery.*` - Discovery tracking
- `agent.llm.*` - LLM integration

These old files are kept for reference only.
