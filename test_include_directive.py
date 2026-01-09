#!/usr/bin/env python3
"""测试 nginx.conf 是否使用正确的 include 指令"""

import sys
from pathlib import Path
from views.takeover_dialog import NginxTakeoverDialog

def test_include_directive():
    """测试 include 指令是否使用随机数"""
    
    print("\n" + "="*60)
    print("测试: nginx.conf include 指令")
    print("="*60 + "\n")
    
    # 创建接管对话框实例（用于测试）
    dialog = NginxTakeoverDialog()
    
    # 测试不同的随机数
    test_cases = [
        "69UQ3",  # 你的例子
        "J43R8",  # 文档例子
        "1Z6VT",  # 测试例子
    ]
    
    for random_id in test_cases:
        print(f"测试随机数: {random_id}")
        config = dialog._generate_full_optimized_config(random_id)
        
        # 检查是否包含正确的 include 指令
        expected_include = f"include {random_id}_conf.d/*.conf;"
        
        if expected_include in config:
            print(f"  [OK] 包含正确的 include 指令: {expected_include}")
        else:
            print(f"  [FAIL] 缺少正确的 include 指令")
            print(f"  期望: {expected_include}")
            print(f"  实际配置中的 include 行:")
            for i, line in enumerate(config.split('\n')):
                if 'include' in line and 'conf.d' in line:
                    print(f"    第{i+1}行: {line.strip()}")
            return False
        
        # 检查是否包含错误的指令
        wrong_include = "include conf.d/*.conf;"
        if wrong_include in config:
            print(f"  [FAIL] 仍然包含旧的 include 指令: {wrong_include}")
            return False
        else:
            print(f"  [OK] 已移除旧的 include 指令")
        
        print()
    
    print("="*60)
    print("[OK] 所有测试通过！")
    print("="*60 + "\n")
    return True


if __name__ == "__main__":
    try:
        success = test_include_directive()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n[ERROR] 测试异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
