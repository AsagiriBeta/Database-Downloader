#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试CGMCC网站协议和登录要求
"""

import requests
import json
from urllib.parse import urljoin

def test_cgmcc():
    """测试CGMCC网站"""
    base_url = "https://www.cgmcc.net"
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    
    print("=" * 60)
    print("CGMCC网站协议和登录测试")
    print("=" * 60)
    
    # 测试1: 访问首页
    print("\n[测试1] 访问首页...")
    try:
        response = session.get(base_url, timeout=10)
        print(f"  状态码: {response.status_code}")
        print(f"  协议: HTTPS")
        print(f"  需要登录: {'是' if 'login' in response.text.lower() or '登录' in response.text else '未知'}")
    except Exception as e:
        print(f"  错误: {e}")
    
    # 测试2: 检查登录页面
    print("\n[测试2] 检查登录页面...")
    login_urls = [
        urljoin(base_url, "/login"),
        urljoin(base_url, "/user/login"),
        urljoin(base_url, "/account/login"),
    ]
    for url in login_urls:
        try:
            response = session.get(url, timeout=10, allow_redirects=False)
            if response.status_code == 200:
                print(f"  找到登录页面: {url}")
                print(f"  需要登录: 是")
                break
        except:
            pass
    else:
        print("  未找到明确的登录页面")
    
    # 测试3: 检查API端点
    print("\n[测试3] 检查可能的API端点...")
    api_endpoints = [
        "/api/strain",
        "/api/strain/list",
        "/api/download",
        "/api/data",
        "/strain",
        "/resource",
    ]
    for endpoint in api_endpoints:
        url = urljoin(base_url, endpoint)
        try:
            response = session.get(url, timeout=10, allow_redirects=False)
            if response.status_code == 200:
                content_type = response.headers.get('Content-Type', '')
                print(f"  找到端点: {endpoint}")
                print(f"    状态码: {response.status_code}")
                print(f"    内容类型: {content_type}")
                if 'json' in content_type:
                    print(f"    协议: REST API (JSON)")
                elif 'text/html' in content_type:
                    print(f"    协议: Web页面")
        except:
            pass
    
    # 测试4: 检查FTP
    print("\n[测试4] 检查FTP服务器...")
    try:
        from ftplib import FTP
        ftp_hosts = ["ftp.cgmcc.net", "www.cgmcc.net"]
        for host in ftp_hosts:
            try:
                ftp = FTP()
                ftp.connect(host, 21, timeout=5)
                print(f"  找到FTP服务器: {host}")
                print(f"  协议: FTP")
                ftp.quit()
                break
            except:
                pass
        else:
            print("  未找到FTP服务器")
    except ImportError:
        print("  FTP库不可用")
    
    # 测试5: 检查数据下载链接
    print("\n[测试5] 检查数据下载链接...")
    try:
        response = session.get(base_url, timeout=10)
        # 查找可能的下载链接
        import re
        download_patterns = [
            r'href=["\']([^"\']*\.(csv|excel|xlsx|tsv|txt|json|xml|zip|tar|gz))["\']',
            r'href=["\']([^"\']*download[^"\']*)["\']',
            r'url["\']?\s*:\s*["\']([^"\']*download[^"\']*)["\']',
        ]
        found_links = set()
        for pattern in download_patterns:
            matches = re.findall(pattern, response.text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    link = match[0]
                else:
                    link = match
                if link.startswith('http') or link.startswith('/'):
                    found_links.add(link)
        
        if found_links:
            print(f"  找到 {len(found_links)} 个可能的下载链接:")
            for link in list(found_links)[:5]:  # 只显示前5个
                full_url = urljoin(base_url, link) if not link.startswith('http') else link
                print(f"    {full_url}")
        else:
            print("  未找到明显的下载链接")
    except Exception as e:
        print(f"  错误: {e}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
    
    # 生成建议
    print("\n建议:")
    print("1. CGMCC网站使用HTTPS协议")
    print("2. 可能需要登录才能下载数据")
    print("3. 建议查看网站的实际登录流程和API文档")
    print("4. 如果网站使用JavaScript动态加载，可能需要使用Selenium")

if __name__ == '__main__':
    test_cgmcc()
