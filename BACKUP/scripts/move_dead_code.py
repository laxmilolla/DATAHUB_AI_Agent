#!/usr/bin/env python3
"""
Move Dead Code to TO_BE_DELETED folder
Safely moves unused code instead of deleting it immediately
"""
import shutil
from pathlib import Path
from datetime import datetime

# Files/folders to move (from DEAD_CODE_REPORT.md analysis)
DEAD_CODE_TO_MOVE = {
    # Experimented folder (moved features)
    'Experimented/': 'Moved features - no longer used',
    
    # Test/debug scripts
    'experiment_extended_test.py': 'Test script - not part of main app',
    'extract_all_elements.py': 'Extraction script - not part of main app',
    'extract_datasubmissions_elements.py': 'Extraction script - not part of main app',
    'extract_input_fields.py': 'Extraction script - not part of main app',
    'test_add_steps.py': 'Test script - not part of main app',
    'test_cdp_connection.py': 'Test script - not part of main app',
    
    # Unused utils (reviewed - not imported anywhere)
    'utils/capture_filters_graphql.py': 'GraphQL capture - not imported',
    'utils/capture_graphql.py': 'GraphQL capture - not imported',
    'utils/check_api_calls.py': 'API call checker - not imported',
    'utils/compare_maps.py': 'Map comparison - not imported',
    'utils/create_element_map.py': 'Element map creation - not imported',
    'utils/fetch_and_parse_html.py': 'HTML fetcher - not imported',
    'utils/html_parser.py': 'HTML parser - not imported in main code',
    'utils/playwright_tree_parser.py': 'Tree parser - not imported',
    'utils/test_element_matching.py': 'Test matching - not imported',
    'utils/xpath_builder.py': 'XPath builder - not imported',
}

# Files to KEEP (still used)
KEEP_FILES = {
    'utils/element_registry.py': 'Used by agent',
    'utils/otp_helper.py': 'Used for TOTP',
    'utils/table_verification.py': 'Used by browser_verify',
    'analyze_dead_code.py': 'Analysis tool',
    'move_dead_code.py': 'This script',
}

def create_backup_folder(project_root: Path) -> Path:
    """Create TO_BE_DELETED folder with timestamp"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_folder = project_root / 'TO_BE_DELETED' / f'moved_{timestamp}'
    backup_folder.mkdir(parents=True, exist_ok=True)
    return backup_folder

def move_file_or_folder(source: Path, dest_folder: Path, reason: str) -> bool:
    """Move a file or folder to backup location"""
    try:
        if not source.exists():
            print(f"⚠️  {source} does not exist - skipping")
            return False
        
        # Create destination path maintaining structure
        dest = dest_folder / source.name
        
        # If it's a folder, move entire folder
        if source.is_dir():
            print(f"📁 Moving folder: {source} -> {dest}")
            print(f"   Reason: {reason}")
            shutil.move(str(source), str(dest))
        else:
            # Create parent directory if needed
            dest.parent.mkdir(parents=True, exist_ok=True)
            print(f"📄 Moving file: {source} -> {dest}")
            print(f"   Reason: {reason}")
            shutil.move(str(source), str(dest))
        
        return True
    except Exception as e:
        print(f"❌ Error moving {source}: {e}")
        return False

def create_readme(backup_folder: Path, moved_items: list):
    """Create README in backup folder explaining what was moved"""
    readme_content = f"""# Dead Code Moved Here

**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Purpose
This folder contains code that was identified as dead/unused and moved here for safe testing.
After verifying the application still works, these files can be permanently deleted.

## Items Moved

"""
    for item, reason in moved_items:
        readme_content += f"- **{item}**: {reason}\n"
    
    readme_content += f"""
## Testing Checklist

Before deleting this folder, verify:

- [ ] Excel upload works
- [ ] Excel test generation works (Python)
- [ ] Excel test generation works (TypeScript)
- [ ] Excel test execution works
- [ ] Registry lookups work
- [ ] TOTP generation works
- [ ] Screenshots are captured
- [ ] Results page displays correctly

## Safe to Delete?

Once all tests pass, this folder can be safely deleted.

**DO NOT DELETE** until:
1. Application runs without errors
2. All Excel features work
3. No import errors in logs
4. At least 1 successful test run completed
"""
    
    readme_path = backup_folder / 'README.md'
    with open(readme_path, 'w') as f:
        f.write(readme_content)
    print(f"✅ Created README: {readme_path}")

def main():
    project_root = Path(__file__).parent
    
    print("="*80)
    print("🗑️  MOVING DEAD CODE TO TO_BE_DELETED")
    print("="*80)
    print(f"Project root: {project_root}")
    print()
    
    # Create backup folder
    backup_folder = create_backup_folder(project_root)
    print(f"📂 Backup folder: {backup_folder}")
    print()
    
    # Track what was moved
    moved_items = []
    moved_count = 0
    skipped_count = 0
    
    # Move each item
    for item_path_str, reason in DEAD_CODE_TO_MOVE.items():
        item_path = project_root / item_path_str
        
        # Check if it's in KEEP list
        if any(item_path_str.startswith(keep) or keep.startswith(item_path_str) 
               for keep in KEEP_FILES.keys()):
            print(f"⏭️  Skipping (in KEEP list): {item_path}")
            skipped_count += 1
            continue
        
        if move_file_or_folder(item_path, backup_folder, reason):
            moved_items.append((item_path_str, reason))
            moved_count += 1
        else:
            skipped_count += 1
        print()
    
    # Create README
    if moved_items:
        create_readme(backup_folder, moved_items)
    
    # Summary
    print("="*80)
    print("📊 SUMMARY")
    print("="*80)
    print(f"✅ Moved: {moved_count} items")
    print(f"⏭️  Skipped: {skipped_count} items")
    print(f"📂 Backup location: {backup_folder}")
    print()
    print("⚠️  NEXT STEPS:")
    print("1. Test the application thoroughly")
    print("2. Run Excel upload/generation/execution")
    print("3. Check for any import errors")
    print("4. If everything works, delete the TO_BE_DELETED folder")
    print("="*80)

if __name__ == '__main__':
    main()

