#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试CGMCC登录API
"""

import requests
import json
from urllib.parse import urljoin

def test_login_endpoints():
    """测试不同的登录端点"""
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
    print("CGMCC登录API调试")
    print("=" * 60)
    print(f"用户名: {username}")
    print(f"基础URL: {base_url}")
    print()
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    })
    
    # 测试的登录端点列表
    login_endpoints = [
        "/api/login",
        "/api/auth/login",
        "/api/user/login",
        "/api/account/login",
        "/login",
        "/auth/login",
        "/user/login",
    ]
    
    # 测试的数据格式
    login_data_formats = [
        {
            "name": "JSON格式 - username/password",
            "data": {"username": username, "password": password},
            "json": True
        },
        {
            "name": "JSON格式 - user/pass",
            "data": {"user": username, "pass": password},
            "json": True
        },
        {
            "name": "JSON格式 - email/password",
            "data": {"email": username, "password": password},
            "json": True
        },
        {
            "name": "JSON格式 - account/password",
            "data": {"account": username, "password": password},
            "json": True
        },
        {
            "name": "Form格式 - username/password",
            "data": {"username": username, "password": password},
            "json": False
        },
    ]
    
    print("开始测试登录端点...\n")
    
    for endpoint in login_endpoints:
        url = urljoin(base_url, endpoint)
        print(f"[测试端点] {endpoint}")
        print(f"  URL: {url}")
        
        # 先测试GET请求，看看端点是否存在
        try:
            get_response = session.get(url, timeout=5, allow_redirects=False)
            print(f"  GET状态码: {get_response.status_code}")
            if get_response.status_code == 405:
                print("  ✓ 端点存在，但不支持GET方法")
            elif get_response.status_code == 404:
                print("  ✗ 端点不存在")
                continue
        except Exception as e:
            print(f"  GET请求错误: {e}")
            continue
        
        # 测试不同的数据格式
        for fmt in login_data_formats:
            try:
                if fmt['json']:
                    response = session.post(
                        url,
                        json=fmt['data'],
                        timeout=10,
                        allow_redirects=False
                    )
                else:
                    # Form格式需要修改Content-Type
                    headers = session.headers.copy()
                    headers.pop('Content-Type', None)
                    response = session.post(
                        url,
                        data=fmt['data'],
                        headers=headers,
                        timeout=10,
                        allow_redirects=False
                    )
                
                print(f"    [{fmt['name']}] 状态码: {response.status_code}")
                
                # 检查响应
                if response.status_code == 200:
                    try:
                        data = response.json()
                        print(f"    ✓ 成功！响应: {json.dumps(data, ensure_ascii=False, indent=2)[:200]}")
                        
                        # 查找token
                        token = (
                            data.get('token') or
                            data.get('access_token') or
                            data.get('accessToken') or
                            data.get('data', {}).get('token') or
                            data.get('data', {}).get('access_token')
                        )
                        if token:
                            print(f"    ✓ 找到token: {token[:50]}...")
                    except:
                        print(f"    ✓ 成功！响应: {response.text[:200]}")
                elif response.status_code == 401:
                    print(f"    ✗ 认证失败（可能是格式不对）")
                elif response.status_code == 404:
                    print(f"    ✗ 端点不存在")
                    break
                elif response.status_code in [301, 302, 303, 307, 308]:
                    print(f"    → 重定向到: {response.headers.get('Location', '未知')}")
                else:
                    print(f"    ? 状态码: {response.status_code}, 响应: {response.text[:100]}")
                    
            except requests.exceptions.Timeout:
                print(f"    ✗ 请求超时")
            except Exception as e:
                print(f"    ✗ 错误: {e}")
        
        print()
    
    print("=" * 60)
    print("测试完成")
    print("=" * 60)
    print("\n提示:")
    print("1. 如果找到成功的端点，请更新config.json中的api_login_url")
    print("2. 如果所有端点都失败，可能需要:")
    print("   - 检查网站是否需要验证码")
    print("   - 使用浏览器开发者工具查看实际的登录请求")
    print("   - 可能需要先获取CSRF token或其他安全token")

if __name__ == '__main__':
    test_login_endpoints()
