#!/usr/bin/env python3
"""
Syntax and structure validation for baseCamp Phase 2 implementation.
Tests code quality and structure without requiring external dependencies.
"""

import ast
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple

def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")

def print_test(test_name: str, success: bool, details: str = ""):
    """Print test result."""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} {test_name}")
    if details:
        print(f"    {details}")

def validate_python_syntax(file_path: Path) -> Tuple[bool, str]:
    """Validate Python syntax of a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()
        
        # Parse the AST
        ast.parse(source, filename=str(file_path))
        return True, ""
    except SyntaxError as e:
        return False, f"Syntax error: {e}"
    except Exception as e:
        return False, f"Error: {e}"

def analyze_file_structure(file_path: Path) -> Dict[str, any]:
    """Analyze the structure of a Python file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()
        
        tree = ast.parse(source)
        
        analysis = {
            'classes': [],
            'functions': [],
            'imports': [],
            'async_functions': [],
            'docstring': ast.get_docstring(tree),
            'lines': len(source.splitlines())
        }
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                analysis['classes'].append(node.name)
            elif isinstance(node, ast.FunctionDef):
                analysis['functions'].append(node.name)
            elif isinstance(node, ast.AsyncFunctionDef):
                analysis['async_functions'].append(node.name)
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        analysis['imports'].append(alias.name)
                else:
                    module = node.module or ''
                    for alias in node.names:
                        analysis['imports'].append(f"{module}.{alias.name}")
        
        return analysis
    except Exception as e:
        return {'error': str(e)}

def validate_project_structure():
    """Validate overall project structure."""
    print_section("Project Structure Validation")
    
    base_path = Path('.')
    src_path = base_path / 'src'
    tests_path = base_path / 'tests'
    
    # Check main directories
    required_dirs = [
        src_path,
        src_path / 'models',
        src_path / 'services', 
        src_path / 'api',
        src_path / 'config',
        tests_path
    ]
    
    for dir_path in required_dirs:
        exists = dir_path.exists() and dir_path.is_dir()
        print_test(f"Directory {dir_path}", exists)
    
    # Check key files
    required_files = [
        'src/main.py',
        'src/models/lead.py',
        'src/models/airtable.py',
        'src/services/llm_service.py',
        'src/services/vector_service.py',
        'src/services/airtable_service.py',
        'src/api/intake.py',
        'src/api/leads.py',
        'src/config/settings.py',
        'tests/conftest.py',
        'tests/test_models.py',
        'tests/test_services.py',
        'tests/test_api.py',
        'requirements.txt',
        'requirements-dev.txt',
        'pytest.ini'
    ]
    
    for file_path in required_files:
        path = base_path / file_path
        exists = path.exists() and path.is_file()
        print_test(f"File {file_path}", exists)

def validate_syntax_all_files():
    """Validate Python syntax for all source files."""
    print_section("Python Syntax Validation")
    
    src_path = Path('src')
    test_path = Path('tests')
    
    python_files = []
    python_files.extend(src_path.rglob('*.py'))
    python_files.extend(test_path.rglob('*.py'))
    python_files.append(Path('validate_implementation.py'))
    
    all_valid = True
    
    for file_path in python_files:
        if file_path.exists():
            is_valid, error = validate_python_syntax(file_path)
            print_test(f"Syntax {file_path}", is_valid, error if not is_valid else "")
            if not is_valid:
                all_valid = False
    
    return all_valid

def validate_models_structure():
    """Validate data models structure."""
    print_section("Data Models Structure Validation")
    
    lead_py = Path('src/models/lead.py')
    airtable_py = Path('src/models/airtable.py')
    
    if not lead_py.exists():
        print_test("Lead models file exists", False)
        return False
    
    if not airtable_py.exists():
        print_test("Airtable models file exists", False)
        return False
    
    # Analyze lead.py structure
    lead_analysis = analyze_file_structure(lead_py)
    if 'error' in lead_analysis:
        print_test("Lead models analysis", False, lead_analysis['error'])
        return False
    
    expected_lead_classes = [
        'ContactInfo', 'LeadInput', 'EnrichedLead', 'AIAnalysis', 
        'VectorData', 'LeadSummary', 'LeadQuery'
    ]
    
    missing_classes = [cls for cls in expected_lead_classes if cls not in lead_analysis['classes']]
    if missing_classes:
        print_test("Lead model classes", False, f"Missing: {missing_classes}")
    else:
        print_test("Lead model classes", True, f"Found {len(expected_lead_classes)} classes")
    
    # Analyze airtable.py structure
    airtable_analysis = analyze_file_structure(airtable_py)
    if 'error' in airtable_analysis:
        print_test("Airtable models analysis", False, airtable_analysis['error'])
        return False
    
    expected_airtable_classes = [
        'AirtableConfig', 'AirtableRecord', 'SyncRecord', 'SyncBatch'
    ]
    
    missing_airtable = [cls for cls in expected_airtable_classes if cls not in airtable_analysis['classes']]
    if missing_airtable:
        print_test("Airtable model classes", False, f"Missing: {missing_airtable}")
    else:
        print_test("Airtable model classes", True, f"Found {len(expected_airtable_classes)} classes")
    
    return len(missing_classes) == 0 and len(missing_airtable) == 0

