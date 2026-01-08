"""
Browser Verify Tool - Handle browser_verify_table tool
Extracted from bedrock_playwright_agent.py lines 2900-3035
"""
import logging
from typing import Dict

logger = logging.getLogger(__name__)


class BrowserVerifyTool:
    """Handle browser_verify_table tool"""
    
    def __init__(self, playwright_manager, discovery_tracker, screenshot_manager):
        """
        Initialize verify tool
        Args:
            playwright_manager: PlaywrightManager instance
            discovery_tracker: DiscoveryTracker instance
            screenshot_manager: ScreenshotManager instance
        """
        self.playwright_manager = playwright_manager
        self.discovery_tracker = discovery_tracker
        self.screenshot_manager = screenshot_manager
    
    async def execute(self, table_selector: str, column_name: str, expected_value: str) -> str:
        """
        Verify table column values
        Args:
            table_selector: CSS selector for table or 'visible_table'
            column_name: Column name to verify
            expected_value: Expected value in all rows
        Returns: Result message
        """
        page = self.playwright_manager.get_page()
        
        try:
            # Find table
            if table_selector == 'visible_table':
                table = page.locator('table').nth(0)
            else:
                table = page.locator(table_selector).nth(0)
            
            # Wait for table to be visible
            await table.wait_for(state='visible', timeout=10000)
            
            # Find column index by header text
            from utils.table_verification import find_column_index
            
            headers = await table.locator('thead th, thead td').all_text_contents()
            column_index = find_column_index(headers, column_name)
            
            if column_index != -1:
                if column_name.lower() == headers[column_index].lower().strip():
                    logger.info(f"  ✅ Found exact column match: '{headers[column_index].strip()}' at index {column_index}")
                else:
                    logger.info(f"  ⚠️ Found partial column match: '{headers[column_index].strip()}' at index {column_index}")
            
            if column_index == -1:
                logger.warning(f"  ⚠️ Column '{column_name}' not found in table headers: {headers}")
                
                # Store verification discovery
                await self.discovery_tracker.track(
                    element_name=f"verify_table_{column_name}",
                    original_query=f"verify column {column_name}",
                    final_selector=table_selector,
                    discovery_method="table_verification",
                    metadata={
                        "verification_type": "table_column",
                        "column_name": column_name,
                        "expected_value": expected_value,
                        "result": "FAIL",
                        "reason": f"Column not found. Available: {headers}"
                    }
                )
                
                return f"❌ VERIFICATION FAILED: Column '{column_name}' not found. Available columns: {', '.join(headers)}"
            
            # Get all rows in that column
            rows = await table.locator('tbody tr').all()
            total_rows = len(rows)
            matching_rows = 0
            mismatches = []
            sample_values = []
            
            for i, row in enumerate(rows[:10]):  # Check first 10 rows
                cells = await row.locator('td').all()
                if column_index < len(cells):
                    cell_text = await cells[column_index].text_content()
                    cell_text = cell_text.strip() if cell_text else ""
                    sample_values.append(cell_text)
                    
                    if expected_value.lower() in cell_text.lower():
                        matching_rows += 1
                    else:
                        mismatches.append(f"Row {i+1}: '{cell_text}'")
            
            # Check remaining rows if any
            if total_rows > 10:
                for i in range(10, total_rows):
                    row = rows[i]
                    cells = await row.locator('td').all()
                    if column_index < len(cells):
                        cell_text = await cells[column_index].text_content()
                        cell_text = cell_text.strip() if cell_text else ""
                        if expected_value.lower() in cell_text.lower():
                            matching_rows += 1
                        else:
                            mismatches.append(f"Row {i+1}: '{cell_text}'")
            
            # Take screenshot
            screenshot_result = await self.screenshot_manager.capture(page, f"verify_{column_name}")
            screenshot_path = screenshot_result.get('filename', '')
            
            if matching_rows == total_rows:
                logger.info(f"  ✅ VERIFICATION PASSED: All {total_rows} rows contain '{expected_value}'")
                
                await self.discovery_tracker.track(
                    element_name=f"verify_table_{column_name}",
                    original_query=f"verify column {column_name} = {expected_value}",
                    final_selector=table_selector if table_selector != 'visible_table' else 'table',
                    discovery_method="table_verification",
                    metadata={
                        "verification_type": "table_column",
                        "column_name": column_name,
                        "expected_value": expected_value,
                        "result": "PASS",
                        "total_rows": total_rows,
                        "matching_rows": matching_rows,
                        "screenshot": screenshot_path
                    }
                )
                
                return f"✅ VERIFICATION PASSED: All {total_rows} rows in '{column_name}' column contain '{expected_value}'"
            else:
                logger.warning(f"  ❌ VERIFICATION FAILED: {matching_rows}/{total_rows} rows match")
                
                await self.discovery_tracker.track(
                    element_name=f"verify_table_{column_name}",
                    original_query=f"verify column {column_name} = {expected_value}",
                    final_selector=table_selector if table_selector != 'visible_table' else 'table',
                    discovery_method="table_verification",
                    metadata={
                        "verification_type": "table_column",
                        "column_name": column_name,
                        "expected_value": expected_value,
                        "result": "FAIL",
                        "total_rows": total_rows,
                        "matching_rows": matching_rows,
                        "mismatches": mismatches,
                        "sample_values": sample_values,
                        "screenshot": screenshot_path
                    }
                )
                
                mismatch_details = "; ".join(mismatches[:5]) if mismatches else "See screenshot"
                return f"❌ VERIFICATION FAILED: {matching_rows}/{total_rows} rows match. Mismatches: {mismatch_details}"
        except Exception as e:
            logger.error(f"  ❌ Table verification error: {e}")
            
            await self.discovery_tracker.track(
                element_name=f"verify_table_{column_name}",
                original_query=f"verify column {column_name} = {expected_value}",
                final_selector=table_selector if table_selector != 'visible_table' else 'table',
                discovery_method="table_verification",
                metadata={
                    "verification_type": "table_column",
                    "column_name": column_name,
                    "expected_value": expected_value,
                    "result": "ERROR",
                    "error": str(e)
                }
            )
            
            return f"❌ VERIFICATION ERROR: {str(e)}"


