#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从浏览器中提取token的工具脚本
"""

import json
import sys

def extract_from_browser():
    """指导用户从浏览器中提取token"""
    print("=" * 60)
    print("从浏览器提取Token指南")
    print("=" * 60)
    print("\n请按照以下步骤操作：\n")
    print("1. 打开浏览器，访问 https://www.cgmcc.net")
    print("2. 按F12打开开发者工具")
    print("3. 切换到 Network（网络）标签")
    print("4. 手动登录网站（点击Login按钮，输入账号密码）")
    print("5. 在Network标签中查找登录相关的请求")
    print("6. 查看响应（Response）或请求头（Headers）中的token\n")
    
    print("或者：\n")
    print("1. 登录后，切换到 Application/Storage 标签")
    print("2. 查看 Local Storage 或 Session Storage")
    print("3. 查找包含token的键值对\n")
    
    token = input("请输入你找到的token（直接回车跳过）: ").strip()
    
    if token:
        # 保存到配置文件
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
        except:
            config = {}
        
        config['token'] = token
        
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ Token已保存到config.json")
        print("现在可以运行: python cgmcc_downloader.py")
    else:
        print("\n未输入token，跳过保存")

if __name__ == '__main__':
    extract_from_browser()
