/**
 * Parser Tree Viewer & Editor
 * Visualize and edit element registry parent-child relationships
 */

// Wrap in IIFE to avoid conflicts with parser.js
(function() {
    // Local variables (won't conflict with parser.js)
    let treeCurrentRegistry = null;
    let treeCurrentDomain = null;
    let treeCurrentPage = null;
    let treeHasUnsavedChanges = false;
    let treeInstance = null;

    /**
     * Open the tree viewer modal
     */
    window.openTreeViewer = function() {
        const registryPath = document.getElementById('registryPath').textContent;
        if (!registryPath) {
            alert('No registry loaded. Please parse a page first.');
            return;
        }
        
        // Extract domain and page from path
        // Format: element_maps/domain/page.json
        const pathParts = registryPath.split('/');
        treeCurrentDomain = pathParts[pathParts.length - 2];
        treeCurrentPage = pathParts[pathParts.length - 1].replace('.json', '');
        
        document.getElementById('treeViewerModal').style.display = 'block';
        document.getElementById('treeSubtitle').textContent = `${treeCurrentDomain} / ${treeCurrentPage}`;
        
        loadRegistryTree();
    };

    /**
     * Open tree viewer from registry selector dropdown
     */
    window.openTreeViewerFromRegistry = function() {
        const selectEl = document.getElementById('registrySelect');
        const selectedValue = selectEl.value;
        
        if (!selectedValue) {
            alert('Please select a registry from the dropdown first.');
            return;
        }
        
        // Extract domain and page from selected value
        // Format: domain/page
        const parts = selectedValue.split('/');
        if (parts.length !== 2) {
            alert('Invalid registry format');
            return;
        }
        
        treeCurrentDomain = parts[0];
        treeCurrentPage = parts[1];
        
        document.getElementById('treeViewerModal').style.display = 'block';
        document.getElementById('treeSubtitle').textContent = `${treeCurrentDomain} / ${treeCurrentPage}`;
        
        loadRegistryTree();
    };

    /**
     * Close the tree viewer modal
     */
    window.closeTreeViewer = function() {
        if (treeHasUnsavedChanges) {
            if (!confirm('You have unsaved changes. Are you sure you want to close?')) {
                return;
            }
        }
        document.getElementById('treeViewerModal').style.display = 'none';
    };

    /**
     * Load registry and build tree
     */
    async function loadRegistryTree() {
        try {
            setStatus('Loading registry...', 'info');
            
            const response = await fetch(`/api/parser/registry?domain=${encodeURIComponent(treeCurrentDomain)}&page=${encodeURIComponent(treeCurrentPage)}`);
            if (!response.ok) {
                throw new Error('Failed to load registry');
            }
            
            treeCurrentRegistry = await response.json();
            buildTree(treeCurrentRegistry);
            
            setStatus(`Loaded ${Object.keys(treeCurrentRegistry.elements || {}).length} elements`, 'success');
        } catch (error) {
            console.error('Error loading registry:', error);
            setStatus('Error loading registry: ' + error.message, 'error');
            alert('Failed to load registry: ' + error.message);
        }
    }

    /**
     * Build jsTree from registry data
     */
    function buildTree(registry) {
        const elements = registry.elements || {};
        
        // Build tree structure
        const treeData = [];
        const processedIds = new Set();
        
        // Find top-level elements (no parent or parent=None)
        const topLevel = [];
        const nested = [];
        
        for (const [name, elem] of Object.entries(elements)) {
            const parent = elem.parent_name;
            if (!parent || parent === 'None') {
                topLevel.push({name, elem});
            } else {
                nested.push({name, elem});
            }
        }
        
        // Build tree nodes
        function createNode(name, elem) {
            const depth = elem.depth || 0;
            const type = elem.type || 'unknown';
            const parentName = elem.parent_name || 'None';
            
            // Determine icon and color
            let icon = '📄';
            if (type === 'accordion') icon = '📦';
            else if (type === 'tab') icon = '📑';
            else if (type === 'checkbox') icon = '☑️';
            else if (type === 'button') icon = '🔘';
            
            // Check for issues
            const issues = [];
            if (depth === 0 && parentName !== 'None') {
                issues.push('depth-mismatch');
            }
            
            // Find children
            const children = nested
                .filter(n => n.elem.parent_name === name)
                .map(n => createNode(n.name, n.elem));
            
            return {
                id: name,
                text: `${icon} ${name.split('(')[0].trim()} <span style="color: #999; font-size: 0.9em;">(depth=${depth})</span>`,
                data: {
                    name: name,
                    element: elem,
                    issues: issues
                },
                children: children.length > 0 ? children : undefined,
                state: {
                    opened: depth === 0
                }
            };
        }
        
        // Create top-level nodes
        for (const item of topLevel) {
            treeData.push(createNode(item.name, item.elem));
        }
        
        // Initialize jsTree
        $('#elementTree').jstree('destroy');  // Clear existing
        $('#elementTree').jstree({
            'core': {
                'data': treeData,
                'check_callback': true,
                'themes': {
                    'name': 'default',
                    'responsive': true
                }
            },
            'plugins': ['wholerow', 'types']
        }).on('select_node.jstree', function (e, data) {
            showElementProperties(data.node.data);
        });
        
        treeInstance = $('#elementTree').jstree(true);
    }

    /**
     * Show element properties in side panel
     */
    function showElementProperties(nodeData) {
        const {name, element, issues} = nodeData;
        
        const html = `
            <div style="background: white; padding: 15px; border-radius: 8px; margin-bottom: 15px;">
                <h4 style="margin-top: 0; color: #1976d2;">📝 ${name.split('(')[0].trim()}</h4>
                
                <div style="margin: 10px 0;">
                    <label style="display: block; font-weight: 600; margin-bottom: 5px; color: #555;">Type:</label>
                    <div style="padding: 8px; background: #f5f5f5; border-radius: 4px;">${element.type || 'N/A'}</div>
                </div>
                
                <div style="margin: 10px 0;">
                    <label style="display: block; font-weight: 600; margin-bottom: 5px; color: #555;">Location:</label>
                    <div style="padding: 8px; background: #f5f5f5; border-radius: 4px;">${element.location || 'N/A'}</div>
                </div>
                
                <div style="margin: 10px 0;">
                    <label style="display: block; font-weight: 600; margin-bottom: 5px; color: #555;">Depth:</label>
                    <div style="padding: 8px; background: #f5f5f5; border-radius: 4px;">${element.depth !== undefined ? element.depth : 'N/A'}</div>
                </div>
                
                <div style="margin: 10px 0;">
                    <label style="display: block; font-weight: 600; margin-bottom: 5px; color: #555;">Current Parent:</label>
                    <div style="padding: 8px; background: #f5f5f5; border-radius: 4px; word-wrap: break-word; font-size: 0.9em;">
                        ${element.parent_name || 'None (Top-level)'}
                    </div>
                </div>
                
                <div style="margin: 10px 0;">
                    <label style="display: block; font-weight: 600; margin-bottom: 5px; color: #555;">Change Parent:</label>
                    <select id="parentSelect" onchange="markUnsaved()" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; font-size: 0.9em;">
                        <option value="">-- Top-level (No parent) --</option>
                        ${getParentOptions(name, element)}
                    </select>
                </div>
                
                <div style="margin-top: 15px; padding-top: 15px; border-top: 2px solid #f0f0f0;">
                    <button onclick="deleteElementFromTree('${name.replace(/'/g, "\\'")}', this)" style="width: 100%; padding: 12px; background: linear-gradient(135deg, #f44336 0%, #d32f2f 100%); color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: 600; font-size: 1em; transition: all 0.3s; box-shadow: 0 3px 12px rgba(244,67,54,0.3);" onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 5px 18px rgba(244,67,54,0.4)'" onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 3px 12px rgba(244,67,54,0.3)'">
                        🗑️ Delete This Element
                    </button>
                </div>
                
                <div style="margin: 10px 0;">
                    <label style="display: block; font-weight: 600; margin-bottom: 5px; color: #555;">Selector:</label>
                    <div style="padding: 8px; background: #f5f5f5; border-radius: 4px; word-wrap: break-word; font-size: 0.85em; font-family: monospace;">
                        ${element.selector || 'N/A'}
                    </div>
                </div>
                
                ${issues.length > 0 ? `
                <div style="margin: 15px 0; padding: 10px; background: #fff3cd; border-left: 4px solid #ffc107; border-radius: 4px;">
                    <strong>⚠️ Issues:</strong>
                    <ul style="margin: 5px 0; padding-left: 20px;">
                        ${issues.map(i => `<li>${i}</li>`).join('')}
                    </ul>
                </div>
                ` : ''}
                
                <button onclick="applyChanges('${name.replace(/'/g, "\\'")}')" style="width: 100%; margin-top: 15px; padding: 10px; background: #4caf50; color: white; border: none; border-radius: 5px; cursor: pointer; font-weight: 600;">
                    ✓ Apply Changes
                </button>
            </div>
            
            <div style="background: white; padding: 15px; border-radius: 8px;">
                <h4 style="margin-top: 0; color: #666;">Statistics</h4>
                <p style="margin: 5px 0; font-size: 0.9em;"><strong>Usage Count:</strong> ${element.usage_count || 0}</p>
                <p style="margin: 5px 0; font-size: 0.9em;"><strong>Last Used:</strong> ${element.last_used ? new Date(element.last_used).toLocaleString() : 'Never'}</p>
                <p style="margin: 5px 0; font-size: 0.9em;"><strong>Source:</strong> ${element.source || 'N/A'}</p>
            </div>
        `;
        
        document.getElementById('elementProperties').innerHTML = html;
    }

    /**
     * Get parent options for dropdown
     */
    function getParentOptions(currentElementName, currentElement) {
        const elements = treeCurrentRegistry.elements || {};
        const options = [];
        
        // Get all accordion elements (potential parents)
        for (const [name, elem] of Object.entries(elements)) {
            // Skip self and non-accordions
            if (name === currentElementName) continue;
            if (elem.type !== 'accordion') continue;
            
            // Add as option
            const selected = (currentElement.parent_name === name) ? 'selected' : '';
            const displayName = name.split('(')[0].trim();
            options.push(`<option value="${name}" ${selected}>${displayName}</option>`);
        }
        
        return options.join('');
    }

    /**
     * Apply changes to an element
     */
    window.applyChanges = function(elementName) {
        const newParent = document.getElementById('parentSelect').value;
        
        if (!treeCurrentRegistry.elements[elementName]) {
            alert('Element not found');
            return;
        }
        
        const element = treeCurrentRegistry.elements[elementName];
        const oldParent = element.parent_name;
        
        // Update parent
        element.parent_name = newParent || 'None';
        
        // Update parent_text
        if (newParent) {
            element.parent_text = newParent.split(' accordion')[0].trim();
            // Update depth to parent's depth + 1
            const parentElem = treeCurrentRegistry.elements[newParent];
            if (parentElem) {
                element.depth = (parentElem.depth || 0) + 1;
            }
        } else {
            element.parent_text = null;
            element.depth = 0;
        }
        
        // Update parent_id
        if (newParent) {
            const parentElem = treeCurrentRegistry.elements[newParent];
            if (parentElem && parentElem.selector) {
                const idMatch = parentElem.selector.match(/id='([^']+)'/);
                element.parent_id = idMatch ? idMatch[1] : null;
            }
        } else {
            element.parent_id = null;
        }
        
        markUnsaved();
        setStatus(`Updated ${elementName.split('(')[0].trim()}`, 'success');
        
        // Rebuild tree to show changes
        buildTree(treeCurrentRegistry);
        
        alert(`✅ Changes applied!\n\nOld parent: ${oldParent || 'None'}\nNew parent: ${newParent || 'None'}\n\nClick "Save Changes" to persist.`);
    };

    /**
     * Mark as having unsaved changes
     */
    window.markUnsaved = function() {
        treeHasUnsavedChanges = true;
        document.getElementById('saveTreeBtn').disabled = false;
        document.getElementById('saveTreeBtn').style.background = '#ff9800';
        setStatus('Unsaved changes', 'warning');
    };

    /**
     * Save tree changes to server
     */
    window.saveTreeChanges = async function() {
        if (!treeHasUnsavedChanges) {
            alert('No changes to save');
            return;
        }
        
        if (!confirm('Save all changes to the registry?')) {
            return;
        }
        
        try {
            setStatus('Saving changes...', 'info');
            
            const response = await fetch(`/api/parser/registry?domain=${encodeURIComponent(treeCurrentDomain)}&page=${encodeURIComponent(treeCurrentPage)}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(treeCurrentRegistry)
            });
            
            if (!response.ok) {
                throw new Error('Failed to save changes');
            }
            
            const result = await response.json();
            
            treeHasUnsavedChanges = false;
            document.getElementById('saveTreeBtn').disabled = true;
            document.getElementById('saveTreeBtn').style.background = '#4caf50';
            
            setStatus('✅ Changes saved successfully!', 'success');
            alert('✅ Registry updated successfully!\n\nChanges have been saved and will be used by the agent immediately.');
            
        } catch (error) {
            console.error('Error saving changes:', error);
            setStatus('Error saving changes: ' + error.message, 'error');
            alert('Failed to save changes: ' + error.message);
        }
    };

    /**
     * Reload tree from server
     */
    window.reloadTree = function() {
        if (treeHasUnsavedChanges) {
            if (!confirm('Discard unsaved changes and reload?')) {
                return;
            }
        }
        treeHasUnsavedChanges = false;
        loadRegistryTree();
    };

    /**
     * Expand all tree nodes
     */
    window.expandAllNodes = function() {
        if (treeInstance) {
            treeInstance.open_all();
        }
    };

    /**
     * Collapse all tree nodes
     */
    window.collapseAllNodes = function() {
        if (treeInstance) {
            treeInstance.close_all();
        }
    };

    /**
     * Filter/search tree
     */
    window.filterTree = function() {
        const searchName = document.getElementById('searchName').value.toLowerCase();
        const filterType = document.getElementById('filterType').value;
        const filterDepth = document.getElementById('filterDepth').value;
        
        if (!treeInstance || !currentRegistry) return;
        
        let totalNodes = 0;
        let visibleNodes = 0;
        
        // Get all nodes
        const allNodes = treeInstance.get_json('#', {flat: true});
        
        allNodes.forEach(node => {
            if (node.id === '#') return; // Skip root
            
            totalNodes++;
            let shouldShow = true;
            
            // Get node data
            const nodeData = node.data;
            if (!nodeData) return;
            
            const element = nodeData.element;
            const name = nodeData.name.toLowerCase();
            
            // Filter by name
            if (searchName && !name.includes(searchName)) {
                shouldShow = false;
            }
            
            // Filter by type
            if (filterType && element.type !== filterType) {
                shouldShow = false;
            }
            
            // Filter by depth
            if (filterDepth) {
                const depth = element.depth !== undefined ? element.depth : 0;
                if (filterDepth === '4+') {
                    if (depth < 4) shouldShow = false;
                } else {
                    if (depth !== parseInt(filterDepth)) shouldShow = false;
                }
            }
            
            // Show/hide node
            if (shouldShow) {
                treeInstance.show_node(node.id);
                visibleNodes++;
                // Show all parent nodes too
                let parent = treeInstance.get_parent(node.id);
                while (parent && parent !== '#') {
                    treeInstance.show_node(parent);
                    parent = treeInstance.get_parent(parent);
                }
            } else {
                treeInstance.hide_node(node.id);
            }
        });
        
        // Update stats
        const statsEl = document.getElementById('filterStats');
        if (searchName || filterType || filterDepth) {
            statsEl.textContent = `Showing ${visibleNodes} of ${totalNodes} elements`;
            statsEl.style.color = '#2196f3';
            statsEl.style.fontWeight = '600';
        } else {
            statsEl.textContent = '';
        }
    };

    /**
     * Clear all filters
     */
    window.clearFilters = function() {
        document.getElementById('searchName').value = '';
        document.getElementById('filterType').value = '';
        document.getElementById('filterDepth').value = '';
        
        if (treeInstance) {
            treeInstance.show_all();
        }
        
        document.getElementById('filterStats').textContent = '';
    };

    /**
     * Show add element form
     */
    window.showAddElementForm = function() {
        // Populate parent select options
        const parentSelect = document.getElementById('newElementParent');
        parentSelect.innerHTML = '<option value="">-- Top-level (No parent) --</option>';
        
        if (currentRegistry && currentRegistry.elements) {
            const elementNames = Object.keys(currentRegistry.elements).sort();
            elementNames.forEach(name => {
                const option = document.createElement('option');
                option.value = name;
                option.textContent = name.length > 60 ? name.substring(0, 60) + '...' : name;
                parentSelect.appendChild(option);
            });
        }
        
        // Show modal
        document.getElementById('addElementModal').style.display = 'block';
    };

    /**
     * Close add element form
     */
    window.closeAddElementForm = function() {
        document.getElementById('addElementModal').style.display = 'none';
        document.getElementById('addElementForm').reset();
    };

    /**
     * Add new element to registry
     */
    window.addNewElement = function(event) {
        event.preventDefault();
        
        const name = document.getElementById('newElementName').value.trim();
        const type = document.getElementById('newElementType').value;
        const selector = document.getElementById('newElementSelector').value.trim();
        const parent = document.getElementById('newElementParent').value;
        const location = document.getElementById('newElementLocation').value.trim();
        const text = document.getElementById('newElementText').value.trim();
        
        if (!name || !type || !selector) {
            alert('Please fill in all required fields (Name, Type, Selector)');
            return;
        }
        
        // Check if element already exists
        if (currentRegistry && currentRegistry.elements && name in currentRegistry.elements) {
            if (!confirm(`An element named "${name}" already exists. Overwrite it?`)) {
                return;
            }
        }
        
        // Create new element
        const newElement = {
            type: type,
            selector: selector,
            source: 'manual_add',
            added_at: new Date().toISOString()
        };
        
        if (location) newElement.location = location;
        if (text) newElement.text = text;
        if (parent) {
            newElement.parent_name = parent;
            newElement.parent_text = parent.split(' accordion')[0];
        }
        
        // Add to registry
        if (!currentRegistry.elements) {
            currentRegistry.elements = {};
        }
        currentRegistry.elements[name] = newElement;
        
        // Update parent-child relationships
        if (parent) {
            if (!currentRegistry.parent_child_relationships) {
                currentRegistry.parent_child_relationships = {};
            }
            if (!currentRegistry.parent_child_relationships[parent]) {
                currentRegistry.parent_child_relationships[parent] = [];
            }
            if (!currentRegistry.parent_child_relationships[parent].includes(name)) {
                currentRegistry.parent_child_relationships[parent].push(name);
            }
        }
        
        // Mark as unsaved and rebuild tree
        markUnsaved();
        buildTree();
        
        // Close form
        closeAddElementForm();
        
        alert(`✅ Element "${name}" added successfully!\n\nClick "💾 Save Changes" to persist.`);
    };

    /**
     * Delete element from tree
     */
    window.deleteElementFromTree = function(elementName, buttonElement) {
        if (!confirm(`⚠️ Are you sure you want to DELETE this element?\n\n"${elementName}"\n\nThis will remove it from the registry and cannot be undone after saving!`)) {
            return;
        }

        // Find and remove from currentRegistry
        if (currentRegistry && currentRegistry.elements) {
            if (elementName in currentRegistry.elements) {
                delete currentRegistry.elements[elementName];
                
                // Also remove from parent_child_relationships if present
                if (currentRegistry.parent_child_relationships) {
                    // Remove as a parent
                    delete currentRegistry.parent_child_relationships[elementName];
                    
                    // Remove as a child from other parents
                    for (let parent in currentRegistry.parent_child_relationships) {
                        const children = currentRegistry.parent_child_relationships[parent];
                        const index = children.indexOf(elementName);
                        if (index > -1) {
                            children.splice(index, 1);
                        }
                    }
                }
                
                // Mark as unsaved and rebuild tree
                markUnsaved();
                buildTree();
                
                // Clear properties panel
                document.getElementById('elementProperties').innerHTML = '<p style="color: #666; text-align: center; padding: 20px;">✅ Element deleted. Select another element or save changes.</p>';
                
                alert('✅ Element deleted! Click "💾 Save Changes" to persist.');
            } else {
                alert('❌ Element not found in registry');
            }
        }
    };

    /**
     * Set status message
     */
    function setStatus(message, type) {
        const statusEl = document.getElementById('treeStatus');
        statusEl.textContent = message;
        
        // Color based on type
        const colors = {
            'info': '#2196f3',
            'success': '#4caf50',
            'warning': '#ff9800',
            'error': '#f44336'
        };
        
        statusEl.style.background = colors[type] || '#fff';
        statusEl.style.color = (type === 'info' || type === 'success' || type === 'warning' || type === 'error') ? 'white' : '#333';
    }
})();
