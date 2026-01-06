#!/usr/bin/env python3
"""
测试对话框标题的多语言支持
"""

import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from utils.language_manager import LanguageManager

def test_dialog_titles():
    """测试不同语言下的对话框标题"""
    app = QApplication(sys.argv)
    
    language_manager = LanguageManager()
    
    # 测试所有支持的语言
    languages = ["en", "zh_CN", "zh_TW", "ja", "ko"]
    
    print("测试新建站点对话框标题的多语言支持:\n")
    print("=" * 70)
    
    for lang in languages:
        language_manager.set_language(lang)
        lang_name = language_manager.get_language_name(lang)
        
        print(f"\n语言: {lang_name} ({lang})")
        print("-" * 50)
        
        # 获取各种标题
        file_menu = language_manager.get("file_menu")
        new_static = language_manager.get("new_static")
        new_php = language_manager.get("new_php")
        new_proxy = language_manager.get("new_proxy")
        
        basic_config = language_manager.get("basic_config")
        static_settings = language_manager.get("static_settings")
        php_settings = language_manager.get("php_settings")
        proxy_settings = language_manager.get("proxy_settings")
        
        websocket_support = language_manager.get("websocket_support")
        websocket_tooltip = language_manager.get("websocket_tooltip")
        
        print(f"文件菜单: {file_menu}")
        print(f"  └─ 新建静态: {new_static}")
        print(f"  └─ 新建PHP: {new_php}")
        print(f"  └─ 新建代理: {new_proxy}")
        print()
        print(f"对话框内部标题:")
        print(f"  └─ 基础配置: {basic_config}")
        print(f"  └─ 静态设置: {static_settings}")
        print(f"  └─ PHP设置: {php_settings}")
        print(f"  └─ 代理设置: {proxy_settings}")
        print()
        print(f"WebSocket选项:")
        print(f"  └─ 文本: {websocket_support}")
        print(f"  └─ 提示: {websocket_tooltip}")
    
    print("\n" + "=" * 70)
    print("\n测试要点:")
    print("1. 菜单项和对话框标题是否保持一致")
    print("2. 所有文本是否正确翻译")
    print("3. 特殊字符是否正确显示")

if __name__ == "__main__":
    test_dialog_titles()
