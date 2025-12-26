# 📸 Pre-Click Screenshot Fixes

**Date:** December 26, 2024  
**Issue:** GLIOMA01 not visible in pre-click screenshots

---

## 🚨 Problems Found

### **1. Elements Not Visible (Off-Screen)**
**Problem:** GLIOMA01 and other elements were off-screen when screenshot taken
- Playwright `is_visible()` returns `true` even if element is scrolled out of view
- Screenshot captured top of page, not where element actually was
- GLIOMA01 was below the fold, not in viewport

**Result:** Empty/wrong screenshots with no red highlight visible

---

### **2. Filename Issues (Special Characters)**
**Problem:** Special characters in filenames created directories instead of files
```bash
005_pre_click_[href="#/explore"].png  ← Created directory, not file!
```

**Caused by:** Characters like `[`, `]`, `#`, `/`, `"` in selector names

**Result:** Screenshots 2, 4, 5 returned 404 errors in UI

---

### **3. Red Highlight Not Visible**
**Problem:** Red outline removed too quickly or not rendered
- Only 300ms wait time before screenshot
- Browser may not have rendered outline yet
- Highlight removed immediately after screenshot

**Result:** Screenshots without red highlighting

---

## ✅ Fixes Implemented

### **Fix 1: Scroll Element Into View**

**Before:**
```python
if validation_result["visible"]:
    await locator.evaluate("el => el.style.outline = '3px solid red'")
    await self.page.wait_for_timeout(300)
    await self.page.screenshot(path=str(filepath))
```

**After:**
```python
if validation_result["visible"]:
    # CRITICAL: Scroll element into view first!
    await locator.scroll_into_view_if_needed()
    await self.page.wait_for_timeout(500)  # Let scroll complete
    
    # Add thick red outline
    await locator.evaluate("el => el.style.outline = '5px solid red'")
    await locator.evaluate("el => el.style.outlineOffset = '2px'")
    await self.page.wait_for_timeout(1000)  # Wait for render
    
    # Take screenshot (element now in view with highlight)
    await self.page.screenshot(path=str(filepath), full_page=False)
    
    # Keep visible briefly
    await self.page.wait_for_timeout(200)
    await locator.evaluate("el => el.style.outline = ''")
```

**Changes:**
- ✅ `scroll_into_view_if_needed()` brings element to viewport
- ✅ Increased wait from 300ms → 1000ms for rendering
- ✅ Thicker outline (5px instead of 3px)
- ✅ Added outline offset for better visibility
- ✅ Keep highlight visible 200ms after screenshot

---

### **Fix 2: Sanitize Filenames**

**New method:**
```python
def _sanitize_filename(self, name: str) -> str:
    """Remove special characters from filename"""
    name = name.replace('[', '').replace(']', '')
    name = name.replace('"', '').replace("'", '')
    name = name.replace('#', '').replace('/', '_')
    name = name.replace('=', '_').replace(':', '_')
    name = name.replace('.', '_').replace(' ', '_')
    # Remove multiple underscores
    while '__' in name:
        name = name.replace('__', '_')
    return name
```

**Before:**
```
005_pre_click_[href="#/explore"].png  ← Breaks!
```

**After:**
```
005_pre_click_href_explore.png  ← Works!
```

---

### **Fix 3: Better Logging**

**Added:**
```python
logger.info(f"  📍 Scrolling element into view...")
logger.info(f"  ✅ Element visible and highlighted: {filename} ({size} bytes)")
```

**Shows:**
- When scrolling happens
- Exact filename and size
- Clear indication of success

---

## 📊 Expected Results

### **Before Fixes:**

**Screenshot 9 (pre_click_GLIOMA01.png):**
- ❌ Shows top of page
- ❌ GLIOMA01 not visible
- ❌ No red highlight
- ❌ Can't verify what element will be clicked

---

### **After Fixes:**

**Screenshot 9 (pre_click_GLIOMA01.png):**
- ✅ GLIOMA01 centered in viewport
- ✅ Thick red outline (5px) around GLIOMA01
- ✅ Clear visual proof of target element
- ✅ Can verify correct element before click

---

## 🎯 Test After Deployment

Run the same GLIOMA01 test and verify:

1. **All pre-click screenshots load (no 404 errors)**
   - Check: Screenshots 2, 4, 5 are accessible
   
2. **GLIOMA01 visible in screenshot 9**
   - Check: GLIOMA01 text is in the image
   - Check: Red outline around GLIOMA01
   
3. **Other elements also highlighted**
   - Check: Continue button (if exists)
   - Check: EXPLORE button
   - Check: Study dropdown
   
4. **Filenames sanitized**
   ```bash
   ls storage/screenshots/
   # Should see no directories, only .png files
   ```

---

## 🔧 Technical Details

### **Why `scroll_into_view_if_needed()`?**

Playwright's built-in method:
- Scrolls element into view only if needed
- Handles both vertical and horizontal scrolling
- Works with scroll containers and iframes
- Waits for scroll animations

### **Why 1000ms wait?**

Browser rendering pipeline:
1. Apply CSS (outline style)
2. Layout recalculation
3. Paint
4. Composite layers

1000ms ensures all steps complete before screenshot.

### **Why `full_page=False`?**

- Only captures viewport (visible area)
- Faster than full page screenshot
- Element is already scrolled into view
- Shows exactly what user would see

---

## 📁 Files Modified

1. **`agent/bedrock_playwright_agent.py`**
   - Added `_sanitize_filename()` method
   - Updated `_validate_element_visibility()` with scroll + better highlighting
   - Increased wait times
   - Better logging

---

## 🚀 Deployment

```bash
scp agent/bedrock_playwright_agent.py ubuntu@EC2:~/DATAHUB_AI_Agent/agent/
ssh ubuntu@EC2 "pkill -f 'python3 api/app.py' && cd ~/DATAHUB_AI_Agent && nohup python3 api/app.py > logs/app.log 2>&1 &"
```

---

*Implementation completed: December 26, 2024*

