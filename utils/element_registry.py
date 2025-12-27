"""
Element Registry - Loads and manages element maps with learning capability
"""

import json
import os
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path


class ElementRegistry:
    """Manages element maps with versioning and learning"""
    
    def __init__(self, maps_dir: str = "element_maps"):
        self.maps_dir = Path(maps_dir)
        self.maps_dir.mkdir(parents=True, exist_ok=True)
        self.current_maps = {}  # Cache loaded maps
        
    def get_map_path(self, domain: str, page: str) -> Path:
        """Get path to element map file"""
        # Clean domain name
        domain = domain.replace('https://', '').replace('http://', '').replace('#/', '')
        domain_dir = self.maps_dir / domain
        domain_dir.mkdir(parents=True, exist_ok=True)
        return domain_dir / f"{page}_page.json"
    
    def load_map(self, domain: str, page: str) -> Optional[Dict[str, Any]]:
        """Load element map for a specific page"""
        map_path = self.get_map_path(domain, page)
        
        if not map_path.exists():
            return None
        
        try:
            with open(map_path, 'r') as f:
                element_map = json.load(f)
            
            # Cache it
            cache_key = f"{domain}:{page}"
            self.current_maps[cache_key] = element_map
            
            return element_map
        except Exception as e:
            print(f"Error loading map from {map_path}: {e}")
            return None
    
    def save_map(self, domain: str, page: str, element_map: Dict[str, Any]):
        """Save element map to file"""
        map_path = self.get_map_path(domain, page)
        
        # Update timestamp
        element_map["last_updated"] = datetime.utcnow().isoformat() + "Z"
        
        # Save to file
        with open(map_path, 'w') as f:
            json.dump(element_map, f, indent=2)
        
        # Update cache
        cache_key = f"{domain}:{page}"
        self.current_maps[cache_key] = element_map
        
        print(f"✅ Saved element map: {map_path}")
    
    def get_element(self, domain: str, page: str, element_name: str) -> Optional[Dict[str, Any]]:
        """Get specific element from map"""
        cache_key = f"{domain}:{page}"
        
        # Load map if not cached
        if cache_key not in self.current_maps:
            self.load_map(domain, page)
        
        if cache_key not in self.current_maps:
            return None
        
        elements = self.current_maps[cache_key].get("elements", {})
        return elements.get(element_name)
    
    def add_element(self, domain: str, page: str, element_name: str, element_data: Dict[str, Any], test_id: str = ""):
        """Add new element discovered by LLM"""
        cache_key = f"{domain}:{page}"
        
        # Load existing map or create new one
        if cache_key not in self.current_maps:
            element_map = self.load_map(domain, page)
            if not element_map:
                # Create new map
                element_map = {
                    "page": page,
                    "url": f"https://{domain}",
                    "version": "1.0",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "elements": {},
                    "statistics": {
                        "total_elements": 0,
                        "parsed_elements": 0,
                        "discovered_elements": 0
                    }
                }
                self.current_maps[cache_key] = element_map
        
        # Add element
        element_map = self.current_maps[cache_key]
        
        # Mark as discovered
        element_data["source"] = "llm_discovery"
        element_data["discovered_at"] = datetime.utcnow().isoformat() + "Z"
        element_data["discovered_in"] = test_id
        element_data["usage_count"] = 1
        element_data["last_used"] = datetime.utcnow().isoformat() + "Z"
        
        element_map["elements"][element_name] = element_data
        
        # Update statistics
        element_map["statistics"]["total_elements"] = len(element_map["elements"])
        element_map["statistics"]["discovered_elements"] += 1
        
        # Increment version
        current_version = float(element_map.get("version", "1.0"))
        element_map["version"] = f"{current_version + 0.1:.1f}"
        
        # Save updated map
        self.save_map(domain, page, element_map)
        
        print(f"✅ Added new element: {element_name} (discovered by LLM in {test_id})")
    
    def update_usage(self, domain: str, page: str, element_name: str):
        """Update usage statistics for an element"""
        element = self.get_element(domain, page, element_name)
        if not element:
            return
        
        # Update usage count
        element["usage_count"] = element.get("usage_count", 0) + 1
        element["last_used"] = datetime.utcnow().isoformat() + "Z"
        
        # Save updated map
        cache_key = f"{domain}:{page}"
        if cache_key in self.current_maps:
            self.save_map(domain, page, self.current_maps[cache_key])
    
    def update_with_discovery(self, domain: str, page: str, discovery_data: Dict[str, Any]):
        """
        Update registry with discovery metadata (both original query and final selector)
        
        Args:
            discovery_data: {
                "name": "Tumor Classification",
                "original_query": "text=Tumor Classification",
                "final_selector": "div[role='button'][aria-expanded]:has-text('Tumor Classification')",
                "discovery_method": "tree_climbing",
                "metadata": {"tree_depth": 2, "relationship": "grandparent"}
            }
        """
        cache_key = f"{domain}:{page}"
        
        # Load existing map or create new one
        if cache_key not in self.current_maps:
            element_map = self.load_map(domain, page)
            if not element_map:
                # Create new map
                element_map = {
                    "page": page,
                    "url": f"https://{domain}",
                    "version": "1.0",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "elements": {},
                    "statistics": {
                        "total_elements": 0,
                        "parsed_elements": 0,
                        "discovered_elements": 0
                    }
                }
                self.current_maps[cache_key] = element_map
        
        element_map = self.current_maps[cache_key]
        element_name = discovery_data.get("name", "unknown")
        original_query = discovery_data.get("original_query", "")
        final_selector = discovery_data.get("final_selector", "")
        
        # 🔍 SMART KEY MATCHING - Try multiple strategies to find existing element
        existing_key = None
        
        # Strategy 1: Try exact name match
        if element_name in element_map["elements"]:
            existing_key = element_name
            print(f"  🎯 Found exact match by name: {element_name}")
        
        # Strategy 2: Try original query match (e.g., "text=Primary")
        elif original_query and original_query in element_map["elements"]:
            existing_key = original_query
            print(f"  🎯 Found match by original query: {original_query}")
        
        # Strategy 3: Try fuzzy text matching (e.g., "Primary" in "text=Primary")
        else:
            for key in element_map["elements"].keys():
                # Check if element_name is substring of key or vice versa
                if element_name.lower() in key.lower() or key.lower() in element_name.lower():
                    existing_key = key
                    print(f"  🎯 Found fuzzy match: '{element_name}' → '{key}'")
                    break
        
        # Strategy 4: Check if we've seen this selector/query before (different key)
        if not existing_key:
            for key, elem_data in element_map["elements"].items():
                if (elem_data.get("query") == original_query or 
                    elem_data.get("selector") == final_selector):
                    existing_key = key
                    print(f"  🎯 Found match by selector/query: '{element_name}' → '{key}'")
                    break
        
        # Now update or create
        if existing_key:
            # UPDATE existing entry (keep same key, update selector)
            element = element_map["elements"][existing_key]
            print(f"  📝 Updating existing element: {existing_key}")
            print(f"     OLD selector: {element.get('selector')}")
            print(f"     NEW selector: {final_selector}")
            is_new = False
        else:
            # ADD new entry
            element = {}
            existing_key = element_name  # Use element_name as the new key
            print(f"  ✅ Adding new element: {element_name}")
            is_new = True
        
        # Update with discovery data
        element.update({
            "query": original_query,
            "selector": final_selector,  # This is the STABLE selector for Playwright!
            "type": "discovered",
            "discovery": {
                "method": discovery_data.get("discovery_method"),
                "metadata": discovery_data.get("metadata", {}),
                "discovered_at": datetime.utcnow().isoformat() + "Z"
            },
            "usage_count": element.get("usage_count", 0) + 1,
            "last_used": datetime.utcnow().isoformat() + "Z"
        })
        
        # Save back using the found/new key
        element_map["elements"][existing_key] = element
        
        # Update statistics
        if is_new:
            element_map["statistics"]["discovered_elements"] = element_map["statistics"].get("discovered_elements", 0) + 1
        element_map["statistics"]["total_elements"] = len(element_map["elements"])
        
        # Increment version
        current_version = float(element_map.get("version", "1.0"))
        element_map["version"] = f"{current_version + 0.1:.1f}"
        
        # Save updated map
        self.save_map(domain, page, element_map)
        
        print(f"  💾 Registry updated for: {element_name}")
        print(f"     Query: {discovery_data.get('original_query')}")
        print(f"     Final: {discovery_data.get('final_selector')}")
        print(f"     Method: {discovery_data.get('discovery_method')}")
    
    def compare_maps(self, domain: str, page: str, baseline_version: str = None) -> Dict[str, Any]:
        """
        Compare current map with baseline version
        For regression testing
        """
        current_map = self.load_map(domain, page)
        if not current_map:
            return {"error": "Current map not found"}
        
        # Load baseline (if version specified, load from versions/)
        if baseline_version:
            versions_dir = self.maps_dir / domain / "versions"
            baseline_path = versions_dir / f"{page}_page_v{baseline_version}.json"
        else:
            # Use current as baseline for now (would need git integration for true baseline)
            baseline_path = self.get_map_path(domain, page)
        
        if not baseline_path.exists():
            return {"error": "Baseline map not found"}
        
        with open(baseline_path, 'r') as f:
            baseline_map = json.load(f)
        
        # Compare elements
        baseline_elements = baseline_map.get("elements", {})
        current_elements = current_map.get("elements", {})
        
        comparison = {
            "baseline_version": baseline_map.get("version"),
            "current_version": current_map.get("version"),
            "changed": [],
            "added": [],
            "removed": [],
            "unchanged": []
        }
        
        # Find changed and removed
        for name, baseline_elem in baseline_elements.items():
            if name not in current_elements:
                comparison["removed"].append({
                    "name": name,
                    "selector": baseline_elem.get("selector")
                })
            elif baseline_elem.get("selector") != current_elements[name].get("selector"):
                comparison["changed"].append({
                    "name": name,
                    "old_selector": baseline_elem.get("selector"),
                    "new_selector": current_elements[name].get("selector")
                })
            else:
                comparison["unchanged"].append(name)
        
        # Find added
        for name, current_elem in current_elements.items():
            if name not in baseline_elements:
                comparison["added"].append({
                    "name": name,
                    "selector": current_elem.get("selector"),
                    "source": current_elem.get("source")
                })
        
        # Calculate risk level
        breaking_changes = len(comparison["changed"]) + len(comparison["removed"])
        if breaking_changes > 5:
            risk_level = "CRITICAL"
        elif breaking_changes > 2:
            risk_level = "HIGH"
        elif breaking_changes > 0:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"
        
        comparison["risk_level"] = risk_level
        comparison["breaking_changes"] = breaking_changes
        
        return comparison
    
    def create_baseline(self, domain: str, page: str):
        """
        Create baseline version for regression testing
        Copies current map to versions/
        """
        current_map = self.load_map(domain, page)
        if not current_map:
            print(f"❌ No map found to create baseline")
            return
        
        # Create versions directory
        versions_dir = self.maps_dir / domain / "versions"
        versions_dir.mkdir(parents=True, exist_ok=True)
        
        # Save as versioned baseline
        version = current_map.get("version", "1.0")
        baseline_path = versions_dir / f"{page}_page_v{version}.json"
        
        with open(baseline_path, 'w') as f:
            json.dump(current_map, f, indent=2)
        
        print(f"✅ Created baseline: {baseline_path}")
        return baseline_path


# Global registry instance
_registry = None

def get_registry(maps_dir: str = "element_maps") -> ElementRegistry:
    """Get global registry instance"""
    global _registry
    if _registry is None:
        _registry = ElementRegistry(maps_dir)
    return _registry