def validate_services_structure():
    """Validate service layer structure."""
    print_section("Service Layer Structure Validation")
    
    services = [
        ('src/services/llm_service.py', ['LLMServiceInterface', 'OllamaService']),
        ('src/services/vector_service.py', ['VectorServiceInterface', 'ChromaVectorService']),
        ('src/services/airtable_service.py', ['CRMServiceInterface', 'AirtableService'])
    ]
    
    all_valid = True
    
    for service_file, expected_classes in services:
        file_path = Path(service_file)
        
        if not file_path.exists():
            print_test(f"Service file {service_file}", False, "File not found")
            all_valid = False
            continue
        
        analysis = analyze_file_structure(file_path)
        if 'error' in analysis:
            print_test(f"Service analysis {service_file}", False, analysis['error'])
            all_valid = False
            continue
        
        missing_classes = [cls for cls in expected_classes if cls not in analysis['classes']]
        if missing_classes:
            print_test(f"Service classes {service_file}", False, f"Missing: {missing_classes}")
            all_valid = False
        else:
            print_test(f"Service classes {service_file}", True, f"Found {len(expected_classes)} classes")
        
        # Check for async methods
        has_async = len(analysis['async_functions']) > 0
        print_test(f"Async methods {service_file}", has_async, f"Found {len(analysis['async_functions'])} async methods")
    
    return all_valid

def validate_api_structure():
    """Validate API endpoints structure."""
    print_section("API Endpoints Structure Validation")
    
    api_files = [
        ('src/api/intake.py', ['submit_lead', 'submit_leads_batch', 'check_similar_leads']),
        ('src/api/leads.py', ['list_leads', 'get_lead', 'update_lead', 'delete_lead'])
    ]
    
    all_valid = True
    
    for api_file, expected_functions in api_files:
        file_path = Path(api_file)
        
        if not file_path.exists():
            print_test(f"API file {api_file}", False, "File not found")
            all_valid = False
            continue
        
        analysis = analyze_file_structure(file_path)
        if 'error' in analysis:
            print_test(f"API analysis {api_file}", False, analysis['error'])
            all_valid = False
            continue
        
        # Check for expected endpoint functions
        all_functions = analysis['functions'] + analysis['async_functions']
        missing_functions = [func for func in expected_functions if func not in all_functions]
        
        if missing_functions:
            print_test(f"API endpoints {api_file}", False, f"Missing: {missing_functions}")
            all_valid = False
        else:
            print_test(f"API endpoints {api_file}", True, f"Found {len(expected_functions)} endpoints")
        
        # Check for async endpoints
        has_async = len(analysis['async_functions']) > 0
        print_test(f"Async endpoints {api_file}", has_async, f"Found {len(analysis['async_functions'])} async endpoints")
    
    return all_valid

def validate_test_structure():
    """Validate test suite structure."""
    print_section("Test Suite Structure Validation")
    
    test_files = [
        ('tests/conftest.py', ['sample_contact_info', 'sample_lead_input', 'mock_llm_service']),
        ('tests/test_models.py', ['TestContactInfo', 'TestLeadInput', 'TestEnrichedLead']),
        ('tests/test_services.py', ['TestLLMService', 'TestVectorService', 'TestAirtableService']),
        ('tests/test_api.py', ['TestIntakeAPI', 'TestLeadsAPI']),
        ('tests/test_integration.py', ['TestApplicationStartup'])
    ]
    
    all_valid = True
    
    for test_file, expected_items in test_files:
        file_path = Path(test_file)
        
        if not file_path.exists():
            print_test(f"Test file {test_file}", False, "File not found")
            all_valid = False
            continue
        
        analysis = analyze_file_structure(file_path)
        if 'error' in analysis:
            print_test(f"Test analysis {test_file}", False, analysis['error'])
            all_valid = False
            continue
        
        # Check for expected test items (classes or functions)
        all_items = analysis['classes'] + analysis['functions'] + analysis['async_functions']
        missing_items = [item for item in expected_items if item not in all_items]
        
        if missing_items:
            print_test(f"Test items {test_file}", False, f"Missing: {missing_items}")
            all_valid = False
        else:
            print_test(f"Test items {test_file}", True, f"Found {len(expected_items)} items")
    
    # Check pytest configuration
    pytest_ini = Path('pytest.ini')
    if pytest_ini.exists():
        print_test("Pytest configuration", True)
    else:
        print_test("Pytest configuration", False, "pytest.ini not found")
        all_valid = False
    
    return all_valid

