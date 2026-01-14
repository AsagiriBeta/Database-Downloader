#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试实际的CGMCC登录API
"""

import requests
import json

def test_login():
    """测试登录"""
    # 从配置文件读取
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
        username = config.get('username', '')
        password = config.get('password', '')
    
    base_url = "https://www.cgmcc.net"
    login_url = f"{base_url}/cgmccapi/restrict/user/login"
    
    session = requests.Session()
    
    # 设置请求头（根据用户提供的实际请求头）
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36 Edg/143.0.0.0',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Origin': base_url,
        'Referer': f'{base_url}/login',
        'Connection': 'keep-alive',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
    })
    
    print("=" * 60)
    print("测试CGMCC登录API")
    print("=" * 60)
    print(f"登录URL: {login_url}")
    print(f"用户名: {username}")
    print()
    
    # 尝试multipart/form-data格式
    print("[测试1] multipart/form-data格式")
    try:
        # 使用files参数来触发multipart编码
        response = session.post(
            login_url,
            data={'username': username, 'password': password},
            files=[],  # 空列表触发multipart编码
            timeout=30
        )
        
        print(f"状态码: {response.status_code}")
        print(f"响应头: {dict(response.headers)}")
        print(f"Cookies: {dict(session.cookies)}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"响应数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
                
                if data.get('status') == 0 or data.get('msg') == '成功':
                    print("\n✓ 登录成功！")
                    print(f"Cookies: {dict(session.cookies)}")
                    return True, session.cookies
            except Exception as e:
                print(f"解析JSON失败: {e}")
                print(f"响应文本: {response.text[:500]}")
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
    
    # 尝试application/x-www-form-urlencoded格式
    print("\n[测试2] application/x-www-form-urlencoded格式")
    try:
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        response = session.post(
            login_url,
            data={'username': username, 'password': password},
            headers=headers,
            timeout=30
        )
        
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"响应数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
                if data.get('status') == 0:
                    print("\n✓ 登录成功！")
                    return True, session.cookies
            except:
                print(f"响应文本: {response.text[:500]}")
    except Exception as e:
        print(f"错误: {e}")
    
    print("\n" + "=" * 60)
    print("登录失败")
    print("=" * 60)
    return False, None

if __name__ == '__main__':
    success, cookies = test_login()
    if success and cookies:
        print(f"\n✓ 登录成功！Cookies已保存到session中")
        print("现在可以使用这个session进行后续请求")
