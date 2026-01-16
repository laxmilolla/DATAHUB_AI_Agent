"""
Extract all elements from Data Commons page with their names and XPaths
Outputs a CSV table with Element Name, Type, and XPath
"""
import asyncio
import csv
import sys
from pathlib import Path
from playwright.async_api import async_playwright
from utils.xpath_builder import XPathBuilder

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent))


async def extract_all_elements(page, output_file='elements_table.csv'):
    """
    Extract all interactive elements from the page with their XPaths
    
    Args:
        page: Playwright page object
        output_file: Output CSV file path
    """
    print("\n" + "="*80)
    print("EXTRACTING ALL ELEMENTS FROM PAGE")
    print("="*80)
    print(f"Page URL: {page.url}")
    print("="*80)
    
    xpath_builder = XPathBuilder(page)
    elements_data = []
    
    # Wait for page to be fully loaded
    await page.wait_for_load_state('networkidle')
    await page.wait_for_timeout(2000)  # Extra wait for dynamic content
    
    print("\n🔍 Extracting elements...")
    
    # Extract buttons
    print("  📌 Extracting buttons...")
    buttons = await page.locator('button, [role="button"], input[type="button"], input[type="submit"]').all()
    for btn in buttons:
        try:
            if not await btn.is_visible():
                continue
            
            attrs = await btn.evaluate('''element => ({
                tag: element.tagName.toLowerCase(),
                role: element.getAttribute('role') || (element.tagName.toLowerCase() === 'button' ? 'button' : null),
                id: element.id,
                text: element.textContent.trim().substring(0, 100),
                ariaLabel: element.getAttribute('aria-label'),
                class: element.className,
                type: element.type || null
            })''')
            
            name = attrs.get('ariaLabel') or attrs.get('text') or attrs.get('id') or 'button'
            if not name.strip():
                name = 'button'
            
            xpath_result = await xpath_builder.build_unique_xpath(attrs, name)
            xpath = xpath_result.get('xpath', 'N/A')
            
            elements_data.append({
                'Element Name': name[:100],
                'Type': 'button',
                'XPath': xpath,
                'Tag': attrs.get('tag', ''),
                'ID': attrs.get('id', ''),
                'Text': attrs.get('text', '')[:50]
            })
        except Exception as e:
            continue
    
    print(f"    ✅ Found {len([e for e in elements_data if e['Type'] == 'button'])} buttons")
    
    # Extract links
    print("  🔗 Extracting links...")
    links = await page.locator('a[href]').all()
    link_count = 0
    for link in links:
        try:
            if not await link.is_visible():
                continue
            
            attrs = await link.evaluate('''element => ({
                tag: 'a',
                id: element.id,
                text: element.textContent.trim().substring(0, 100),
                href: element.href,
                ariaLabel: element.getAttribute('aria-label'),
                class: element.className
            })''')
            
            name = attrs.get('ariaLabel') or attrs.get('text') or attrs.get('id') or attrs.get('href', 'link')
            if not name.strip():
                name = 'link'
            
            xpath_result = await xpath_builder.build_unique_xpath(attrs, name)
            xpath = xpath_result.get('xpath', 'N/A')
            
            elements_data.append({
                'Element Name': name[:100],
                'Type': 'link',
                'XPath': xpath,
                'Tag': 'a',
                'ID': attrs.get('id', ''),
                'Text': attrs.get('text', '')[:50]
            })
            link_count += 1
        except Exception as e:
            continue
    
    print(f"    ✅ Found {link_count} links")
    
    # Extract inputs
    print("  📝 Extracting inputs...")
    inputs = await page.locator('input:not([type="checkbox"]):not([type="radio"])').all()
    input_count = 0
    for inp in inputs:
        try:
            if not await inp.is_visible():
                continue
            
            attrs = await inp.evaluate('''element => ({
                tag: 'input',
                type: element.type,
                id: element.id,
                name: element.name,
                placeholder: element.placeholder,
                ariaLabel: element.getAttribute('aria-label'),
                class: element.className
            })''')
            
            name = attrs.get('placeholder') or attrs.get('ariaLabel') or attrs.get('name') or attrs.get('id') or 'input'
            if not name.strip():
                name = f"input ({attrs.get('type', 'text')})"
            
            xpath_result = await xpath_builder.build_unique_xpath(attrs, name)
            xpath = xpath_result.get('xpath', 'N/A')
            
            elements_data.append({
                'Element Name': name[:100],
                'Type': f"input ({attrs.get('type', 'text')})",
                'XPath': xpath,
                'Tag': 'input',
                'ID': attrs.get('id', ''),
                'Text': attrs.get('placeholder', '')[:50]
            })
            input_count += 1
        except Exception as e:
            continue
    
    print(f"    ✅ Found {input_count} inputs")
    
    # Extract selects/dropdowns
    print("  📋 Extracting dropdowns...")
    selects = await page.locator('select, [role="combobox"], [role="listbox"]').all()
    select_count = 0
    for sel in selects:
        try:
            if not await sel.is_visible():
                continue
            
            attrs = await sel.evaluate('''element => ({
                tag: element.tagName.toLowerCase(),
                role: element.getAttribute('role'),
                id: element.id,
                name: element.name,
                ariaLabel: element.getAttribute('aria-label'),
                class: element.className
            })''')
            
            name = attrs.get('ariaLabel') or attrs.get('name') or attrs.get('id') or 'dropdown'
            if not name.strip():
                name = 'dropdown'
            
            xpath_result = await xpath_builder.build_unique_xpath(attrs, name)
            xpath = xpath_result.get('xpath', 'N/A')
            
            elements_data.append({
                'Element Name': name[:100],
                'Type': 'dropdown',
                'XPath': xpath,
                'Tag': attrs.get('tag', ''),
                'ID': attrs.get('id', ''),
                'Text': ''
            })
            select_count += 1
        except Exception as e:
            continue
    
    print(f"    ✅ Found {select_count} dropdowns")
    
    # Extract checkboxes
    print("  ☑️  Extracting checkboxes...")
    checkboxes = await page.locator('input[type="checkbox"]').all()
    checkbox_count = 0
    for cb in checkboxes:
        try:
            if not await cb.is_visible():
                continue
            
            attrs = await cb.evaluate('''element => ({
                tag: 'input',
                type: 'checkbox',
                id: element.id,
                name: element.name,
                ariaLabel: element.getAttribute('aria-label'),
                class: element.className
            })''')
            
            name = attrs.get('ariaLabel') or attrs.get('name') or attrs.get('id') or 'checkbox'
            if not name.strip():
                name = 'checkbox'
            
            xpath_result = await xpath_builder.build_unique_xpath(attrs, name)
            xpath = xpath_result.get('xpath', 'N/A')
            
            elements_data.append({
                'Element Name': name[:100],
                'Type': 'checkbox',
                'XPath': xpath,
                'Tag': 'input',
                'ID': attrs.get('id', ''),
                'Text': ''
            })
            checkbox_count += 1
        except Exception as e:
            continue
    
    print(f"    ✅ Found {checkbox_count} checkboxes")
    
    # Write to CSV
    print(f"\n💾 Writing {len(elements_data)} elements to {output_file}...")
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        if elements_data:
            writer = csv.DictWriter(f, fieldnames=['Element Name', 'Type', 'XPath', 'Tag', 'ID', 'Text'])
            writer.writeheader()
            writer.writerows(elements_data)
    
    print(f"✅ Done! Extracted {len(elements_data)} elements")
    print(f"📄 Saved to: {output_file}")
    
    # Print summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    type_counts = {}
    for elem in elements_data:
        elem_type = elem['Type']
        type_counts[elem_type] = type_counts.get(elem_type, 0) + 1
    
    for elem_type, count in sorted(type_counts.items()):
        print(f"  {elem_type}: {count}")
    print("="*80)
    
    return elements_data


async def main():
    """Main function"""
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = 'https://hub-stage.datacommons.cancer.gov/'
    
    output_file = sys.argv[2] if len(sys.argv) > 2 else 'elements_table.csv'
    
    print(f"\n🌐 Opening browser and navigating to: {url}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        await page.goto(url, wait_until='networkidle', timeout=60000)
        
        # Extract elements
        elements = await extract_all_elements(page, output_file)
        
        # Keep browser open for inspection
        print("\n⏸️  Browser will remain open for 30 seconds for inspection...")
        await page.wait_for_timeout(30000)
        
        await browser.close()
    
    print("\n✅ Extraction complete!")


if __name__ == '__main__':
    asyncio.run(main())

