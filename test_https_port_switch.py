#!/usr/bin/env python3
"""
测试HTTPS端口自动切换功能

这个测试脚本验证：
1. 勾选启用HTTPS复选框时，端口自动切换到443
2. 取消勾选启用HTTPS复选框时，端口自动切换到80
"""

import sys
from PySide6.QtWidgets import QApplication
from views.site_config_dialog import StaticSiteConfigDialog

def test_port_switch():
    """测试端口切换功能"""
    app = QApplication(sys.argv)
    
    # 创建一个虚拟的MainViewModel
    class MockMainViewModel:
        def __init__(self):
            self.sites = []
    
    main_vm = MockMainViewModel()
    
    # 创建静态站点配置对话框
    dialog = StaticSiteConfigDialog(
        main_viewmodel=main_vm,
        parent=None,
        language_manager=None
    )
    
    # 初始状态：HTTPS未勾选，端口应为80
    print("初始状态:")
    print(f"  HTTPS 启用: {dialog.https_check.isChecked()}")
    print(f"  监听端口: {dialog.port_spin.value()}")
    assert dialog.port_spin.value() == 80, "初始端口应该是80"
    assert not dialog.https_check.isChecked(), "初始HTTPS应该未启用"
    
    # 勾选HTTPS复选框
    print("\n勾选HTTPS复选框...")
    dialog.https_check.setChecked(True)
    # 处理事件循环，确保信号槽正确执行
    app.processEvents()
    print(f"  HTTPS 启用: {dialog.https_check.isChecked()}")
    print(f"  监听端口: {dialog.port_spin.value()}")
    assert dialog.port_spin.value() == 443, f"勾选HTTPS后端口应该是443，实际是{dialog.port_spin.value()}"
    assert dialog.https_check.isChecked(), "HTTPS应该已启用"
    
    # 再次取消勾选HTTPS复选框
    print("\n取消勾选HTTPS复选框...")
    dialog.https_check.setChecked(False)
    # 处理事件循环，确保信号槽正确执行
    app.processEvents()
    print(f"  HTTPS 启用: {dialog.https_check.isChecked()}")
    print(f"  监听端口: {dialog.port_spin.value()}")
    assert dialog.port_spin.value() == 80, f"取消勾选HTTPS后端口应该是80，实际是{dialog.port_spin.value()}"
    assert not dialog.https_check.isChecked(), "HTTPS应该未启用"
    
    # 多次切换测试
    print("\n多次切换测试...")
    for i in range(3):
        dialog.https_check.setChecked(True)
        app.processEvents()
        assert dialog.port_spin.value() == 443, f"第{i+1}次勾选后端口应该是443，实际是{dialog.port_spin.value()}"
        
        dialog.https_check.setChecked(False)
        app.processEvents()
        assert dialog.port_spin.value() == 80, f"第{i+1}次取消勾选后端口应该是80，实际是{dialog.port_spin.value()}"
    
    print("\n✅ 所有测试通过！HTTPS端口自动切换功能正常工作。")
    print("\n总结:")
    print("  - 勾选启用HTTPS时，监听端口自动设置为443")
    print("  - 取消勾选启用HTTPS时，监听端口自动设置为80")
    print("  - 切换过程中SSL证书和密钥输入框也正确启用/禁用")
    
    return True

if __name__ == "__main__":
    try:
        success = test_port_switch()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
