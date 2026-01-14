#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
详细测试CGMCC登录，尝试不同的字段名
"""

import requests
import json

def test_login_variations():
    """测试不同的登录格式"""
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
        username = config.get('username', '')
        password = config.get('password', '')
    
    base_url = "https://www.cgmcc.net"
    login_url = f"{base_url}/cgmccapi/restrict/user/login"
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Origin': base_url,
        'Referer': f'{base_url}/login',
    })
    
    # 先访问登录页面，获取JSESSIONID
    print("=" * 60)
    print("测试CGMCC登录（详细）")
    print("=" * 60)
    print("\n[步骤1] 访问登录页面获取session...")
    try:
        response = session.get(f"{base_url}/login", timeout=10)
        print(f"状态码: {response.status_code}")
        print(f"Cookies: {dict(session.cookies)}")
    except Exception as e:
        print(f"错误: {e}")
    
    # 尝试不同的字段名组合
    test_cases = [
        {'username': username, 'password': password},
        {'user': username, 'pass': password},
        {'account': username, 'password': password},
        {'loginName': username, 'password': password},
        {'name': username, 'password': password},
    ]
    
    print("\n[步骤2] 尝试不同的字段名...")
    for i, test_data in enumerate(test_cases, 1):
        print(f"\n[测试 {i}] 字段: {list(test_data.keys())}")
        try:
            response = session.post(
                login_url,
                data=test_data,
                files=[],  # 触发multipart编码
                timeout=30
            )
            
            print(f"  状态码: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"  响应: {json.dumps(data, ensure_ascii=False)}")
                    
                    if data.get('status') == 0 or data.get('msg') == '成功':
                        print(f"  ✓ 登录成功！")
                        print(f"  Cookies: {dict(session.cookies)}")
                        return True, session.cookies, test_data
                    elif 'NullPointerException' in str(data.get('msg', '')):
                        print(f"  ✗ 服务器错误（可能是字段名不对）")
                    else:
                        print(f"  ✗ 登录失败: {data.get('msg', '未知错误')}")
                except:
                    print(f"  响应文本: {response.text[:200]}")
        except Exception as e:
            print(f"  错误: {e}")
    
    print("\n" + "=" * 60)
    print("所有测试都失败了")
    print("=" * 60)
    print("\n提示：")
    print("1. 请检查浏览器Network标签中登录请求的Payload部分")
    print("2. 查看实际的字段名是什么")
    print("3. 或者查看是否有其他必需的参数")
    
    return False, None, None

if __name__ == '__main__':
    success, cookies, data = test_login_variations()
    if success:
        print(f"\n✓ 成功的字段组合: {data}")
        print("请更新脚本使用这些字段名")
