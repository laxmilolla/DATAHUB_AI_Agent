#!/usr/bin/env python3
"""
Convert JSON registry files to Katalon Studio Object Repository format
"""
import json
import sys
from pathlib import Path

def convert_to_katalon_json(registry_file: str, output_file: str = None):
    """
    Convert our JSON registry format to Katalon Object Repository format
    
    Katalon Object Repository format:
    {
        "id": "Object Repository/PageName",
        "objects": [
            {
                "id": "Object Repository/PageName/ElementName",
                "name": "ElementName",
                "selectorMethod": "xpath" | "css" | "id",
                "selectorValue": "...",
                "tag": "button" | "input" | etc.
            }
        ]
    }
    """
    with open(registry_file, 'r') as f:
        registry = json.load(f)
    
    # Extract page name from registry file path
    page_name = registry.get('page', 'Page')
    domain = Path(registry_file).parent.name
    
    # Create Katalon format
    katalon_obj = {
        "id": f"Object Repository/{domain}/{page_name}",
        "objects": []
    }
    
    # Convert each element
    for element_name, element_data in registry.get('elements', {}).items():
        # Determine selector method
        selector = element_data.get('selector', '')
        xpath = element_data.get('xpath', '')
        
        selector_method = 'xpath'
        selector_value = xpath if xpath else selector
        
        # Prefer XPath if available, otherwise use selector
        if selector.startswith('#') or selector.startswith('.'):
            selector_method = 'css'
            selector_value = selector
        elif selector.startswith('//') or xpath:
            selector_method = 'xpath'
            selector_value = xpath if xpath else selector
        elif element_data.get('id'):
            selector_method = 'id'
            selector_value = element_data.get('id')
        
        katalon_element = {
            "id": f"Object Repository/{domain}/{page_name}/{element_name}",
            "name": element_name,
            "selectorMethod": selector_method,
            "selectorValue": selector_value,
            "tag": element_data.get('type', 'unknown'),
            "description": element_data.get('description', ''),
            "source": element_data.get('source', 'unknown')
        }
        
        katalon_obj["objects"].append(katalon_element)
    
    # Save output
    if not output_file:
        output_file = registry_file.replace('.json', '_katalon.json')
    
    with open(output_file, 'w') as f:
        json.dump(katalon_obj, f, indent=2)
    
    print(f"✅ Converted {len(katalon_obj['objects'])} elements")
    print(f"📁 Output: {output_file}")
    return output_file

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python katalon_converter.py <registry_file.json> [output_file.json]")
        sys.exit(1)
    
    convert_to_katalon_json(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
