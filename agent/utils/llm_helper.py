"""
LLM Helper - Helper functions for LLM disambiguation
Extracted from bedrock_playwright_agent.py lines 777-939
"""
import json
import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class LLMHelper:
    """Helper functions for LLM disambiguation"""
    
    def __init__(self, bedrock_client, story: str = ""):
        """
        Initialize LLM helper
        Args:
            bedrock_client: BedrockClient instance
            story: Story text for context
        """
        self.bedrock_client = bedrock_client
        self.story = story
    
    async def describe_element(self, element: Any) -> str:
        """
        Describe an element for LLM to understand its context and purpose
        """
        try:
            tag = await element.evaluate("el => el.tagName")
            role = await element.get_attribute("role") or "none"
            aria_expanded = await element.get_attribute("aria-expanded")
            aria_selected = await element.get_attribute("aria-selected")
            text = (await element.text_content() or "")[:80]
            
            class_name = await element.get_attribute("class") or ""
            data_attrs = await element.evaluate("""el => {
                const attrs = {};
                for (let attr of el.attributes) {
                    if (attr.name.startsWith('data-')) {
                        attrs[attr.name] = attr.value;
                    }
                }
                return JSON.stringify(attrs);
            }""")
            
            # Get location context
            box = await element.bounding_box()
            if box:
                x_pos = int(box['x'])
                y_pos = int(box['y'])
                
                if x_pos < 300:
                    location = "LEFT SIDEBAR (filter panel)"
                elif x_pos > 1100:
                    location = "RIGHT SIDEBAR"
                else:
                    if y_pos < 400:
                        location = "CENTER TOP (tab bar / header area)"
                    else:
                        location = "CENTER MAIN (data table area)"
                
                location_detail = f"{location} at x={x_pos}, y={y_pos}"
            else:
                location_detail = "HIDDEN/OFF-SCREEN"
            
            # Detect element type
            element_type = "unknown"
            if aria_expanded is not None:
                element_type = "FILTER ACCORDION/DROPDOWN (collapsible section)"
            elif role == "tab":
                element_type = "DATA TABLE TAB (switches table view)"
            elif "filter" in class_name.lower() or "filter" in data_attrs.lower():
                element_type = "FILTER CONTROL"
            elif tag == "BUTTON":
                element_type = "BUTTON"
            elif tag == "A":
                element_type = "LINK"
            
            parent_info = await element.evaluate("""el => {
                const parent = el.parentElement;
                if (!parent) return 'no parent';
                const classes = parent.className || '';
                if (classes.includes('sidebar') || classes.includes('filter')) return 'inside sidebar/filter';
                if (classes.includes('tab')) return 'inside tab bar';
                if (classes.includes('table') || classes.includes('grid')) return 'inside data table';
                return classes.slice(0, 50) || 'no class';
            }""")
            
            is_button = tag == "BUTTON"
            is_link = tag == "A"
            has_click_handler = await element.evaluate("el => typeof el.onclick === 'function' || el.hasAttribute('onclick')")
            
            description = f"""
TYPE: {element_type}
TAG: <{tag.lower()}>
ROLE: {role}
TEXT: "{text}"
LOCATION: {location_detail}
EXPANDABLE: {"YES (aria-expanded=" + aria_expanded + ")" if aria_expanded else "no"}
SELECTED: {"YES (active tab)" if aria_selected == "true" else "no"}
CLASSES: {class_name[:60] or "none"}
PARENT: {parent_info}
INTERACTIVE: {"button" if is_button else "link" if is_link else "has onclick" if has_click_handler else "maybe not clickable"}
"""
            return description.strip()
        except Exception as e:
            return f"Error describing element: {e}"
    
    async def choose_element(self, candidates: List[Dict], selector: str) -> int:
        """
        Let LLM decide which element to click based on story context
        Returns: Index of chosen element
        """
        story = self.story or 'No specific story context available'
        
        # Format candidates
        candidates_text = ""
        for i, candidate in enumerate(candidates):
            candidates_text += f"\n--- Element {i} ---\n{candidate['description']}\n"
        
        prompt = f"""I'm trying to click: {selector}

The test story says: "{story}"

I found {len(candidates)} matching elements on the page:
{candidates_text}

Based on the story context, which element should I click?

Consider these rules:
- If story mentions "sidebar" or "side filter" → prefer elements in left sidebar (x < 400)
- If story mentions "expand" → prefer elements with aria-expanded attribute
- If story mentions "filter" or "dropdown" → prefer elements with role="button" in filter panels
- If story mentions "tab" → prefer elements with role="tab"
- Always prefer interactive elements (buttons, links) over static text/displays
- Avoid elements that are just displays or counters

Respond with ONLY the element number (0, 1, 2, etc.) - nothing else.
"""
        
        response = await self.bedrock_client.call_llm_simple(prompt, max_tokens=10)
        
        # Parse response
        try:
            match = re.search(r'\b(\d+)\b', response)
            if match:
                chosen = int(match.group(1))
                if 0 <= chosen < len(candidates):
                    logger.info(f"  🤖 LLM chose element {chosen} based on story context")
                    return chosen
                else:
                    logger.warning(f"  ⚠️ LLM chose {chosen} but valid range is 0-{len(candidates)-1}, using 0")
                    return 0
            else:
                logger.warning(f"  ⚠️ LLM response unclear: '{response}', using element 0")
                return 0
        except Exception as e:
            logger.warning(f"  ⚠️ Could not parse LLM response: {e}, using element 0")
            return 0

