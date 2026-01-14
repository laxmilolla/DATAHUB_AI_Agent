# Dropdown Handling Improvements - Brainstorm

## Current Flow

**Step 1: Click Dropdown Button (e.g., "Study")**
1. Click the dropdown button
2. Wait 1 second
3. Check if menu portal appeared
4. Store menu portal selector in `context.open_dropdown_menu`

**Step 2: Click Option (e.g., "NewTestSpn_laxmi")**
1. Detect `open_dropdown_menu` exists
2. Search for option within that menu portal
3. Click the option
4. Clear `open_dropdown_menu`

## Problems Identified

### Problem 1: Menu Portal Detection Timing
- **Issue**: Detection happens AFTER click + 1 second wait
- **Impact**: Menu might appear/disappear before detection
- **Solution**: Check BEFORE click if element is dropdown, then wait immediately after

### Problem 2: Material-UI Select Structure
- **Issue**: Material-UI Select uses portals that might be outside main DOM
- **Impact**: Selectors might not find the menu
- **Solution**: Better selectors + check document body, not just page

### Problem 3: Menu Closes Too Quickly
- **Issue**: Menu might close before option is selected
- **Impact**: Option click fails
- **Solution**: Keep menu open, prevent auto-close

### Problem 4: Detection Logic Too Complex
- **Issue**: Multiple checks (known names, attributes, metadata) - might miss edge cases
- **Impact**: Dropdown not detected
- **Solution**: Simplify + add more detection methods

## Proposed Improvements

### Improvement 1: Pre-Click Dropdown Detection
**Before clicking, check if element is a dropdown:**

```python
async def _is_dropdown_button(self, locator: Locator) -> bool:
    """Check if element is a dropdown button BEFORE clicking"""
    try:
        # Check attributes
        role = await locator.get_attribute('role')
        aria_expanded = await locator.get_attribute('aria-expanded')
        aria_has_popup = await locator.get_attribute('aria-haspopup')
        class_name = await locator.get_attribute('class') or ''
        
        # Material-UI Select indicators
        is_mui_select = (
            'MuiSelect' in class_name or
            'MuiSelect-select' in class_name or
            role == 'button' and aria_has_popup == 'listbox'
        )
        
        # Standard dropdown indicators
        is_standard_dropdown = (
            role == 'button' and aria_expanded is not None or
            aria_has_popup == 'listbox' or
            aria_has_popup == 'menu'
        )
        
        # Check if element name suggests dropdown
        element_text = await locator.text_content() or ''
        known_dropdowns = ['study', 'datacommons', 'dropdown', 'select']
        is_known_dropdown = any(name in element_text.lower() for name in known_dropdowns)
        
        return is_mui_select or is_standard_dropdown or is_known_dropdown
    except:
        return False
```

### Improvement 2: Enhanced Menu Portal Detection
**Check multiple locations and use better selectors:**

```python
async def _wait_for_dropdown_menu_portal(self, timeout: int = 3000) -> Optional[str]:
    """Enhanced menu portal detection"""
    menu_selectors = [
        # Material-UI Select specific
        '.MuiPopover-root [role="listbox"]',
        '[class*="MuiSelect-menu"]',
        '[class*="MuiMenu-root"]',
        '[class*="MuiPaper-root"][role="listbox"]',
        
        # Standard selectors
        '[role="listbox"]',
        '[role="menu"]',
        
        # Check in document body (portals)
        'body > [role="listbox"]',
        'body > [role="menu"]',
        'body > .MuiPopover-root',
    ]
    
    # Try all selectors in parallel (faster)
    for selector in menu_selectors:
        try:
            # Check both page and document body
            page_locator = self.page.locator(selector).first
            body_locator = self.page.locator(f'body {selector}').first
            
            # Wait for either to appear
            for locator in [page_locator, body_locator]:
                count = await locator.count()
                if count > 0:
                    await locator.wait_for(state='visible', timeout=500)
                    if await locator.is_visible():
                        logger.info(f"  ✅ Menu portal found: {selector}")
                        return selector
        except:
            continue
    
    return None
```

### Improvement 3: Keep Menu Open
**Prevent menu from closing before option is selected:**

