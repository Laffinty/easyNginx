#!/usr/bin/env python3
"""
直接测试_on_https_toggled方法
"""

import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from views.site_config_dialog import StaticSiteConfigDialog

def test_toggled_method():
    """直接测试_toggled方法"""
    app = QApplication(sys.argv)
    
    class MockMainViewModel:
        def __init__(self):
            self.sites = []
    
    main_vm = MockMainViewModel()
    dialog = StaticSiteConfigDialog(main_viewmodel=main_vm)
    
    print("初始状态:")
    print(f"  HTTPS 启用: {dialog.https_check.isChecked()}")
    print(f"  监听端口: {dialog.port_spin.value()}")
    
    # 手动调用_on_https_toggled方法
    print("\n调用_on_https_toggled(Qt.Checked)...")
    dialog._on_https_toggled(Qt.Checked)
    print(f"  HTTPS 启用: {dialog.https_check.isChecked()}")
    print(f"  监听端口: {dialog.port_spin.value()}")
    
    if dialog.port_spin.value() == 443:
        print("\n✓ 端口正确切换到443")
    else:
        print(f"\n✗ 端口切换失败，期望443，实际为{dialog.port_spin.value()}")
        return False
    
    print("\n调用_on_https_toggled(Qt.Unchecked)...")
    dialog._on_https_toggled(Qt.Unchecked)
    print(f"  HTTPS 启用: {dialog.https_check.isChecked()}")
    print(f"  监听端口: {dialog.port_spin.value()}")
    
    if dialog.port_spin.value() == 80:
        print("\n✓ 端口正确切换到80")
    else:
        print(f"\n✗ 端口切换失败，期望80，实际为{dialog.port_spin.value()}")
        return False
    
    print("\n✓ 所有测试通过！_on_https_toggled方法工作正常。")
    return True

if __name__ == "__main__":
    success = test_toggled_method()
    sys.exit(0 if success else 1)
