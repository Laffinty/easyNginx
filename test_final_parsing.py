#!/usr/bin/env python3
"""Test final parsing with debug."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from services.config_parser import ConfigParser
from loguru import logger

def test_parsing():
    parser = ConfigParser()
    config_file = Path("C:/Users/ikrx2/Desktop/nginx-1.29.4/conf/14ZUS_conf.d/testsite1.conf")
    
    print("=" * 70)
    print("TESTING FINAL PARSING WITH DEBUG")
    print("=" * 70)
    
    sites = parser.parse_config_file(config_file, None)
    
    if sites:
        site = sites[0]
        print(f"\nParsed site:")
        print(f"  site_name: {site.site_name}")
        print(f"  listen_port: {site.listen_port}")
        print(f"  server_name: {site.server_name}")
        print(f"  site_type: {site.site_type}")
        
        if hasattr(site, 'root_path'):
            print(f"  root_path: {site.root_path}")
        else:
            print(f"  root_path: MISSING")
            
        if hasattr(site, 'index_file'):
            print(f"  index_file: {site.index_file}")
        else:
            print(f"  index_file: MISSING")
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    test_parsing()
