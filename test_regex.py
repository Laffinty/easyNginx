#!/usr/bin/env python3
"""Test directive pattern on root."""

import re

# Test string
test_line = '    root "C:\\Users\\ikrx2\\Desktop\\1";'

print("Testing directive pattern on root line:")
print(f"Line: {test_line}")
print()

# Current pattern
pattern1 = re.compile(
    r'(\w+)\s+(.+?)(?=\s*;|\s*\{)',
    re.MULTILINE | re.DOTALL
)

match1 = pattern1.search(test_line)
if match1:
    print(f"Pattern 1 MATCH:")
    print(f"  Key: '{match1.group(1)}'")
    print(f"  Value: '{match1.group(2)}'")
else:
    print("Pattern 1: NO MATCH")

# Try a simpler pattern without lookahead
print()
print("Testing simpler pattern:")
pattern2 = re.compile(
    r'(\w+)\s+([^;]+?);',
    re.MULTILINE | re.DOTALL
)

match2 = pattern2.search(test_line)
if match2:
    print(f"Pattern 2 MATCH:")
    print(f"  Key: '{match2.group(1)}'")
    print(f"  Value: '{match2.group(2).strip()}'")
else:
    print("Pattern 2: NO MATCH")

# Try with updated pattern that handles more cases
print()
print("Testing improved pattern:")
pattern3 = re.compile(
    r'(^|\s+)(\w+)\s+(.+?)(?=\s*;|\s*\{|$)',
    re.MULTILINE | re.DOTALL
)

match3 = pattern3.search(test_line)
if match3:
    print(f"Pattern 3 MATCH:")
    print(f"  Key: '{match3.group(2)}'")
    print(f"  Value: '{match3.group(3).strip()}'")
else:
    print("Pattern 3: NO MATCH")
