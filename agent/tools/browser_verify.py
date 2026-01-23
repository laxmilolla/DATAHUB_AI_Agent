"""
Browser Verify Tool - Handle browser_verify_table and browser_verify_element tools
Extracted from bedrock_playwright_agent.py lines 2900-3035

Now supports element verification using element_locator.check_registry() with unique_attributes
for improved matching and disambiguation.
"""
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class BrowserVerifyTool:
    """Handle browser_verify_table and browser_verify_element tools
    
    - Table verification: Uses direct Playwright selectors
    - Element verification: Uses element_locator.check_registry() with unique_attributes
    """
    
    def __init__(self, playwright_manager, discovery_tracker, screenshot_manager, element_locator=None):
        """
        Initialize verify tool
        Args:
            playwright_manager: PlaywrightManager instance
            discovery_tracker: DiscoveryTracker instance
            screenshot_manager: ScreenshotManager instance
            element_locator: ElementLocator instance (optional, for element verification)
        """
        self.playwright_manager = playwright_manager
        self.discovery_tracker = discovery_tracker
        self.screenshot_manager = screenshot_manager
        self.element_locator = element_locator
    
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
            row_details = []  # Store all row details for display
            
            # Check all rows
            for i, row in enumerate(rows):
                cells = await row.locator('td').all()
                if column_index < len(cells):
                    cell_text = await cells[column_index].text_content()
                    cell_text = cell_text.strip() if cell_text else ""
                    sample_values.append(cell_text)
                    
                    # Check if row matches
                    matches = expected_value.lower() in cell_text.lower()
                    if matches:
                        matching_rows += 1
                    else:
                        mismatches.append(f"Row {i+1}: '{cell_text}'")
                    
                    # Store row detail for display
                    row_details.append({
                        "row_number": i + 1,
                        "value": cell_text,
                        "matches": matches
                    })
            
            # Take screenshot
            screenshot_result = await self.screenshot_manager.capture(page, f"verify_{column_name}")
            screenshot_path = screenshot_result.get('filename', '')
            
            if matching_rows == total_rows:
                logger.info(f"  ✅ VERIFICATION PASSED: All {total_rows} rows contain '{expected_value}'")
                
                # Build detailed row-by-row message
                row_details_text = "\n\nRow-by-Row Verification:\n"
                row_details_text += "┌──────┬──────────────────────────────┬────────┬──────────────────────────────┐\n"
                row_details_text += "│ Row  │ Value                        │ Status │ Expected                     │\n"
                row_details_text += "├──────┼──────────────────────────────┼────────┼──────────────────────────────┤\n"
                for detail in row_details:
                    value_display = detail["value"][:28] if len(detail["value"]) <= 28 else detail["value"][:25] + "..."
                    status = "✅" if detail["matches"] else "❌"
                    expected_display = expected_value[:28] if len(expected_value) <= 28 else expected_value[:25] + "..."
                    row_details_text += f"│ {detail['row_number']:4d} │ {value_display:28s} │ {status:6s} │ {expected_display:28s} │\n"
                row_details_text += "└──────┴──────────────────────────────┴────────┴──────────────────────────────┘"
                
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
                        "row_details": row_details,
                        "screenshot": screenshot_path
                    }
                )
                
                return f"✅ VERIFICATION PASSED: All {total_rows} rows in '{column_name}' column contain '{expected_value}'{row_details_text}"
            else:
                logger.warning(f"  ❌ VERIFICATION FAILED: {matching_rows}/{total_rows} rows match")
                
                # Build detailed row-by-row message
                row_details_text = "\n\nRow-by-Row Verification:\n"
                row_details_text += "┌──────┬──────────────────────────────┬────────┬──────────────────────────────┐\n"
                row_details_text += "│ Row  │ Value                        │ Status │ Expected                     │\n"
                row_details_text += "├──────┼──────────────────────────────┼────────┼──────────────────────────────┤\n"
                for detail in row_details:
                    value_display = detail["value"][:28] if len(detail["value"]) <= 28 else detail["value"][:25] + "..."
                    status = "✅" if detail["matches"] else "❌"
                    expected_display = expected_value[:28] if len(expected_value) <= 28 else expected_value[:25] + "..."
                    row_details_text += f"│ {detail['row_number']:4d} │ {value_display:28s} │ {status:6s} │ {expected_display:28s} │\n"
                row_details_text += "└──────┴──────────────────────────────┴────────┴──────────────────────────────┘"
                
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
                        "row_details": row_details,
                        "screenshot": screenshot_path
                    }
                )
                
                mismatch_details = "; ".join(mismatches[:5]) if mismatches else "See screenshot"
                return f"❌ VERIFICATION FAILED: {matching_rows}/{total_rows} rows match. Mismatches: {mismatch_details}{row_details_text}"
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
    
    async def verify_element(self, element_description: str, verification_type: str = "present", expected_value: Optional[str] = None) -> str:
        """
        Verify individual element using registry lookups with unique_attributes
        
        Args:
            element_description: Element name/description (e.g., "Login", "username", "name")
            verification_type: Type of verification - "present", "text", "attribute", "visible"
            expected_value: Expected value (for text/attribute verification)
        
        Returns: Result message
        """
        if not self.element_locator:
            return "❌ VERIFICATION ERROR: Element locator not available. Cannot verify elements."
        
        page = self.playwright_manager.get_page()
        
        try:
            # Get domain and page for registry lookup
            domain, page_name = await self.playwright_manager.get_domain_and_page()
            logger.info(f"  🔍 Element verification: element='{element_description}', type={verification_type}, domain={domain}, page={page_name}")
            
            if not domain or not page_name:
                logger.warning(f"  ⚠️ Cannot determine domain/page for registry lookup")
                return f"❌ VERIFICATION ERROR: Cannot determine domain/page from current URL: {page.url}"
            
            # Use element_locator.check_registry() which now supports unique_attributes
            registry_selector = self.element_locator.check_registry(element_description, domain, page_name)
            
            if not registry_selector:
                # Try variations
                registry_selector = self.element_locator.check_registry(element_description.capitalize(), domain, page_name)
                if not registry_selector:
                    registry_selector = self.element_locator.check_registry(element_description.lower(), domain, page_name)
            
            if not registry_selector:
                logger.warning(f"  ⚠️ Element '{element_description}' not found in registry")
                
                await self.discovery_tracker.track(
                    element_name=f"verify_{element_description}",
                    original_query=f"verify {element_description} {verification_type}",
                    final_selector=None,
                    discovery_method="element_verification",
                    metadata={
                        "verification_type": verification_type,
                        "element_description": element_description,
                        "expected_value": expected_value,
                        "result": "FAIL",
                        "reason": "Element not found in registry"
                    }
                )
                
                return f"❌ VERIFICATION FAILED: Element '{element_description}' not found in registry"
            
            logger.info(f"  ✅ Found element in registry: {registry_selector}")
            
            # Find element using registry selector
            try:
                if registry_selector.startswith("xpath="):
                    locator = page.locator(f"xpath={registry_selector[6:]}")
                else:
                    locator = page.locator(registry_selector)
                
                # Wait for element to be available
                await locator.wait_for(state='attached', timeout=5000)
                element_count = await locator.count()
                
                if element_count == 0:
                    logger.warning(f"  ⚠️ Element found in registry but not present on page")
                    
                    # Extract element attributes for XPath generation
                    element_attrs = {}
                    try:
                        element_attrs = await self.discovery_tracker.xpath_generator.extract_element_attributes(locator.first)
                    except Exception as e:
                        logger.debug(f"  ⚠️ Could not extract element attributes: {e}")
                    
                    await self.discovery_tracker.track(
                        element_name=f"verify_{element_description}",
                        original_query=f"verify {element_description} {verification_type}",
                        final_selector=registry_selector,
                        discovery_method="element_verification",
                        metadata={
                            "element_attrs": element_attrs,
                            "verification_type": verification_type,
                            "element_description": element_description,
                            "expected_value": expected_value,
                            "result": "FAIL",
                            "reason": "Element not present on page"
                        }
                    )
                    
                    return f"❌ VERIFICATION FAILED: Element '{element_description}' not present on page"
                
                # Perform verification based on type
                result = None
                actual_value = None
                
                if verification_type == "present":
                    result = True
                    logger.info(f"  ✅ VERIFICATION PASSED: Element '{element_description}' is present")
                
                elif verification_type == "visible":
                    is_visible = await locator.first.is_visible()
                    result = is_visible
                    actual_value = "visible" if is_visible else "hidden"
                    logger.info(f"  {'✅' if is_visible else '❌'} Element '{element_description}' visibility: {actual_value}")
                
                elif verification_type == "text":
                    element_text = await locator.first.text_content()
                    actual_value = element_text.strip() if element_text else ""
                    if expected_value:
                        result = expected_value.lower() in actual_value.lower()
                        logger.info(f"  {'✅' if result else '❌'} Element '{element_description}' text: '{actual_value}' (expected: '{expected_value}')")
                    else:
                        result = bool(actual_value)
                        logger.info(f"  {'✅' if result else '❌'} Element '{element_description}' has text: '{actual_value}'")
                
                elif verification_type == "attribute":
                    if not expected_value:
                        return "❌ VERIFICATION ERROR: Expected attribute name required for attribute verification"
                    # Parse attribute name and expected value
                    parts = expected_value.split("=", 1)
                    if len(parts) == 2:
                        attr_name, attr_expected = parts[0].strip(), parts[1].strip()
                        actual_value = await locator.first.get_attribute(attr_name)
                        result = attr_expected.lower() in (actual_value or "").lower()
                        logger.info(f"  {'✅' if result else '❌'} Element '{element_description}' attribute '{attr_name}': '{actual_value}' (expected: '{attr_expected}')")
                    else:
                        # Just check if attribute exists
                        attr_name = expected_value.strip()
                        actual_value = await locator.first.get_attribute(attr_name)
                        result = actual_value is not None
                        logger.info(f"  {'✅' if result else '❌'} Element '{element_description}' has attribute '{attr_name}': {actual_value is not None}")
                
                else:
                    return f"❌ VERIFICATION ERROR: Unknown verification type: {verification_type}"
                
                # Take screenshot
                screenshot_result = await self.screenshot_manager.capture(page, f"verify_{element_description}")
                screenshot_path = screenshot_result.get('filename', '')
                
                # Extract element attributes for XPath generation
                element_attrs = {}
                try:
                    element_attrs = await self.discovery_tracker.xpath_generator.extract_element_attributes(locator.first)
                except Exception as e:
                    logger.debug(f"  ⚠️ Could not extract element attributes: {e}")
                
                # Track discovery
                await self.discovery_tracker.track(
                    element_name=f"verify_{element_description}",
                    original_query=f"verify {element_description} {verification_type}",
                    final_selector=registry_selector,
                    discovery_method="element_verification",
                    metadata={
                        "element_attrs": element_attrs,
                        "verification_type": verification_type,
                        "element_description": element_description,
                        "expected_value": expected_value,
                        "actual_value": actual_value,
                        "result": "PASS" if result else "FAIL",
                        "screenshot": screenshot_path
                    }
                )
                
                if result:
                    if verification_type == "present":
                        return f"✅ VERIFICATION PASSED: Element '{element_description}' is present"
                    elif verification_type == "visible":
                        return f"✅ VERIFICATION PASSED: Element '{element_description}' is visible"
                    elif verification_type == "text":
                        return f"✅ VERIFICATION PASSED: Element '{element_description}' text matches: '{actual_value}'"
                    elif verification_type == "attribute":
                        return f"✅ VERIFICATION PASSED: Element '{element_description}' attribute matches: '{actual_value}'"
                else:
                    if verification_type == "visible":
                        return f"❌ VERIFICATION FAILED: Element '{element_description}' is not visible"
                    elif verification_type == "text":
                        return f"❌ VERIFICATION FAILED: Element '{element_description}' text '{actual_value}' does not match expected '{expected_value}'"
                    elif verification_type == "attribute":
                        return f"❌ VERIFICATION FAILED: Element '{element_description}' attribute does not match expected value"
                
            except Exception as e:
                logger.error(f"  ❌ Element verification error: {e}")
                
                # Extract element attributes for XPath generation (if locator is available)
                element_attrs = {}
                try:
                    # Try to get locator from registry selector if available
                    if registry_selector:
                        if registry_selector.startswith("xpath="):
                            temp_locator = page.locator(f"xpath={registry_selector[6:]}")
                        else:
                            temp_locator = page.locator(registry_selector)
                        element_attrs = await self.discovery_tracker.xpath_generator.extract_element_attributes(temp_locator.first)
                except Exception as e2:
                    logger.debug(f"  ⚠️ Could not extract element attributes: {e2}")
                
                await self.discovery_tracker.track(
                    element_name=f"verify_{element_description}",
                    original_query=f"verify {element_description} {verification_type}",
                    final_selector=registry_selector,
                    discovery_method="element_verification",
                    metadata={
                        "element_attrs": element_attrs,
                        "verification_type": verification_type,
                        "element_description": element_description,
                        "expected_value": expected_value,
                        "result": "ERROR",
                        "error": str(e)
                    }
                )
                
                return f"❌ VERIFICATION ERROR: {str(e)}"
                
        except Exception as e:
            logger.error(f"  ❌ Element verification error: {e}")
            return f"❌ VERIFICATION ERROR: {str(e)}"




