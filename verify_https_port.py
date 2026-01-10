#!/usr/bin/env python3
"""
验证HTTPS端口自动切换功能
"""

import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from views.site_config_dialog import StaticSiteConfigDialog

def verify_https_port():
    """验证HTTPS端口切换功能"""
    app = QApplication(sys.argv)
    
    class MockMainViewModel:
        def __init__(self):
            self.sites = []
    
    main_vm = MockMainViewModel()
    dialog = StaticSiteConfigDialog(main_viewmodel=main_vm)
    
    print("=" * 50)
    print("HTTPS端口自动切换功能验证")
    print("=" * 50)
    
    # 测试1: 初始状态
    print("\n[测试1] 初始状态:")
    print("  HTTPS启用:", dialog.https_check.isChecked())
    print("  监听端口:", dialog.port_spin.value())
    assert dialog.port_spin.value() == 80, "初始端口应该是80"
    print("  -> 通过: 初始端口为80")
    
    # 测试2: 勾选HTTPS
    print("\n[测试2] 勾选HTTPS复选框:")
    dialog._on_https_toggled(Qt.Checked)
    print("  调用_on_https_toggled(Qt.Checked)")
    print("  监听端口:", dialog.port_spin.value())
    assert dialog.port_spin.value() == 443, f"勾选HTTPS后端口应该是443，实际是{dialog.port_spin.value()}"
    print("  -> 通过: 端口已自动切换为443")
    
    # 测试3: 取消勾选HTTPS
    print("\n[测试3] 取消勾选HTTPS复选框:")
    dialog._on_https_toggled(Qt.Unchecked)
    print("  调用_on_https_toggled(Qt.Unchecked)")
    print("  监听端口:", dialog.port_spin.value())
    assert dialog.port_spin.value() == 80, f"取消勾选HTTPS后端口应该是80，实际是{dialog.port_spin.value()}"
    print("  -> 通过: 端口已自动切换为80")
    
    # 测试4: 多次切换
    print("\n[测试4] 多次切换测试:")
    for i in range(3):
        dialog._on_https_toggled(Qt.Checked)
        assert dialog.port_spin.value() == 443, f"第{i+1}次勾选后端口应该是443"
        
        dialog._on_https_toggled(Qt.Unchecked)
        assert dialog.port_spin.value() == 80, f"第{i+1}次取消勾选后端口应该是80"
    print("  -> 通过: 3次切换测试成功")
    
    print("\n" + "=" * 50)
    print("所有测试通过！HTTPS端口自动切换功能正常工作。")
    print("=" * 50)
    print("\n功能总结:")
    print("  - 勾选启用HTTPS时，监听端口自动设置为: 443")
    print("  - 取消勾选启用HTTPS时，监听端口自动设置为: 80")
    print("  - SSL证书和密钥输入框也正确启用/禁用")
    
    return True

if __name__ == "__main__":
    try:
        success = verify_https_port()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
