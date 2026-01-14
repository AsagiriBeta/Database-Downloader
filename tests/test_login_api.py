#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试CGMCC登录API，查找实际的登录端点
"""

import requests
import json
from urllib.parse import urljoin

def test_login():
    """测试登录API"""
    base_url = "https://www.cgmcc.net"
    
    # 从配置文件读取账号密码
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
            username = config.get('username', '')
            password = config.get('password', '')
    except:
        print("无法读取配置文件")
        return
    
    if not username or not password:
        print("配置文件中没有用户名或密码")
        return
    
    print("=" * 60)
    print("测试CGMCC登录API")
    print("=" * 60)
    print(f"用户名: {username}")
    print()
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Referer': base_url,
        'Origin': base_url
    })
    
    # 根据用户提供的响应格式，尝试不同的登录端点
    login_endpoints = [
        "/api/user/login",
        "/api/login",
        "/api/auth/login",
        "/user/login",
        "/login",
    ]
    
    login_data = {
        "username": username,
        "password": password
    }
    
    for endpoint in login_endpoints:
        url = urljoin(base_url, endpoint)
        print(f"\n[测试] {endpoint}")
        print(f"URL: {url}")
        
        try:
            response = session.post(
                url,
                json=login_data,
                timeout=10,
                allow_redirects=False
            )
            
            print(f"状态码: {response.status_code}")
            print(f"响应头: {dict(response.headers)}")
            print(f"Cookies: {dict(session.cookies)}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"响应数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
                    
                    if data.get('status') == 0 or data.get('msg') == '成功':
                        print("✓ 登录成功！")
                        print(f"Cookies: {dict(session.cookies)}")
                        
                        # 检查是否有token
                        token = (
                            data.get('token') or
                            data.get('access_token') or
                            data.get('data', {}).get('token')
                        )
                        if token:
                            print(f"Token: {token}")
                        else:
                            print("使用Cookie认证")
                        
                        return endpoint, session.cookies
                except:
                    print(f"响应文本: {response.text[:200]}")
            
        except Exception as e:
            print(f"错误: {e}")
    
    print("\n" + "=" * 60)
    print("未找到成功的登录端点")
    print("=" * 60)
    return None, None

if __name__ == '__main__':
    endpoint, cookies = test_login()
    if endpoint:
        print(f"\n成功的登录端点: {endpoint}")
        print(f"请更新config.json中的api_login_url为: {endpoint}")
