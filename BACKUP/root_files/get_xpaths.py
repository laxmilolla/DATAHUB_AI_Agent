#!/usr/bin/env python3
import re

with open('test_simple_generated.py', 'r') as f:
    content = f.read()

steps_data = []
lines = content.split('\n')
current_url = None

for i, line in enumerate(lines):
    step_match = re.search(r'# Step (\d+): (.+)', line)
    if step_match:
        step_num = step_match.group(1)
        step_text = step_match.group(2).strip()
        steps_data.append({
            'step': step_num,
            'text': step_text,
            'url': None,
            'xpath': None
        })
    
    if 'page.goto(' in line:
        url_match = re.search(r"page\.goto\('([^']+)'\)", line)
        if url_match:
            current_url = url_match.group(1)
            if steps_data:
                steps_data[-1]['url'] = current_url
    
    if steps_data and "selector = 'xpath=" in line:
        xpath_match = re.search(r"selector = 'xpath=(.+)'", line)
        if xpath_match:
            xpath = xpath_match.group(1).replace("\\'", "'")
            steps_data[-1]['xpath'] = xpath
    
    if steps_data and not steps_data[-1]['url'] and current_url:
        steps_data[-1]['url'] = current_url

print("=" * 80)
print("XPATH AND URL FOR EACH STEP")
print("=" * 80)
print()

for s in steps_data:
    print(f"Step {s['step']}: {s['text'][:65]}")
    print(f"  URL: {s['url'] or 'N/A'}")
    if s['xpath']:
        print(f"  XPath: {s['xpath']}")
    elif 'wait' in s['text'].lower():
        print(f"  XPath: N/A (wait step)")
    elif 'Go to' in s['text']:
        print(f"  XPath: N/A (navigation)")
    else:
        print(f"  XPath: NOT FOUND")
    print()

