# BACKUP - Existing Codebase

This folder contains a complete backup of the existing codebase before refactoring.

## Structure

All existing code has been copied here for reference and methodical pulling.

## What's Backed Up

- `agent/` - Agent core code
- `api/` - API routes
- `web/` - Web templates and static files
- `generator/` - Playwright generators
- `validator/` - Test runner and validator
- `utils/` - Utility functions
- `storage/` - Storage structure (reference only)
- `tests/` - Test files
- `element_maps/` - Element registry files
- All root-level Python files
- All root-level documentation files

## Purpose

This backup allows us to:
1. Reference existing code patterns
2. Pull components methodically
3. Maintain original codebase while refactoring
4. Rollback if needed

## Usage

When pulling code from BACKUP:
1. Study the code in BACKUP
2. Copy/adapt what's needed
3. Integrate into REFACTOR folder
4. Test before moving to next component

## Important

- This is a backup - don't modify files here
- Use as reference for patterns and code structure
- Pull methodically, one component at a time
