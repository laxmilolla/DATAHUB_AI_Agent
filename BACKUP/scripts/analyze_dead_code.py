#!/usr/bin/env python3
"""
Dead Code Analyzer
Identifies unused code, imports, functions, and files
"""
import ast
import os
import re
from pathlib import Path
from collections import defaultdict
from typing import Dict, Set, List, Tuple

class DeadCodeAnalyzer:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.all_files = {}
        self.imports = defaultdict(set)  # file -> set of imports
        self.defined_functions = defaultdict(set)  # file -> set of functions
        self.defined_classes = defaultdict(set)  # file -> set of classes
        self.used_imports = defaultdict(set)  # file -> set of used imports
        self.used_functions = defaultdict(set)  # file -> set of used functions
        self.used_classes = defaultdict(set)  # file -> set of used classes
        
    def analyze_file(self, file_path: Path) -> Dict:
        """Analyze a single Python file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content, filename=str(file_path))
            
            imports = set()
            functions = set()
            classes = set()
            used_names = set()
            
            for node in ast.walk(tree):
                # Collect imports
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.add(alias.name.split('.')[0])
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.add(node.module.split('.')[0])
                
                # Collect function definitions
                if isinstance(node, ast.FunctionDef):
                    functions.add(node.name)
                
                # Collect class definitions
                if isinstance(node, ast.ClassDef):
                    classes.add(node.name)
                
                # Collect used names (function calls, attribute access)
                if isinstance(node, ast.Name):
                    used_names.add(node.id)
                elif isinstance(node, ast.Attribute):
                    if isinstance(node.value, ast.Name):
                        used_names.add(node.value.id)
            
            return {
                'imports': imports,
                'functions': functions,
                'classes': classes,
                'used_names': used_names
            }
        except Exception as e:
            print(f"⚠️ Error analyzing {file_path}: {e}")
            return {'imports': set(), 'functions': set(), 'classes': set(), 'used_names': set()}
    
    def scan_project(self):
        """Scan entire project"""
        print("🔍 Scanning project for Python files...")
        
        # Find all Python files
        python_files = []
        exclude_dirs = {'venv', '__pycache__', '.git', 'node_modules', 'BACKUP', 'Test', 'storage'}
        
        for root, dirs, files in os.walk(self.project_root):
            # Remove excluded directories from dirs list
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            for file in files:
                if file.endswith('.py'):
                    file_path = Path(root) / file
                    python_files.append(file_path)
        
        print(f"📁 Found {len(python_files)} Python files")
        
        # Analyze each file
        for file_path in python_files:
            rel_path = file_path.relative_to(self.project_root)
            self.all_files[rel_path] = file_path
            analysis = self.analyze_file(file_path)
            
            self.imports[rel_path] = analysis['imports']
            self.defined_functions[rel_path] = analysis['functions']
            self.defined_classes[rel_path] = analysis['classes']
            self.used_imports[rel_path] = analysis['used_names']
        
        print("✅ Analysis complete")
    
    def find_unused_imports(self) -> Dict[str, List[str]]:
        """Find imports that are never used"""
        unused = {}
        
        for file_path, imports in self.imports.items():
            unused_in_file = []
            used = self.used_imports[file_path]
            
            for imp in imports:
                # Check if import is used (directly or as prefix)
                if imp not in used and not any(name.startswith(imp + '.') for name in used):
                    unused_in_file.append(imp)
            
            if unused_in_file:
                unused[str(file_path)] = unused_in_file
        
        return unused
    
    def find_unused_functions(self) -> Dict[str, List[str]]:
        """Find functions that are never called"""
        unused = {}
        
        # Build a map of all function definitions
        all_functions = {}
        for file_path, functions in self.defined_functions.items():
            for func in functions:
                all_functions[func] = str(file_path)
        
        # Check if functions are used
        for file_path, functions in self.defined_functions.items():
            unused_in_file = []
            
            for func in functions:
                # Check if function is used anywhere
                is_used = False
                for other_file, used_names in self.used_imports.items():
                    if func in used_names:
                        # Check if it's imported from this file
                        if other_file != file_path:
                            # Check if file imports from this module
                            module_name = str(file_path).replace('/', '.').replace('\\', '.').replace('.py', '')
                            if module_name in self.imports[other_file]:
                                is_used = True
                                break
                        else:
                            # Same file - check if it's called
                            is_used = True
                            break
                
                if not is_used:
                    unused_in_file.append(func)
            
            if unused_in_file:
                unused[str(file_path)] = unused_in_file
        
        return unused
    
    def find_unused_files(self) -> List[str]:
        """Find Python files that are never imported"""
        unused_files = []
        
        # Entry points (files that are run directly)
        entry_points = {
            'api/app.py',
            'api/routes.py',
            'REFACTOR/api/excel_routes.py',
            'Experimented/api/instructions_routes.py',
        }
        
        # Find all imported modules
        imported_modules = set()
        for file_path, imports in self.imports.items():
            for imp in imports:
                # Try to find the file
                possible_paths = [
                    f"{imp}.py",
                    f"{imp}/__init__.py",
                    f"{imp.replace('.', '/')}.py",
                ]
                for possible in possible_paths:
                    imported_modules.add(possible)
        
        # Check each file
        for file_path in self.all_files.keys():
            file_str = str(file_path)
            
            # Skip entry points
            if any(file_str.endswith(ep) for ep in entry_points):
                continue
            
            # Skip __init__.py files
            if file_path.name == '__init__.py':
                continue
            
            # Check if file is imported
            is_imported = False
            for imported in imported_modules:
                if file_str.endswith(imported) or imported in file_str:
                    is_imported = True
                    break
            
            # Also check if it's referenced in any import statement
            if not is_imported:
                module_name = str(file_path).replace('/', '.').replace('\\', '.').replace('.py', '')
                for other_file, imports in self.imports.items():
                    if module_name in imports or any(imp.startswith(module_name) for imp in imports):
                        is_imported = True
                        break
            
            if not is_imported:
                unused_files.append(file_str)
        
        return unused_files
    
    def find_unused_routes(self) -> Dict[str, List[str]]:
        """Find Flask routes that are never called"""
        unused_routes = {}
        
        # Find all route definitions
        route_pattern = r'@(?:bp|app|bp_excel|bp_instructions)\.route\([\'"]([^\'"]+)[\'"]'
        
        for file_path in self.all_files.values():
            if 'routes' not in str(file_path).lower():
                continue
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                routes = re.findall(route_pattern, content)
                
                # Check if routes are referenced in frontend JS/HTML
                unused_in_file = []
                for route in routes:
                    # Check frontend files
                    frontend_files = list(self.project_root.glob('web/**/*.js')) + \
                                   list(self.project_root.glob('web/**/*.html'))
                    
                    is_used = False
                    for frontend_file in frontend_files:
                        try:
                            with open(frontend_file, 'r', encoding='utf-8') as f:
                                if route in f.read():
                                    is_used = True
                                    break
                        except:
                            pass
                    
                    if not is_used:
                        unused_in_file.append(route)
                
                if unused_in_file:
                    unused_routes[str(file_path)] = unused_in_file
            except Exception as e:
                print(f"⚠️ Error checking routes in {file_path}: {e}")
        
        return unused_routes
    
    def generate_report(self):
        """Generate comprehensive dead code report"""
        print("\n" + "="*80)
        print("📊 DEAD CODE ANALYSIS REPORT")
        print("="*80)
        
        # Unused imports
        print("\n🔴 UNUSED IMPORTS:")
        print("-" * 80)
        unused_imports = self.find_unused_imports()
        if unused_imports:
            for file_path, imports in sorted(unused_imports.items()):
                print(f"\n{file_path}:")
                for imp in sorted(imports):
                    print(f"  - {imp}")
        else:
            print("✅ No unused imports found")
        
        # Unused functions
        print("\n🔴 UNUSED FUNCTIONS:")
        print("-" * 80)
        unused_functions = self.find_unused_functions()
        if unused_functions:
            for file_path, functions in sorted(unused_functions.items()):
                print(f"\n{file_path}:")
                for func in sorted(functions):
                    print(f"  - {func}")
        else:
            print("✅ No unused functions found")
        
        # Unused files
        print("\n🔴 POTENTIALLY UNUSED FILES:")
        print("-" * 80)
        unused_files = self.find_unused_files()
        if unused_files:
            for file_path in sorted(unused_files):
                print(f"  - {file_path}")
        else:
            print("✅ No unused files found")
        
        # Unused routes
        print("\n🔴 UNUSED ROUTES:")
        print("-" * 80)
        unused_routes = self.find_unused_routes()
        if unused_routes:
            for file_path, routes in sorted(unused_routes.items()):
                print(f"\n{file_path}:")
                for route in sorted(routes):
                    print(f"  - {route}")
        else:
            print("✅ No unused routes found")
        
        # Summary
        print("\n" + "="*80)
        print("📈 SUMMARY")
        print("="*80)
        print(f"Total files analyzed: {len(self.all_files)}")
        print(f"Files with unused imports: {len(unused_imports)}")
        print(f"Files with unused functions: {len(unused_functions)}")
        print(f"Potentially unused files: {len(unused_files)}")
        print(f"Files with unused routes: {len(unused_routes)}")
        print("="*80)


def main():
    project_root = Path(__file__).parent
    analyzer = DeadCodeAnalyzer(project_root)
    analyzer.scan_project()
    analyzer.generate_report()


if __name__ == '__main__':
    main()

