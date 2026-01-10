#!/usr/bin/env python3
"""Test root context."""

import re
from pathlib import Path
from utils.encoding_utils import read_file_robust

config_file = Path("C:/Users/ikrx2/Desktop/nginx-1.29.4/conf/14ZUS_conf.d/testsite1.conf")
content = read_file_robust(config_file)

# Extract server content manually
import re
server_blocks = []
pos = 0

while pos < len(content):
    server_pos = content.find('server', pos)
    if server_pos == -1:
        break
    
    bracket_pos = content.find('{', server_pos)
    if bracket_pos != -1:
        depth = 1
        search_pos = bracket_pos + 1
        while search_pos < len(content) and depth > 0:
            if content[search_pos] == '{':
                depth += 1
            elif content[search_pos] == '}':
                depth -= 1
            search_pos += 1
        
        if depth == 0:
            block = content[server_pos:search_pos]
            server_blocks.append(block)
            pos = search_pos
            continue
    
    pos = server_pos + 6

if not server_blocks:
    print("No server blocks found")
    exit(1)

server_block = server_blocks[0]
first_brace = server_block.find('{')
last_brace = server_block.rfind('}')
server_content = server_block[first_brace+1:last_brace]

# Find root and show raw bytes around it
root_pos = server_content.find('root')
print("=" * 70)
print("ROOT CONTEXT - RAW BYTES")
print("=" * 70)

if root_pos != -1:
    # Show 20 chars before and after root
    start = max(0, root_pos - 20)
    end = min(len(server_content), root_pos + 50)
    context = server_content[start:end]
    
    print("Text context:")
    print(repr(context))
    print()
    
    print("Hex dump:")
    for i, c in enumerate(context):
        print(f"{ord(c):02x} ", end="")
        if (i + 1) % 16 == 0:
            print()
    print()
    
    # Show character by character around root
    print("Character by character:")
    for i, c in enumerate(context):
        pos = start + i
        marker = " <-- root starts here" if pos == root_pos else ""
        print(f"Pos {pos:4}: {repr(c):8} ({ord(c):3}){marker}")

# Test the directive pattern on this specific context
print("\n" + "=" * 70)
print("TESTING DIRECTIVE PATTERN")
print("=" * 70)

# Just test the root line
lines = context.split('\n')
for line in lines:
    if 'root' in line:
        print(f"Testing line: {repr(line)}")
        
        pattern = re.compile(
            r'(\w+)\s+(.+?)(?=\s*;|\s*\{)',
            re.MULTILINE | re.DOTALL
        )
        
        match = pattern.search(line)
        if match:
            print(f"  MATCH: key='{match.group(1)}', value='{match.group(2)}'")
        else:
            print("  NO MATCH")
            
            # Try without lookahead
            pattern2 = re.compile(r'(\w+)\s+([^;]+);')
            match2 = pattern2.search(line)
            if match2:
                print(f"  Pattern 2 MATCH: key='{match2.group(1)}', value='{match2.group(2).strip()}'")
