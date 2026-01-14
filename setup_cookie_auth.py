#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
设置Cookie认证的工具
"""

import json
import sys

def setup_cookie():
    """设置Cookie认证"""
    print("=" * 60)
    print("Cookie认证设置指南")
    print("=" * 60)
    print("\n请按照以下步骤操作：\n")
    print("1. 打开浏览器，访问 https://www.cgmcc.net")
    print("2. 手动登录网站（输入账号密码）")
    print("3. 按F12打开开发者工具")
    print("4. 切换到 Application/Storage 标签（Chrome）或 Storage 标签（Firefox）")
    print("5. 在左侧选择 Cookies -> https://www.cgmcc.net")
    print("6. 复制所有cookie值\n")
    
    print("或者：\n")
    print("1. 登录后，在Network标签中找到登录请求")
    print("2. 查看请求的Headers")
    print("3. 找到Cookie字段，复制整个值\n")
    
    print("请选择方式：")
    print("1. 手动输入cookie字符串")
    print("2. 输入登录请求的实际URL（我会尝试自动登录）")
    
    choice = input("\n请输入选择（1或2，直接回车跳过）: ").strip()
    
    if choice == "1":
        cookie_str = input("请输入cookie字符串: ").strip()
        if cookie_str:
            # 解析cookie字符串
            cookies = {}
            for item in cookie_str.split(';'):
                if '=' in item:
                    key, value = item.strip().split('=', 1)
                    cookies[key] = value
            
            # 保存到配置文件
            try:
                with open('config.json', 'r', encoding='utf-8') as f:
                    config = json.load(f)
            except:
                config = {}
            
            config['cookies'] = cookies
            
            with open('config.json', 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            print(f"\n✓ Cookie已保存到config.json")
            print("现在可以运行: python cgmcc_downloader.py")
    
    elif choice == "2":
        login_url = input("请输入登录请求的实际URL: ").strip()
        if login_url:
            try:
                with open('config.json', 'r', encoding='utf-8') as f:
                    config = json.load(f)
            except:
                config = {}
            
            config['api_login_url'] = login_url.replace('https://www.cgmcc.net', '')
            
            with open('config.json', 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            print(f"\n✓ 登录URL已更新到config.json")
            print("现在可以运行: python cgmcc_downloader.py")
    else:
        print("\n未进行任何操作")

if __name__ == '__main__':
    try:
        setup_cookie()
    except KeyboardInterrupt:
        print("\n\n操作已取消")
    except Exception as e:
        print(f"\n错误: {e}")
