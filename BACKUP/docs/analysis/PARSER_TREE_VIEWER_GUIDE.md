# 🌳 Parser Tree Viewer & Editor - User Guide

**Your secret weapon for visualizing and fixing element registry issues!**

---

## 🎯 What It Does

The Parser Tree Viewer lets you:
- ✅ **See element hierarchy** visually as a tree
- ✅ **Edit parent relationships** via dropdown (no drag-drop needed)
- ✅ **Fix parsing mistakes** instantly
- ✅ **Spot duplicates** and misaligned depths
- ✅ **Save changes** directly to registry
- ✅ **Auto-backup** before every save

---

## 🚀 How to Use It

### **Step 1: Parse a Page**
1. Go to the **Parser** page
2. Upload HTML or enter URL
3. Parse the page
4. Wait for "✅ Registry Updated Successfully!"

### **Step 2: Open Tree Viewer**
Click the **"🌳 View & Edit Element Tree"** button

### **Step 3: View Hierarchy**
You'll see a tree like this:
```
📦 Demographics (depth=0)
  ├─ ☑️ Sex At Birth (depth=1)
  └─ ☑️ Race (depth=1)

📦 Diagnosis (depth=0)
  ├─ 📦 Age at Diagnosis (days) (depth=1)
  ├─ 📦 Diagnosis (depth=1) ⚠️
  ├─ 📦 Diagnosis Basis (depth=1)
  └─ 📦 Disease Phase (depth=1)
```

### **Step 4: Edit an Element**
1. **Click on any element** in the tree
2. **Properties panel** opens on the right
3. **Change Parent** dropdown shows all possible parents
4. **Select new parent** from dropdown
5. **Click "Apply Changes"**

### **Step 5: Save**
Click **"💾 Save Changes"** at the top to persist all edits

---

## 🎨 Visual Guide

```
┌──────────────────────────────────────────────────────────────┐
│ 🌳 Element Tree Viewer & Editor                              │
│ clinicalcommons.ccdi.cancer.gov / explore                    │
├──────────────────────────────────────────────────────────────┤
│ [💾 Save] [🔄 Reload] [⬇️ Expand All] [⬆️ Collapse All]     │
├────────────────────────────┬─────────────────────────────────┤
│ Tree View                  │ Properties Panel                │
│                            │                                 │
│ 📦 Diagnosis               │ 📝 Age at Diagnosis (days)      │
│  ├─ 📦 Age at Diagnosis    │                                 │
│  ├─ 📦 Diagnosis Basis     │ Type: accordion                 │
│  └─ 📦 Disease Phase       │ Location: left sidebar          │
│                            │ Depth: 1                        │
│                            │                                 │
│                            │ Current Parent:                 │
│                            │ Diagnosis accordion             │
│                            │                                 │
│                            │ Change Parent:                  │
│                            │ [▼ Select Parent... ]           │
│                            │                                 │
│                            │ [✓ Apply Changes]               │
└────────────────────────────┴─────────────────────────────────┘
```

---

## 🔧 Common Tasks

### **Fix Wrong Parent:**
1. Find element in tree
2. Click to select
3. Choose correct parent from dropdown
4. Apply changes
5. Save

### **Move to Top-Level:**
1. Select element
2. Choose "-- Top-level (No parent) --" from dropdown
3. Apply changes
4. Save

### **Spot Duplicates:**
- Elements with same name at different levels
- Elements with depth=0 but have parent_name
- Elements marked with ⚠️ in tree

### **Fix Depth Issues:**
- When you change parent, depth auto-updates
- Parent depth + 1 = child depth
- Top-level elements always depth=0

---

## 💡 Icons Explained

| Icon | Meaning |
|------|---------|
| 📦 | Accordion |
| 📑 | Tab |
| ☑️ | Checkbox |
| 🔘 | Button |
| 📄 | Other element |
| ⚠️ | Issue detected |

---

## ⚠️ Validation Rules

**Automatic validation checks:**
- ✅ Depth matches parent hierarchy
- ✅ No circular references (parent can't be its own child)
- ✅ Only accordions can be parents
- ✅ Depth consistency (child depth = parent depth + 1)

**The system prevents:**
- ❌ Making element its own parent
- ❌ Invalid parent-child relationships
- ❌ Corrupting the registry

---

## 🎯 Real Example

**Problem:** "Age at Diagnosis (days)" appears at both top-level AND nested

**Before:**
```
📦 Age at Diagnosis (days) (depth=0, parent=None) ❌ WRONG
📦 Diagnosis (depth=0)
  └─ 📦 Age at Diagnosis (days) (depth=1, parent=Diagnosis) ✅ CORRECT
```

**Solution:**
1. Delete or ignore the top-level duplicate
2. Keep only the nested version
3. Or change top-level one's parent to Diagnosis

**After:**
```
📦 Diagnosis (depth=0)
  └─ 📦 Age at Diagnosis (days) (depth=1, parent=Diagnosis) ✅
```

---

## 💾 Backup & Safety

**Automatic backups:**
- Every save creates a backup in `element_maps/domain/versions/`
- Backup format: `page_backup_YYYYMMDD_HHMMSS.json`
- Can manually restore from backups if needed

**Manual restore:**
```bash
# If you need to rollback
cp element_maps/domain/versions/explore_backup_20260102_153000.json \
   element_maps/domain/explore_page.json
```

---

## 🚨 Troubleshooting

### **Tree not loading:**
- Make sure you parsed a page first
- Check console for errors (F12)
- Refresh page and try again

### **Can't save changes:**
- Make sure you clicked "Apply Changes" first
- Check that Save button is enabled (orange)
- Look for error messages in status bar

### **Changes not showing in agent:**
- Restart Flask after big changes
- Clear browser cache
- Re-deploy agent if needed

---

## 📊 Technical Details

**Files Created:**
- `web/templates/parser.html` - Enhanced with tree viewer modal
- `web/static/js/tree_viewer.js` - Tree viewer JavaScript
- `api/routes.py` - Added API endpoints:
  - `GET /api/parser/registry/<domain>/<page>` - Load registry
  - `PUT /api/parser/registry/<domain>/<page>` - Save registry

**Libraries Used:**
- `jsTree` - For tree visualization
- `jQuery` - For DOM manipulation

---

## 🎓 Best Practices

1. **Review before saving**
   - Check all changes make sense
   - Verify depth values updated
   - Look for any warnings

2. **Use descriptive edits**
   - Only change what needs fixing
   - Don't move elements unnecessarily

3. **Test after changes**
   - Run agent with updated registry
   - Verify elements still found correctly

4. **Keep backups**
   - System auto-backs up
   - But you can manual backup too:
     ```bash
     cp element_maps/domain/page.json backup_$(date +%Y%m%d).json
     ```

---

## 🎉 Benefits

**Before Tree Viewer:**
- ❌ Edit JSON manually
- ❌ Hard to see hierarchy
- ❌ Easy to make mistakes
- ❌ No validation

**After Tree Viewer:**
- ✅ Visual tree interface
- ✅ See all relationships
- ✅ Dropdown prevents errors
- ✅ Auto-validation
- ✅ Instant save
- ✅ Auto-backup

---

## 📞 Quick Reference

**Access:** Parser page → "🌳 View & Edit Element Tree"

**Keyboard Shortcuts:**
- (None yet - use buttons)

**API Endpoints:**
- Load: `GET /api/parser/registry/<domain>/<page>`
- Save: `PUT /api/parser/registry/<domain>/<page>`

---

**Happy Editing! 🌳✨**

*The parser is the heart of the system - now you can see it beat!*