```python
async def _keep_menu_open(self, menu_selector: str):
    """Prevent menu from auto-closing"""
    try:
        # Disable click-outside-to-close behavior
        await self.page.evaluate(f"""
            () => {{
                const menu = document.querySelector('{menu_selector}');
                if (menu) {{
                    // Prevent backdrop clicks from closing
                    const backdrop = menu.closest('.MuiBackdrop-root');
                    if (backdrop) {{
                        backdrop.style.pointerEvents = 'none';
                    }}
                    // Prevent escape key from closing
                    menu.setAttribute('data-keep-open', 'true');
                }}
            }}
        """)
    except:
        pass
```

### Improvement 4: Better Option Finding
**More robust option search with fuzzy matching:**

```python
async def _find_option_in_menu(self, menu_selector: str, option_text: str) -> Optional[Locator]:
    """Enhanced option finding with fuzzy matching"""
    try:
        menu_locator = self.page.locator(menu_selector).first
        await menu_locator.wait_for(state='visible', timeout=3000)
        
        # Get all options
        all_options = await menu_locator.locator('[role="option"], li, div[role="option"]').all()
        
        # Try exact match first
        for option in all_options:
            text = await option.text_content() or ''
            if option_text.strip().lower() == text.strip().lower():
                if await option.is_visible():
                    return option
        
        # Try partial match
        for option in all_options:
            text = await option.text_content() or ''
            if option_text.strip().lower() in text.strip().lower():
                if await option.is_visible():
                    return option
        
        # Try fuzzy match (handle underscores, spaces)
        normalized_search = option_text.replace('_', ' ').replace('-', ' ').lower()
        for option in all_options:
            text = await option.text_content() or ''
            normalized_text = text.replace('_', ' ').replace('-', ' ').lower()
            if normalized_search in normalized_text:
                if await option.is_visible():
                    return option
        
        return None
    except:
        return None
```

### Improvement 5: Two-Step Dropdown Flow
**Explicit dropdown open + option select:**

```python
async def execute(self, selector: str, element_description: str = None) -> str:
    """Enhanced execute with better dropdown handling"""
    
    # STEP 1: Check if this is a dropdown button BEFORE clicking
    chosen_locator = await self._find_element(selector)
    
    if chosen_locator:
        is_dropdown = await self._is_dropdown_button(chosen_locator)
        
        if is_dropdown:
            # Click dropdown button
            await chosen_locator.click()
            
            # Immediately wait for menu (no delay)
            menu_portal = await self._wait_for_dropdown_menu_portal(timeout=2000)
            
            if menu_portal:
                self.context.open_dropdown_menu = menu_portal
                await self._keep_menu_open(menu_portal)
                return f"✅ Dropdown opened: {menu_portal}"
            else:
                # Try alternative detection
                menu_portal = await self._wait_for_dropdown_menu_portal_alternative()
                if menu_portal:
                    self.context.open_dropdown_menu = menu_portal
                    return f"✅ Dropdown opened (alternative): {menu_portal}"
    
    # STEP 2: If menu is open, search for option
    if self.context.open_dropdown_menu:
        option_locator = await self._find_option_in_menu(
            self.context.open_dropdown_menu,
            element_description or selector
        )
        
        if option_locator:
            await option_locator.click()
            self.context.open_dropdown_menu = None
            return f"✅ Option selected: {element_description or selector}"
    
    # Normal click flow...
```

## Implementation Priority

1. **HIGH**: Pre-click dropdown detection (Improvement 1)
2. **HIGH**: Enhanced menu portal detection (Improvement 2)
3. **MEDIUM**: Better option finding (Improvement 4)
4. **MEDIUM**: Keep menu open (Improvement 3)
5. **LOW**: Two-step flow refactor (Improvement 5)

## Testing Strategy

1. **Test Study Dropdown**:
   - Click "Study" → Should detect menu portal
   - Click "NewTestSpn_laxmi" → Should find and click option

2. **Test Datacommons Dropdown**:
   - Click "Datacommons" → Should detect menu portal
   - Click "GC" → Should find and click option

3. **Test Edge Cases**:
   - Menu appears slowly
   - Menu in portal outside main DOM
   - Option text with underscores/spaces
   - Multiple menus open

## Questions to Consider

1. Should we add a dedicated `browser_select_dropdown` tool?
2. Should we use Playwright's native select handling?
3. Should we take screenshot after menu opens to verify?
4. Should we add retry logic if menu detection fails?

