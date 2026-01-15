"""
Playwright Tree Parser - Build hierarchy from fully-expanded DOM
Uses recursive JavaScript to extract the entire element tree in ONE call
"""

import sys
import asyncio
from typing import Dict, List, Any
from datetime import datetime
from utils.xpath_builder import XPathBuilder


class PlaywrightTreeParser:
    """Parse fully-expanded page using recursive JavaScript tree building"""
    
    def __init__(self, page):
        self.page = page
        self.elements = {}
        self.parent_child_map = {}
        self.xpath_builder = XPathBuilder(page)
        
    async def parse(self) -> Dict[str, Any]:
        """Parse page using BRANCH-BY-BRANCH approach (one accordion at a time)"""
        
        print("\n" + "=" * 80)
        print("🌳 TREE-BASED PARSER - Branch-by-Branch Traversal")
        print("=" * 80)
        
        # STEP 1: Scroll page to load any lazy content
        print("\n📜 Scrolling page to load lazy content...")
        await self._scroll_to_load_all(accordion_id=None)
        
        # STEP 2: Find all top-level accordions (without expanding)
        print("\n🔍 Finding top-level accordions...")
        top_level_accordions = await self._find_top_level_accordions()
        print(f"✅ Found {len(top_level_accordions)} top-level accordions")
        
        # STEP 3: Process each branch one at a time
        for idx, accordion_info in enumerate(top_level_accordions, 1):
            accordion_text = accordion_info.get('text', 'Unknown')[:50]
            print(f"\n{'='*80}")
            print(f"🌿 BRANCH {idx}/{len(top_level_accordions)}: {accordion_text}")
            print(f"{'='*80}")
            sys.stdout.flush()
            
            # Expand THIS accordion and its nested children
            print(f"⏳ Step 1: Expanding branch...")
            sys.stdout.flush()
            await self._expand_accordion_branch(accordion_info)
            print(f"✅ Step 1 complete")
            sys.stdout.flush()
            
            # Parse THIS branch only
            print(f"⏳ Step 2: Building tree...")
            sys.stdout.flush()
            branch_tree = await self._build_branch_tree(accordion_info)
            print(f"✅ Step 2 complete")
            sys.stdout.flush()
            
            # Process the branch
            print(f"⏳ Step 3: Processing tree...")
            sys.stdout.flush()
            if branch_tree:
                await self._process_tree([branch_tree], parent_name=None, depth=0)
                print(f"✅ Branch complete: {len(self.elements)} total elements so far")
                sys.stdout.flush()
            else:
                print(f"⚠️  No elements found in this branch")
                sys.stdout.flush()
        
        # STEP 4: Extract other elements (tabs, buttons, inputs, tables)
        await self._extract_tabs()
        await self._extract_buttons()
        await self._extract_inputs()
        await self._extract_tables()
        
        # Build result
        element_map = {
            "url": self.page.url,
            "page": self._extract_page_name(self.page.url),
            "parsed_at": datetime.now().isoformat(),
            "version": "5.0_branch",
            "parser_type": "playwright_tree_branch_by_branch",
            "elements": self.elements,
            "parent_child_relationships": self.parent_child_map
        }
        
        print(f"\n{'='*80}")
        print(f"✅ PARSING COMPLETE")
        print(f"✅ Extracted {len(self.elements)} total elements")
        print(f"✅ Tracked {len(self.parent_child_map)} parent-child relationships")
        print(f"{'='*80}")
        
        return element_map
    
    def _extract_page_name(self, url: str) -> str:
        """Extract page name from URL"""
        import re
        match = re.search(r'/(explore|home|dashboard|settings|profile|data)$', url)
        if match:
            return match.group(1)
        return "home"
    
    async def _find_top_level_accordions(self) -> List[Dict]:
        """Find all top-level accordions (without expanding them)"""
        try:
            print("  🔍 Running JavaScript to find top-level accordions...")
            sys.stdout.flush()
            
            accordions = await self.page.evaluate('''() => {
                console.log('[JS] Starting accordion search...');
                const topLevelAccordions = [];
                
                // Find all accordion buttons
                const allAccordions = document.querySelectorAll('button[aria-expanded], [role="button"][aria-expanded]');
                console.log('[JS] Found', allAccordions.length, 'total accordions');
                
                for (let i = 0; i < allAccordions.length; i++) {
                    const accordion = allAccordions[i];
                    // Simplified check: Just look at immediate parent container
                    // Don't traverse entire tree (was causing infinite loop)
                    
                    // Consider top-level if within 3 parent levels of body
                    let parent = accordion.parentElement;
                    let depth = 0;
                    let isTopLevel = true;
                    
                    while (parent && parent !== document.body && depth < 10) {
                        // If we find another accordion in parent chain, it's nested
                        if (parent.hasAttribute && parent.hasAttribute('aria-expanded')) {
                            isTopLevel = false;
                            break;
                        }
                        parent = parent.parentElement;
                        depth++;
                    }
                    
                    if (isTopLevel) {
                        const rect = accordion.getBoundingClientRect();
                        topLevelAccordions.push({
                            id: accordion.id || '',
                            text: accordion.textContent.trim().substring(0, 100),
                            tag: accordion.tagName.toLowerCase(),
                            class: accordion.className,
                            x: rect.x,
                            y: rect.y,
                            expanded: accordion.getAttribute('aria-expanded') === 'true'
                        });
                    }
                }
                
                console.log('[JS] Found', topLevelAccordions.length, 'top-level accordions');
                return topLevelAccordions;
            }''')
            
            print(f"  ✅ JavaScript returned {len(accordions)} accordions")
            sys.stdout.flush()
            
            for acc in accordions:
                status = "✓ expanded" if acc.get('expanded') else "✗ collapsed"
                print(f"  - {acc.get('text', 'Unknown')[:50]} ({status})")
            
            return accordions
            
        except Exception as e:
            print(f"  ⚠️  Error finding top-level accordions: {e}")
            sys.stdout.flush()
            return []
    
    async def _expand_accordion_branch(self, accordion_info: Dict):
        """Expand a specific accordion and all its nested children"""
        accordion_id = accordion_info.get('id')
        accordion_text = accordion_info.get('text', 'Unknown')[:50]
        
        print(f"\n📂 Expanding: {accordion_text} (id={accordion_id})")
        sys.stdout.flush()
        
        try:
            # Step 1: Expand the main accordion if collapsed
            if not accordion_info.get('expanded'):
                print(f"  🔄 Accordion is collapsed, clicking to expand...")
                sys.stdout.flush()
                
                if accordion_id:
                    accordion = self.page.locator(f'button[id="{accordion_id}"]').first
                else:
                    accordion = self.page.locator(f'button:has-text("{accordion_text[:30]}")').first
                
                try:
                    await accordion.click(force=True, timeout=2000)
                    await self.page.wait_for_timeout(500)
                    print(f"  ✅ Main accordion expanded")
                    sys.stdout.flush()
                except Exception as e:
                    print(f"  ⚠️  Failed to expand main accordion: {e}")
                    sys.stdout.flush()
                    return
            else:
                print(f"  ✅ Already expanded")
                sys.stdout.flush()
            
            # Step 2: Find and expand nested accordions (SIMPLIFIED - no rounds, just expand what's visible)
            print(f"  🔍 Looking for nested accordions...")
            sys.stdout.flush()
            
            # Just try once - don't loop multiple rounds
            try:
                if accordion_id:
                    # Find collapsed accordions within this accordion's content
                    nested_selector = f'#{accordion_id} + div button[aria-expanded="false"]'
                    nested_collapsed = await self.page.locator(nested_selector).all()
                else:
                    # Skip nested expansion if no ID
                    nested_collapsed = []
                
                if len(nested_collapsed) > 0:
                    print(f"  📂 Expanding {len(nested_collapsed)} nested accordions (limit 10)...")
                    sys.stdout.flush()
                    
                    for i, nested in enumerate(nested_collapsed[:10]):  # Limit to 10 max
                        try:
                            await nested.click(force=True, timeout=1000)
                        except:
                            pass
                    
                    await self.page.wait_for_timeout(300)
                    print(f"  ✅ Nested expansion complete")
                    sys.stdout.flush()
                else:
                    print(f"  ✅ No nested accordions to expand")
                    sys.stdout.flush()
                    
            except Exception as e:
                print(f"  ⚠️  Error expanding nested: {e}")
                sys.stdout.flush()
            
            print(f"  ✅ Branch expansion complete")
            sys.stdout.flush()
            
            # Step 3: Scroll to load all lazy-loaded content
            print(f"  📜 Scrolling to load all content...")
            sys.stdout.flush()
            await self._scroll_to_load_all(accordion_id)
            
        except Exception as e:
            print(f"  ⚠️  Error expanding branch: {e}")
            sys.stdout.flush()
    
    async def _scroll_to_load_all(self, accordion_id: str = None):
        """Scroll through content to trigger lazy loading of all items"""
        try:
            if accordion_id:
                # Find the content container for this accordion
                content_selector = f'#{accordion_id} + div'
            else:
                # Scroll the main page
                content_selector = 'body'
            
            print(f"    🔍 Finding scrollable containers...")
            sys.stdout.flush()
            
            # Look for scrollable divs within the content area
            scrollable_containers = await self.page.evaluate(f'''(contentSelector) => {{
                const content = document.querySelector(contentSelector);
                if (!content) return [];
                
                const scrollables = [];
                // Find all divs with overflow scroll/auto
                const allDivs = content.querySelectorAll('div');
                
                for (const div of allDivs) {{
                    const style = window.getComputedStyle(div);
                    const hasScroll = (style.overflowY === 'scroll' || style.overflowY === 'auto') &&
                                     div.scrollHeight > div.clientHeight;
                    
                    if (hasScroll) {{
                        // Return info we can use to locate it
                        scrollables.push({{
                            id: div.id || '',
                            className: div.className || '',
                            scrollHeight: div.scrollHeight,
                            clientHeight: div.clientHeight,
                            index: scrollables.length
                        }});
                    }}
                }}
                
                return scrollables;
            }}''', content_selector)
            
            if len(scrollable_containers) == 0:
                print(f"    ✅ No scrollable containers found")
                sys.stdout.flush()
                return
            
            print(f"    📜 Found {len(scrollable_containers)} scrollable containers")
            sys.stdout.flush()
            
            # Scroll each container
            for container_info in scrollable_containers:
                container_id = container_info.get('id')
                scroll_height = container_info.get('scrollHeight', 0)
                client_height = container_info.get('clientHeight', 0)
                
                print(f"    📜 Scrolling container (height: {scroll_height}px)...")
                sys.stdout.flush()
                
                # Scroll to bottom in steps
                if container_id:
                    locator = self.page.locator(f'#{container_id}')
                else:
                    # Use className or index
                    continue
                
                try:
                    # Scroll down in multiple steps to trigger lazy loading
                    for i in range(5):  # 5 scroll steps
                        await locator.evaluate('el => el.scrollTop = el.scrollHeight')
                        await self.page.wait_for_timeout(300)  # Wait for items to load
                    
                    print(f"      ✅ Scrolled to bottom")
                    sys.stdout.flush()
                    
                except Exception as e:
                    print(f"      ⚠️ Failed to scroll: {e}")
                    sys.stdout.flush()
            
            # Final wait for all lazy loading to complete
            await self.page.wait_for_timeout(500)
            print(f"  ✅ Scrolling complete")
            sys.stdout.flush()
                
        except Exception as e:
            print(f"  ⚠️  Error scrolling to load content: {e}")
            sys.stdout.flush()
    
    async def _build_branch_tree(self, accordion_info: Dict) -> Dict:
        """Build tree for a SPECIFIC accordion branch"""
        accordion_id = accordion_info.get('id')
        accordion_text = accordion_info.get('text', '')
        
        print(f"\n🌳 Building tree for this branch (id={accordion_id})...")
        sys.stdout.flush()
        
        tree_node = await self.page.evaluate(r'''(accordionId) => {
            console.log('[JS] Building tree for accordion:', accordionId);
            // Find the specific accordion
            let accordion;
            if (accordionId) {
                accordion = document.getElementById(accordionId);
            }
            
            if (!accordion) {
                return null;
            }
            
            // Build node for this accordion
            const node = {
                id: accordion.id || '',
                text: accordion.textContent.trim().substring(0, 100),
                type: 'accordion',
                tag: accordion.tagName.toLowerCase(),
                role: accordion.getAttribute('role'),
                'aria-expanded': accordion.getAttribute('aria-expanded'),
                class: accordion.className,
                position: accordion.getBoundingClientRect(),
                children: [],
                checkboxes: []
            };
            
            // Find content div
            let contentDiv = accordion.nextElementSibling;
            if (!contentDiv || contentDiv.getAttribute('role') === 'button') {
                if (accordion.id) {
                    contentDiv = document.querySelector(`div[id="${accordion.id}"]:not([role="button"])`);
                }
            }
            
            if (!contentDiv) {
                return node;
            }
            
            // Recursive function to build nested tree
            function buildNested(container, maxDepth = 10, currentDepth = 0) {
                if (currentDepth > maxDepth) return [];
                
                const elements = [];
                
                // Find direct child accordions
                const allAccordions = container.querySelectorAll('button[aria-expanded], [role="button"][aria-expanded]');
                
                for (const childAccordion of allAccordions) {
                    // Check if direct child
                    let parent = childAccordion.parentElement;
                    let isDirect = false;
                    
                    while (parent && parent !== container) {
                        if (parent.getAttribute('role') === 'button') {
                            break;
                        }
                        parent = parent.parentElement;
                    }
                    
                    if (parent === container) {
                        isDirect = true;
                    }
                    
                    if (isDirect) {
                        const childNode = {
                            id: childAccordion.id || '',
                            text: childAccordion.textContent.trim().substring(0, 100),
                            type: 'accordion',
                            tag: childAccordion.tagName.toLowerCase(),
                            role: childAccordion.getAttribute('role'),
                            'aria-expanded': childAccordion.getAttribute('aria-expanded'),
                            class: childAccordion.className,
                            position: childAccordion.getBoundingClientRect(),
                            children: [],
                            checkboxes: []
                        };
                        
                        // Find child's content div
                        let childContentDiv = childAccordion.nextElementSibling;
                        if (!childContentDiv || childContentDiv.getAttribute('role') === 'button') {
                            if (childAccordion.id) {
                                childContentDiv = document.querySelector(`div[id="${childAccordion.id}"]:not([role="button"])`);
                            }
                        }
                        
                        if (childContentDiv) {
                            // Recurse for grandchildren
                            childNode.children = buildNested(childContentDiv, maxDepth, currentDepth + 1);
                            
                            // Find checkboxes in child
                            const childCheckboxes = childContentDiv.querySelectorAll('input[type="checkbox"], [role="checkbox"]');
                            childNode.checkboxes = Array.from(childCheckboxes).map(cb => {
                                let label = '';
                                const labelEl = cb.closest('label');
                                if (labelEl) {
                                    label = labelEl.textContent.trim();
                                } else if (cb.id) {
                                    const forLabel = document.querySelector(`label[for="${cb.id}"]`);
                                    if (forLabel) {
                                        label = forLabel.textContent.trim();
                                    }
                                }
                                if (!label) {
                                    const parentItem = cb.closest('li') || cb.closest('div[class*="item"]');
                                    if (parentItem) {
                                        label = parentItem.textContent.trim();
                                    } else {
                                        label = cb.parentElement.textContent.trim();
                                    }
                                }
                                label = label.replace(/\s+/g, ' ').substring(0, 150);
                                
                                return {
                                    id: cb.id || '',
                                    name: cb.name || '',
                                    value: cb.value || '',
                                    label: label,
                                    tag: 'input',
                                    type: 'checkbox',
                                    class: cb.className
                                };
                            });
                        }
                        
                        elements.push(childNode);
                    }
                }
                
                return elements;
            }
            
            // Build nested tree for this branch
            node.children = buildNested(contentDiv, 10, 0);
            
            // Find checkboxes at the root level of this accordion
            const rootCheckboxes = contentDiv.querySelectorAll('input[type="checkbox"], [role="checkbox"]');
            node.checkboxes = Array.from(rootCheckboxes).map(cb => {
                let label = '';
                const labelEl = cb.closest('label');
                if (labelEl) {
                    label = labelEl.textContent.trim();
                } else if (cb.id) {
                    const forLabel = document.querySelector(`label[for="${cb.id}"]`);
                    if (forLabel) {
                        label = forLabel.textContent.trim();
                    }
                }
                if (!label) {
                    const parentItem = cb.closest('li') || cb.closest('div[class*="item"]');
                    if (parentItem) {
                        label = parentItem.textContent.trim();
                    } else {
                        label = cb.parentElement.textContent.trim();
                    }
                }
                label = label.replace(/\s+/g, ' ').substring(0, 150);
                
                return {
                    id: cb.id || '',
                    name: cb.name || '',
                    value: cb.value || '',
                    label: label,
                    tag: 'input',
                    type: 'checkbox',
                    class: cb.className
                };
            });
            
            return node;
        }''', accordion_id)
        
        if tree_node:
            num_children = len(tree_node.get('children', []))
            num_checkboxes = len(tree_node.get('checkboxes', []))
            print(f"  ✅ Found {num_children} nested accordions, {num_checkboxes} checkboxes")
            sys.stdout.flush()
        else:
            print(f"  ⚠️  Failed to build tree for this branch")
            sys.stdout.flush()
        
        return tree_node
    
    
    
    async def _process_tree(self, tree: List[Dict], parent_name: str = None, parent_id: str = None, depth: int = 0):
        """Recursively process tree and extract elements with parent-child relationships"""
        
        indent = "  " * depth
        
        for node in tree:
            text = node.get('text', '').strip()
            node_id = node.get('id', '')
            
            if not text:
                continue
            
            # Determine location based on position
            pos = node.get('position', {})
            location = "sidebar-filters" if pos.get('x', 999) < 400 else "main-content"
            location_desc = "left sidebar filter panel" if location == "sidebar-filters" else "page"
            
            # Generate name
            if parent_name:
                name = f"{text} accordion nested in {parent_name.split(' accordion')[0]} ({location_desc})"
            else:
                name = f"{text} accordion ({location_desc})"
            
            # Build XPath (pass parent_name for nested elements)
            attrs = {
                'tag': node.get('tag', 'div'),
                'id': node_id,
                'role': node.get('role'),
                'aria-expanded': node.get('aria-expanded'),
                'class': node.get('class', ''),
                'text': text[:50]
            }
            
            print(f"   DEBUG TREE PARSER: Calling build_unique_xpath with parent_name='{parent_name}' for '{name}'")
            xpath_result = await self.xpath_builder.build_unique_xpath(attrs, name, parent_name=parent_name)
            
            # Save element
            self.elements[name] = {
                "type": "accordion",
                "semantic_type": "filter-accordion" if location == "sidebar-filters" else "content-accordion",
                "text": text,
                "xpath": xpath_result.get("xpath"),
                "uniqueness_method": xpath_result.get("uniqueness_method"),
                "location": location_desc,
                "selector": f"[role='button'][id='{node_id}']" if node_id else f"[role='button']:has-text('{text[:30]}')",
                "parent_name": parent_name,
                "parent_text": parent_name.split(' accordion')[0] if parent_name else None,
                "parent_id": parent_id,  # Add parent's DOM ID
                "source": "tree_parse",
                "depth": depth
            }
            
            # Track parent-child relationship
            if parent_name:
                if parent_name not in self.parent_child_map:
                    self.parent_child_map[parent_name] = []
                self.parent_child_map[parent_name].append(name)
                print(f"{indent}✅ {name} [child of: {parent_name.split(' accordion')[0]}]")
            else:
                print(f"{indent}✅ {name}")
            
            # Process checkboxes in this accordion
            checkboxes = node.get('checkboxes', [])
            if checkboxes:
                print(f"{indent}  📋 Processing {len(checkboxes)} checkboxes")
                for cb in checkboxes:
                    await self._process_checkbox(cb, parent_name=name, parent_id=node_id, depth=depth)
            
            # Recursively process children
            children = node.get('children', [])
            if children:
                print(f"{indent}  🔍 {len(children)} child accordions")
                await self._process_tree(children, parent_name=name, parent_id=node_id, depth=depth + 1)
    
    async def _process_checkbox(self, cb_data: Dict, parent_name: str, parent_id: str, depth: int):
        """Process a checkbox element"""
        
        label = cb_data.get('label', '').strip()[:100]
        
        # If label is empty, try to extract from ID
        # Pattern: checkbox_{ACCORDION}_{VALUE}
        if not label:
            cb_id = cb_data.get('id', '')
            if cb_id and cb_id.startswith('checkbox_'):
                # Remove 'checkbox_' prefix
                parts = cb_id.replace('checkbox_', '', 1).split('_', 1)
                if len(parts) == 2:
                    # parts[0] is accordion name, parts[1] is the value/label
                    label = parts[1]
                    print(f"    ℹ️  Extracted label from ID: '{label[:50]}'")
        
        if not label:
            print(f"    ⚠️ Skipping checkbox with empty label: id={cb_data.get('id')}")
            return
        
        name = f"{label} checkbox (filter)"
        
        attrs = {
            'tag': 'input',
            'type': 'checkbox',
            'id': cb_data.get('id', ''),
            'name': cb_data.get('name', ''),
            'value': cb_data.get('value', ''),
            'class': cb_data.get('class', ''),
            'label': label
        }
        
        xpath_result = await self.xpath_builder.build_unique_xpath(attrs, name)
        
        self.elements[name] = {
            "type": "checkbox",
            "semantic_type": "filter-checkbox",
            "text": label,
            "xpath": xpath_result.get("xpath"),
            "uniqueness_method": xpath_result.get("uniqueness_method"),
            "selector": f"input[type='checkbox'][id='{cb_data.get('id')}']" if cb_data.get('id') else "input[type='checkbox']",
            "parent_name": parent_name,
            "parent_text": parent_name.split(' accordion')[0] if parent_name else None,
            "parent_id": parent_id,  # Add parent's DOM ID
            "source": "tree_parse"
        }
        
        # Track relationship
        if parent_name not in self.parent_child_map:
            self.parent_child_map[parent_name] = []
        self.parent_child_map[parent_name].append(name)
    
    async def _extract_tabs(self):
        """Extract tab elements"""
        print("\n📑 Extracting tabs...")
        
        try:
            tabs = await self.page.locator('[role="tab"]').all()
            print(f"  🔍 Found {len(tabs)} tabs")
            
            for tab in tabs:
                try:
                    attrs = await tab.evaluate('''element => ({
                        tag: element.tagName.toLowerCase(),
                        id: element.id,
                        role: element.getAttribute('role'),
                        'aria-selected': element.getAttribute('aria-selected'),
                        class: element.className,
                        text: element.textContent.trim()
                    })''')
                    
                    text = attrs.get('text', '')
                    if not text:
                        continue
                    
                    # Extract tab name without dynamic count (e.g., "Diagnosis(28,944)" -> "Diagnosis")
                    # This makes the XPath work regardless of the count number
                    tab_name = text.split('(')[0].strip() if '(' in text else text
                    
                    box = await tab.bounding_box()
                    location = "main content area" if box and box['y'] > 200 else "top navigation"
                    
                    name = f"{text} tab ({location})"
                    
                    # Build XPath with partial match (contains) to handle dynamic numbers
                    tag = attrs.get('tag', 'button')
                    xpath = f"//{tag}[@role='tab' and contains(normalize-space(.), '{tab_name}')]"
                    
                    self.elements[name] = {
                        "type": "tab",
                        "text": tab_name,  # Store clean name without count
                        "xpath": xpath,
                        "uniqueness_method": "role_plus_text_partial",
                        "location": location,
                        "selector": f"[role='tab']:has-text('{tab_name}')",
                        "source": "tree_parse"
                    }
                    
                    print(f"    ✅ {name}")
                    
                except Exception:
                    continue
                    
        except Exception as e:
            print(f"  ⚠️ Tab extraction failed: {e}")
    
    async def _extract_buttons(self):
        """Extract button elements (excluding accordions and tabs)"""
        print("\n🔘 Extracting buttons...")
        
        try:
            buttons = await self.page.locator('button:not([role="tab"]):not([aria-expanded])').all()
            
            count = 0
            for button in buttons[:15]:
                try:
                    if not await button.is_visible():
                        continue
                    
                    attrs = await button.evaluate('''element => ({
                        tag: 'button',
                        id: element.id,
                        class: element.className,
                        text: element.textContent.trim()
                    })''')
                    
                    text = attrs.get('text', '')[:50]
                    if not text or len(text) < 2:
                        continue
                    
                    name = f"{text} button"
                    xpath_result = await self.xpath_builder.build_unique_xpath(attrs, name)
                    
                    self.elements[name] = {
                        "type": "button",
                        "text": text,
                        "xpath": xpath_result.get("xpath"),
                        "uniqueness_method": xpath_result.get("uniqueness_method"),
                        "selector": f"button:has-text('{text}')",
                        "source": "tree_parse"
                    }
                    
                    count += 1
                    
                except Exception:
                    continue
            
            print(f"  ✅ Extracted {count} buttons")
                    
        except Exception as e:
            print(f"  ⚠️ Button extraction failed: {e}")
    
    async def _extract_inputs(self):
        """Extract input elements (excluding checkboxes)"""
        print("\n📝 Extracting inputs...")
        
        try:
            inputs = await self.page.locator('input:not([type="checkbox"])').all()
            
            count = 0
            for inp in inputs[:10]:
                try:
                    if not await inp.is_visible():
                        continue
                    
                    attrs = await inp.evaluate('''element => ({
                        tag: 'input',
                        type: element.type,
                        id: element.id,
                        name: element.name,
                        placeholder: element.placeholder,
                        class: element.className
                    })''')
                    
                    name = attrs.get('placeholder') or attrs.get('name') or attrs.get('id') or 'input'
                    name = f"{name} input"
                    
                    xpath_result = await self.xpath_builder.build_unique_xpath(attrs, name)
                    
                    self.elements[name] = {
                        "type": "input",
                        "xpath": xpath_result.get("xpath"),
                        "uniqueness_method": xpath_result.get("uniqueness_method"),
                        "selector": f"input[type='{attrs.get('type')}']",
                        "source": "tree_parse"
                    }
                    
                    count += 1
                    
                except Exception:
                    continue
            
            print(f"  ✅ Extracted {count} inputs")
                    
        except Exception as e:
            print(f"  ⚠️ Input extraction failed: {e}")
    
    async def _extract_tables(self):
        """Extract table elements (headers and structure)"""
        print("\n📊 Extracting tables...")
        
        try:
            # Find all visible tables
            tables = await self.page.locator('table').all()
            
            table_count = 0
            for table_idx, table in enumerate(tables):
                try:
                    if not await table.is_visible():
                        continue
                    
                    # Extract table headers
                    headers = await table.evaluate('''table => {
                        const headers = [];
                        const headerCells = table.querySelectorAll('thead th, thead td');
                        headerCells.forEach(th => {
                            headers.push({
                                text: th.textContent.trim(),
                                index: headers.length
                            });
                        });
                        return headers;
                    }''')
                    
                    if not headers or len(headers) == 0:
                        continue
                    
                    table_count += 1
                    table_name = f"data table {table_count}"
                    
                    print(f"  📋 Table {table_count}: {len(headers)} columns")
                    
                    # Save table metadata
                    self.elements[table_name] = {
                        "type": "table",
                        "semantic_type": "data-table",
                        "columns": [h['text'] for h in headers],
                        "column_count": len(headers),
                        "xpath": f"(//table)[{table_idx + 1}]",
                        "uniqueness_method": "positional",
                        "selector": "table",
                        "source": "tree_parse"
                    }
                    
                    # Save each column as a separate element
                    for header in headers:
                        col_text = header['text']
                        if not col_text or len(col_text) < 2:
                            continue
                        
                        col_name = f"{col_text} column (table {table_count})"
                        col_index = header['index']
                        
                        self.elements[col_name] = {
                            "type": "table_column",
                            "semantic_type": "data-column",
                            "text": col_text,
                            "column_index": col_index,
                            "table": table_name,
                            "xpath": f"(//table)[{table_idx + 1}]//thead//th[{col_index + 1}]",
                            "uniqueness_method": "positional",
                            "selector": f"table thead th:nth-child({col_index + 1})",
                            "source": "tree_parse"
                        }
                        
                        print(f"    - Column {col_index}: {col_text}")
                    
                except Exception as e:
                    print(f"    ⚠️ Failed to extract table {table_idx + 1}: {e}")
                    continue
            
            print(f"  ✅ Extracted {table_count} tables")
                    
        except Exception as e:
            print(f"  ⚠️ Table extraction failed: {e}")


async def parse_with_tree(page) -> Dict[str, Any]:
    """Main entry point for tree-based parsing"""
    parser = PlaywrightTreeParser(page)
    return await parser.parse()

