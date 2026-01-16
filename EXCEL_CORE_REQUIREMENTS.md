# Excel Workflow - Core Requirements

## 🎯 Main Requirements: XPath and URL

Yes, you're correct! The **two main things** needed in Excel are:

1. **XPath** - To locate elements on the page
2. **URL** - To navigate to pages

---

## 📊 How They're Used

### **XPath** (Required for element actions)
- Used for: `click`, `fill`, `verify` actions
- Can be `N/A` for: `navigate`, `wait` actions
- Purpose: Tells Playwright exactly which element to interact with

**Example**:
```
Action: click
XPath: //button[@id='login']
→ Generates: element = page.locator('xpath=//button[@id=\'login\']')
```

### **URL** (Required for navigation)
- Used for: `navigate` action
- Can be `N/A` for: `click`, `fill`, `verify`, `wait` actions
- Purpose: Tells Playwright which page to go to

**Example**:
```
Action: navigate
URL: https://example.com
→ Generates: page.goto('https://example.com')
```

---

## 📋 Required Columns

The Excel file must have these 4 columns:

| Column | Required? | Used For | Can Be N/A? |
|--------|-----------|----------|-------------|
| **Step** | ✅ Yes | Step numbering | ❌ No |
| **Action** | ✅ Yes | Determines code type | ❌ No |
| **URL** | ✅ Yes | Navigation | ✅ Yes (for non-navigate actions) |
| **XPath** | ✅ Yes | Element location | ✅ Yes (for navigate/wait actions) |

---

## 🔄 Action-Based Usage

### **Action: `navigate`**
- **URL**: ✅ Required (cannot be N/A)
- **XPath**: ❌ Not used (can be N/A)
- **Code**: `page.goto(url)`

### **Action: `click`**
- **URL**: ✅ Can be N/A (uses current page)
- **XPath**: ✅ Required (cannot be N/A)
- **Code**: `page.locator('xpath=...').click()`

### **Action: `fill`**
- **URL**: ✅ Can be N/A (uses current page)
- **XPath**: ✅ Required (cannot be N/A)
- **Code**: `page.locator('xpath=...').fill(text_value)`

### **Action: `verify`**
- **URL**: ✅ Can be N/A (uses current page)
- **XPath**: ✅ Required (cannot be N/A)
- **Code**: `page.locator('xpath=...').wait_for(state='visible')`

### **Action: `wait`**
- **URL**: ✅ Can be N/A
- **XPath**: ✅ Can be N/A
- **Code**: `page.wait_for_timeout(wait_time)`

---

## 💡 Key Insight

**The workflow is simple:**
- **Want to go somewhere?** → Provide URL
- **Want to interact with element?** → Provide XPath

**Everything else is optional:**
- Object Type (just for naming/logging)
- Text Value (only needed for `fill` actions)
- Wait Time (only needed for `wait` actions)
- Functions (only needed for special cases like TOTP)

---

## 📝 Minimal Excel Example

**Minimum required data:**

| Step | Action | URL | XPath |
|------|--------|-----|-------|
| 1 | navigate | https://example.com | N/A |
| 2 | click | N/A | //button[@id='login'] |
| 3 | fill | N/A | //input[@name='email'] |
| 4 | click | N/A | //button[@type='submit'] |

**What gets generated:**

```python
# Step 1: Navigate (URL required)
page.goto('https://example.com')

# Step 2: Click (XPath required)
element = page.locator('xpath=//button[@id=\'login\']')
element.click()

# Step 3: Fill (XPath required)
element = page.locator('xpath=//input[@name=\'email\']')
element.fill('text_value')  # text_value from Text Value column

# Step 4: Click (XPath required)
element = page.locator('xpath=//button[@type=\'submit\']')
element.click()
```

---

## ✅ Summary

**Core Requirements:**
- ✅ **XPath** - For finding elements (click, fill, verify)
- ✅ **URL** - For navigation (navigate action)

**Everything else is optional or action-specific:**
- Step (just numbering)
- Action (determines what to do)
- Text Value (only for fill)
- Wait Time (only for wait)
- Object Type (just for readability)
- Functions (only for special cases)

**The generator is smart:**
- It knows when URL is needed (navigate action)
- It knows when XPath is needed (click/fill/verify actions)
- It allows N/A for columns that aren't used for that action

