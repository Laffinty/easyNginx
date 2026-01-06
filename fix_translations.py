#!/usr/bin/env python3
"""
补充缺失的翻译键
"""

import json
from pathlib import Path

def load_json(file_path):
    """加载JSON文件"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(file_path, data):
    """保存JSON文件"""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def main():
    """主函数"""
    translation_dir = Path("translations")
    
    # 加载英文翻译作为参考
    en_data = load_json(translation_dir / "en.json")
    
    # 需要处理的语言文件
    languages = ["zh_TW.json", "ja.json", "ko.json"]
    
    for lang_file in languages:
        lang_path = translation_dir / lang_file
        lang_data = load_json(lang_path)
        
        # 找出缺失的键
        missing_keys = []
        for key in en_data.keys():
            if key not in lang_data:
                missing_keys.append(key)
        
        if missing_keys:
            print(f"\n{lang_file} 缺少 {len(missing_keys)} 个键:")
            for key in missing_keys:
                print(f"  - {key}")
                # 将英文翻译添加到缺失的语言文件中
                lang_data[key] = en_data[key]
            
            # 保存更新后的文件
            save_json(lang_path, lang_data)
            print(f"  已补充缺失的键到 {lang_file}")
        else:
            print(f"\n{lang_file}: 所有键都已存在")

if __name__ == "__main__":
    main()
