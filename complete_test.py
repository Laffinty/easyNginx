#!/usr/bin/env python3
"""Complete test of site loading."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

def test_site_loading():
    """Test site loading with all fixes."""
    
    # Test file
    config_file = Path("C:/Users/ikrx2/Desktop/nginx-1.29.4/conf/14ZUS_conf.d/testsite1.conf")
    
    print("=" * 80)
    print("COMPLETE SITE LOADING TEST")
    print("=" * 80)
    print(f"Config file: {config_file}")
    print(f"File exists: {config_file.exists()}")
    print()
    
    if not config_file.exists():
        print("File not found!")
        return False
    
    # Read config content
    from utils.encoding_utils import read_file_robust
    content = read_file_robust(config_file)
    
    print("Config Content Analysis:")
    print("-" * 80)
    
    # Check for key directives
    import re
    
    listen_match = re.search(r'listen\s+([^;]+);', content)
    if listen_match:
        print(f"✓ Listen found: {listen_match.group(1).strip()}")
    else:
        print("✗ Listen NOT found")
    
    server_name_match = re.search(r'server_name\s+([^;]+);', content)
    if server_name_match:
        print(f"✓ Server_name found: {server_name_match.group(1).strip()}")
    else:
        print("✗ Server_name NOT found")
    
    root_match = re.search(r'(^|\s+)root\s+([^;]+);', content, re.MULTILINE)
    if root_match:
        print(f"✓ Root found: {root_match.group(2).strip()}")
    else:
        print("✗ Root NOT found")
    
    index_match = re.search(r'(^|\s+)index\s+([^;]+);', content, re.MULTILINE)
    if index_match:
        print(f"✓ Index found: {index_match.group(2).strip()}")
    else:
        print("✗ Index NOT found")
    
    print()
    print("=" * 80)
    print("PARSED SITE DETAILS")
    print("=" * 80)
    
    # Parse the config
    from services.config_parser import ConfigParser
    parser = ConfigParser()
    sites = parser.parse_config_content(content, source_filename=config_file.name)
    
    if not sites:
        print("No sites parsed!")
        return False
    
    site = sites[0]
    print(f"Site name:     {site.site_name}")
    print(f"Listen port:   {site.listen_port}")
    print(f"Server name:   {site.server_name}")
    print(f"Type:          {site.site_type}")
    
    if hasattr(site, 'root_path'):
        print(f"Root path:     {site.root_path}")
    else:
        print("Root path:     MISSING ATTRIBUTE")
    
    if hasattr(site, 'index_file'):
        print(f"Index file:    {site.index_file}")
    else:
        print("Index file:    MISSING ATTRIBUTE")
    
    print()
    print("=" * 80)
    print("VALIDATION")
    print("=" * 80)
    
    expected = {
        'site_name': 'testsite1',
        'listen_port': 81,
        'server_name': 'localhost',
        'root_path': r'C:\Users\ikrx2\Desktop\1',
        'index_file': 'index.html'
    }
    
    results = {}
    
    # Check site_name
    results['site_name'] = site.site_name == expected['site_name']
    
    # Check listen_port
    results['listen_port'] = site.listen_port == expected['listen_port']
    
    # Check server_name
    results['server_name'] = site.server_name == expected['server_name']
    
    # Check root_path
    if hasattr(site, 'root_path'):
        results['root_path'] = site.root_path == expected['root_path']
    else:
        results['root_path'] = False
    
    # Check index_file
    if hasattr(site, 'index_file'):
        results['index_file'] = site.index_file == expected['index_file']
    else:
        results['index_file'] = False
    
    all_passed = all(results.values())
    
    for field, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status:8} | {field:15} | Expected: {str(expected[field]):25} | Got: {str(getattr(site, field, 'MISSING')):25}")
    
    print()
    print("=" * 80)
    if all_passed:
        print("ALL TESTS PASSED!")
    else:
        print("SOME TESTS FAILED!")
        print()
        print("Failed fields:", ", ".join([k for k, v in results.items() if not v]))
    print("=" * 80)
    
    return all_passed

if __name__ == "__main__":
    success = test_site_loading()
    sys.exit(0 if success else 1)
