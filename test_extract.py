#!/usr/bin/env python3
"""Test extract_site_name_from_filename directly."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from services.config_parser import ConfigParser

parser = ConfigParser()

# Test the function
test_filename = "testsite1.conf"
result = parser._extract_site_name_from_filename(test_filename)

print(f"Input: {test_filename}")
print(f"Output: {result}")

# Expected: testsite1
if result == "testsite1":
    print("✓ SUCCESS")
else:
    print("✗ FAILED")
