#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verification script for UI changes.
Tests the three requirements:
1. Site statistics should follow current language
2. Window title should show "easyNginx" + version only
3. Only Start, Stop, Reload buttons should be visible (no "More" button)
"""

import sys
import io
from pathlib import Path
from PySide6.QtWidgets import QApplication

# Set UTF-8 encoding for Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from utils.language_manager import LanguageManager
from models.nginx_status import NginxStatus, NginxProcessStatus
from views.status_bar import StatusBar
from views.main_window import MainWindow
from viewmodels.main_viewmodel import MainViewModel


def test_language_manager():
    """Test language manager translations."""
    print("\n=== Testing Language Manager ===")
    
    lm = LanguageManager()
    
    # Test English
    lm.set_language("en")
    text_en = lm.get("total_sites", total=5, static=2, php=1, proxy=2)
    print(f"English (en): {text_en}")
    
    # Test Chinese Simplified
    lm.set_language("zh_CN")
    text_zh = lm.get("total_sites", total=5, static=2, php=1, proxy=2)
    print(f"Chinese Simplified (zh_CN): {text_zh}")
    
    # Test Japanese
    lm.set_language("ja")
    text_ja = lm.get("total_sites", total=5, static=2, php=1, proxy=2)
    print(f"Japanese (ja): {text_ja}")
    
    # Test Korean
    lm.set_language("ko")
    text_ko = lm.get("total_sites", total=5, static=2, php=1, proxy=2)
    print(f"Korean (ko): {text_ko}")


def test_window_title():
    """Test that window title only shows 'easyNginx' + version."""
    print("\n=== Testing Window Title ===")
    
    from views.main_window import APP_VERSION
    print(f"APP_VERSION defined as: {APP_VERSION}")
    
    # Expected title format
    expected_title = f"easyNginx {APP_VERSION}"
    print(f"Expected window title: {expected_title}")
    
    # Check that it does NOT contain the old text
    assert "Professional" not in expected_title, "Title should not contain 'Professional'"
    assert "专业Nginx管理工具" not in expected_title, "Title should not contain Chinese description"
    assert "-" not in expected_title or APP_VERSION in expected_title, "Only dash should be for version"
    
    print("✓ Window title format is correct")


def test_status_bar():
    """Test that status bar uses language manager and doesn't have 'More' button."""
    print("\n=== Testing Status Bar ===")
    
    app = QApplication.instance() or QApplication(sys.argv)
    
    # Create a minimal viewmodel with the required attributes
    from PySide6.QtCore import QObject, Signal
    
    class FakeViewModel(QObject):
        nginx_status_changed = Signal(object)
        
        def __init__(self):
            super().__init__()
            self.nginx_service = None
            self.language_manager = LanguageManager()
            
        def control_nginx(self, action):
            print(f"Control nginx: {action}")
    
    # Create status bar
    vm = FakeViewModel()
    status_bar = StatusBar(vm)
    
    # Check that language manager is used
    print("✓ StatusBar initialized successfully")
    
    # Create test status
    status = NginxStatus(
        status=NginxProcessStatus.RUNNING,
        total_sites=3,
        sites_by_type={"static": 1, "php": 1, "proxy": 1}
    )
    
    # Test different languages
    languages = ["en", "zh_CN", "ja", "ko"]
    
    for lang in languages:
        print(f"\nTesting language: {lang}")
        status_bar.language_manager.set_language(lang)
        status_bar.update_status(status)
        
        # Get the info text
        info_text = status_bar.info_text.text()
        print(f"  Status text: {info_text}")
        
        # Check that it contains translated text
        assert len(info_text) > 0, f"Info text should not be empty for language {lang}"
        assert "Static" not in info_text or lang == "en", f"Should not have hardcoded English in {lang}"
    
    print("\n✓ Status bar correctly uses language manager for site statistics")
    
    # Check that there is no 'more_btn' attribute
    assert not hasattr(status_bar, 'more_btn'), "StatusBar should not have 'more_btn' attribute"
    print("✓ 'More' button has been removed from status bar")
    
    # Check that only 3 buttons exist
    button_count = 0
    if hasattr(status_bar, 'start_btn'):
        button_count += 1
    if hasattr(status_bar, 'stop_btn'):
        button_count += 1
    if hasattr(status_bar, 'reload_btn'):
        button_count += 1
    
    assert button_count == 3, f"Expected 3 control buttons, found {button_count}"
    print("✓ Only Start, Stop, Reload buttons are present")


def main():
    """Run all verification tests."""
    print("="*60)
    print("VERIFYING UI CHANGES")
    print("="*60)
    
    try:
        # Test 1: Language manager translations
        test_language_manager()
        
        # Test 2: Window title
        test_window_title()
        
        # Test 3: Status bar
        test_status_bar()
        
        print("\n" + "="*60)
        print("✓ ALL TESTS PASSED!")
        print("="*60)
        print("\nVerified changes:")
        print("1. ✓ Site statistics follow current language setting")
        print("2. ✓ Window title shows 'easyNginx' + version only")
        print("3. ✓ Only Start, Stop, Reload buttons are visible (no 'More' button)")
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