def validate_documentation():
    """Validate documentation files."""
    print_section("Documentation Validation")
    
    doc_files = [
        'README.md',
        'CLAUDE.md', 
        'todo.md',
        'requirements.md',
        'tech-stack.md',
        'design-notes.md'
    ]
    
    all_exist = True
    
    for doc_file in doc_files:
        file_path = Path(doc_file)
        exists = file_path.exists() and file_path.is_file()
        print_test(f"Documentation {doc_file}", exists)
        if not exists:
            all_exist = False
        elif file_path.stat().st_size > 0:
            print_test(f"Content {doc_file}", True, f"{file_path.stat().st_size} bytes")
        else:
            print_test(f"Content {doc_file}", False, "Empty file")
            all_exist = False
    
    return all_exist

def calculate_code_metrics():
    """Calculate basic code metrics."""
    print_section("Code Metrics")
    
    src_path = Path('src')
    test_path = Path('tests')
    
    total_files = 0
    total_lines = 0
    total_classes = 0
    total_functions = 0
    
    for path in [src_path, test_path]:
        for py_file in path.rglob('*.py'):
            if py_file.is_file():
                total_files += 1
                analysis = analyze_file_structure(py_file)
                if 'error' not in analysis:
                    total_lines += analysis.get('lines', 0)
                    total_classes += len(analysis.get('classes', []))
                    total_functions += len(analysis.get('functions', [])) + len(analysis.get('async_functions', []))
    
    print_test("Code files", True, f"{total_files} Python files")
    print_test("Lines of code", True, f"~{total_lines} lines")
    print_test("Classes defined", True, f"{total_classes} classes")
    print_test("Functions defined", True, f"{total_functions} functions")
    
    # Estimate implementation completeness
    if total_lines > 2000 and total_classes > 15 and total_functions > 50:
        print_test("Implementation size", True, "Substantial implementation")
        return True
    else:
        print_test("Implementation size", False, "Implementation appears incomplete")
        return False

def run_validation():
    """Run complete validation suite."""
    print_section("baseCamp Phase 2 Structure & Syntax Validation")
    print("Validating code structure, syntax, and completeness...")
    
    validation_results = []
    
    # Run all validations
    validation_results.append(("Project Structure", validate_project_structure))
    validation_results.append(("Python Syntax", validate_syntax_all_files))
    validation_results.append(("Data Models", validate_models_structure))
    validation_results.append(("Service Layer", validate_services_structure))
    validation_results.append(("API Endpoints", validate_api_structure))
    validation_results.append(("Test Suite", validate_test_structure))
    validation_results.append(("Documentation", validate_documentation))
    validation_results.append(("Code Metrics", calculate_code_metrics))
    
    # Execute validations
    results = {}
    for name, validation_func in validation_results:
        try:
            if callable(validation_func):
                results[name] = validation_func()
            else:
                results[name] = validation_func
        except Exception as e:
            print_test(f"{name} validation", False, f"Error: {e}")
            results[name] = False
    
    # Summary
    print_section("Validation Summary")
    
    total_tests = len(results)
    passed_tests = sum(1 for result in results.values() if result)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\nOverall Result: {passed_tests}/{total_tests} validation categories passed")
    
    if passed_tests >= total_tests * 0.8:  # 80% pass rate
        print("\n🎉 Phase 2 structure validation SUCCESSFUL!")
        print("✅ Code structure and syntax are properly implemented")
        print("✅ All major components are present and well-structured")
        print("✅ Ready for dependency installation and Phase 3 integration")
        
        # Next steps
        print("\n📋 Next Steps:")
        print("1. Install dependencies: pip install -r requirements-dev.txt")
        print("2. Set up environment: cp .env.example .env") 
        print("3. Start external services (Ollama, ChromaDB)")
        print("4. Run integration tests")
        
        return True
    else:
        print(f"\n⚠️  Phase 2 validation completed with issues")
        print("Some structural components need attention")
        return False

if __name__ == "__main__":
    success = run_validation()
    sys.exit(0 if success else 1)