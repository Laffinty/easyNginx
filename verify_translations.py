#!/usr/bin/env python3
"""
验证翻译文件完整性的简单脚本
"""

import json
from pathlib import Path

def verify_translations():
    """验证翻译文件."""
    translation_dir = Path("translations")
    
    # 需要检查的关键翻译键
    required_keys = [
        "about_title",
        "about_content",
        "static_site_config",
        "php_site_config",
        "proxy_site_config",
        "preview_title",
        "update_preview",
        "copy_config",
        "preview_config",
        "preview_tooltip",
        "invalid_config",
        "config_error",
        "select_ssl_cert",
        "cert_filter",
        "select_ssl_key",
        "key_filter",
        "select_root_dir",
        "website_settings",
        "websocket_tooltip"
    ]
    
    print("验证翻译文件...")
    
    for lang_file in translation_dir.glob("*.json"):
        print(f"\n检查 {lang_file.name}:")
        try:
            with open(lang_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            missing_keys = []
            for key in required_keys:
                if key not in data:
                    missing_keys.append(key)
            
            if missing_keys:
                print(f"  [X] 缺少以下键: {', '.join(missing_keys)}")
            else:
                print(f"  [OK] 所有必需的键都存在")
                
            # 检查about_content是否已简化
            about_content = data.get("about_content", "")
            if "主要功能" in about_content or "Key Features" in about_content:
                print(f"  [WARN] about_content 仍包含功能介绍，需要简化")
            elif "Copyright" in about_content or "许可证" in about_content:
                print(f"  [OK] about_content 已正确简化")
            
        except Exception as e:
            print(f"  [ERROR] 读取文件时出错: {e}")

if __name__ == "__main__":
    verify_translations()
