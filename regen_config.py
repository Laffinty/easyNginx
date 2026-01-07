#!/usr/bin/env python3
# Regenerate nginx.conf

import sys
sys.path.append('.')

from viewmodels.main_viewmodel import MainViewModel
from pathlib import Path

# Create viewmodel
vm = MainViewModel(
    nginx_path="C:/Users/ikrx2/Desktop/nginx-1.29.4/nginx.exe",
    config_path="C:/Users/ikrx2/Desktop/nginx-1.29.4/conf/nginx.conf"
)

# Load sites
vm.load_sites()
print(f"Found {len(vm.sites)} sites")

# Generate and save config
if vm.sites:
    print("Regenerating config...")
    config_content = vm._build_full_config()
    
    config_path = Path(vm.nginx_service.config_path)
    config_path.write_text(config_content, encoding='utf-8')
    
    print("Config regenerated successfully!")
    print(f"Config saved to: {config_path}")
else:
    print("No sites found. Creating minimal config...")
    minimal_config = """# Nginx Global Configuration
worker_processes auto;
error_log logs/error.log warn;

events {
    worker_connections 1024;
    use select;
}

http {
    include       mime.types;
    default_type  application/octet-stream;
}
"""
    config_path = Path(vm.nginx_service.config_path)
    config_path.write_text(minimal_config, encoding='utf-8')
    print("Minimal config created!")

# Test config
try:
    is_valid, message = vm.nginx_service.test_config()
    if is_valid:
        print("Config test PASSED")
    else:
        print(f"Config test FAILED: {message}")
except Exception as e:
    print(f"Test error: {e}")
