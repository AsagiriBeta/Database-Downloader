#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CGMCC数据库自动下载脚本
支持HTTP/HTTPS和FTP协议下载
"""

import os
import sys
import json
import logging
import argparse
from pathlib import Path
from typing import Optional, Dict, List
from urllib.parse import urlparse
import time

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError:
    print("错误: 请先安装requests库: pip install requests")
    sys.exit(1)

try:
    from ftplib import FTP
except ImportError:
    FTP = None

# 配置日志
logs_dir = Path('logs')
logs_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(logs_dir / 'cgmcc_downloader.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class CGMCCDownloader:
    """CGMCC数据库下载器"""
    
    def __init__(self, config_file: str = "config.json"):
        """
        初始化下载器
        
        Args:
            config_file: 配置文件路径
        """
        self.config = self.load_config(config_file)
        self.session = self.create_session()
        self.download_dir = Path(self.config.get('download_dir', './downloads'))
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.token = None
        self.token_file = Path('cgmcc_token.json')
        
        # 如果配置中有cookies，设置cookie
        cookies = self.config.get('cookies', {})
        if cookies:
            for key, value in cookies.items():
                self.session.cookies.set(key, value, domain='www.cgmcc.net')
            logger.info(f"已加载 {len(cookies)} 个cookie")
        
    def load_config(self, config_file: str) -> Dict:
        """加载配置文件"""
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            logger.warning(f"配置文件 {config_file} 不存在，使用默认配置")
            return self.get_default_config()
    
    def get_default_config(self) -> Dict:
        """获取默认配置"""
        return {
            "base_url": "https://www.cgmcc.net",
            "download_dir": "./downloads",
            "username": "",
            "password": "",
            "token": "",
            "token_file": "cgmcc_token.json",
            "api_login_url": "/api/login",
            "api_auth_header": "Authorization",
            "token_type": "Bearer",
            "timeout": 30,
            "retry_times": 3,
            "retry_delay": 5,
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "download_urls": [],
            "ftp_config": {
                "host": "",
                "port": 21,
                "username": "",
                "password": "",
                "remote_path": "/",
                "files": []
            }
        }
    
    def create_session(self) -> requests.Session:
        """创建带重试机制的会话"""
        session = requests.Session()
        
        # 设置重试策略
        retry_strategy = Retry(
            total=self.config.get('retry_times', 3),
            backoff_factor=self.config.get('retry_delay', 5),
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # 设置请求头
        session.headers.update({
            'User-Agent': self.config.get('user_agent', 'CGMCC-Downloader/1.0')
        })
        
        return session
    
    def load_token(self) -> Optional[str]:
        """
        从配置文件或token文件加载token
        
        Returns:
            token字符串，如果不存在则返回None
        """
        # 首先检查配置文件中是否有token
        token = self.config.get('token', '').strip()
        if token:
            logger.info("从配置文件加载token")
            return token
        
        # 检查token文件
        token_file_path = Path(self.config.get('token_file', 'cgmcc_token.json'))
        if token_file_path.exists():
            try:
                with open(token_file_path, 'r', encoding='utf-8') as f:
                    token_data = json.load(f)
                    token = token_data.get('token', '').strip()
                    if token:
                        logger.info("从token文件加载token")
                        return token
            except Exception as e:
                logger.warning(f"读取token文件失败: {e}")
        
        return None
    
    def save_token(self, token: str, expires_in: Optional[int] = None):
        """
        保存token到文件
        
        Args:
            token: token字符串
            expires_in: token过期时间（秒），可选
        """
        token_file_path = Path(self.config.get('token_file', 'cgmcc_token.json'))
        token_data = {
            'token': token,
            'saved_at': int(time.time())
        }
        if expires_in:
            token_data['expires_at'] = int(time.time()) + expires_in
        
        try:
            with open(token_file_path, 'w', encoding='utf-8') as f:
                json.dump(token_data, f, indent=2)
            logger.info(f"Token已保存到: {token_file_path}")
        except Exception as e:
            logger.error(f"保存token失败: {e}")
    
    def get_token_from_login(self) -> Optional[str]:
        """
        通过用户名密码获取token或建立session
        
        Returns:
            token字符串，如果获取失败则返回None
        """
        username = self.config.get('username')
        password = self.config.get('password')
        
        if not username or not password:
            logger.warning("未配置用户名和密码，无法获取token")
            return None
        
        base_url = self.config.get('base_url')
        api_login_url = self.config.get('api_login_url', '/api/login')
        login_url = f"{base_url}{api_login_url}"
        
        logger.info(f"尝试登录: {login_url}")
        
        try:
            # 尝试多种常见的登录API格式
            # 注意：根据实际请求，CGMCC使用multipart/form-data格式
            # 需要logincode（验证码），如果配置中没有则尝试空值或跳过
            logincode = self.config.get('logincode', '')
            
            login_data_formats = [
                # Multipart格式（CGMCC实际使用的格式）- 带验证码
                {
                    'url': login_url,
                    'data': {'username': username, 'password': password, 'logincode': logincode},
                    'files': None,
                    'content_type': 'multipart/form-data'
                },
                # Multipart格式 - 不带验证码（某些情况下可能不需要）
                {
                    'url': login_url,
                    'data': {'username': username, 'password': password},
                    'files': None,
                    'content_type': 'multipart/form-data'
                },
                # JSON格式 - username/password
                {
                    'url': login_url,
                    'data': {'username': username, 'password': password},
                    'files': None,
                    'content_type': 'application/json'
                },
                # Form格式 - application/x-www-form-urlencoded
                {
                    'url': login_url,
                    'data': {'username': username, 'password': password},
                    'files': None,
                    'content_type': 'application/x-www-form-urlencoded'
                },
            ]
            
            for login_format in login_data_formats:
                try:
                    content_type = login_format.get('content_type', 'application/json')
                    headers = {}
                    
                    if content_type == 'multipart/form-data':
                        # multipart/form-data格式，需要传递files参数（即使是None）来触发multipart编码
                        # 或者使用files参数传递空元组列表
                        response = self.session.post(
                            login_format['url'],
                            data=login_format['data'],
                            files=[],  # 空列表会触发multipart编码
                            timeout=self.config.get('timeout', 30)
                        )
                    elif content_type == 'application/json':
                        response = self.session.post(
                            login_format['url'],
                            json=login_format['data'],
                            timeout=self.config.get('timeout', 30)
                        )
                    else:
                        # application/x-www-form-urlencoded格式
                        headers['Content-Type'] = content_type
                        response = self.session.post(
                            login_format['url'],
                            data=login_format['data'],
                            headers=headers,
                            timeout=self.config.get('timeout', 30)
                        )
                    
                    logger.debug(f"登录响应状态码: {response.status_code}")
                    
                    if response.status_code in [200, 201]:
                        # 检查响应内容
                        try:
                            response_data = response.json()
                            logger.debug(f"登录响应: {json.dumps(response_data, ensure_ascii=False)[:200]}")
                            
                            # 检查登录是否成功
                            if response_data.get('status') == 0 or response_data.get('msg') == '成功':
                                logger.info("登录成功")
                                
                                # 尝试从响应中提取token
                                token = (
                                    response_data.get('token') or
                                    response_data.get('access_token') or
                                    response_data.get('accessToken') or
                                    response_data.get('data', {}).get('token') or
                                    response_data.get('data', {}).get('access_token')
                                )
                                
                                if token:
                                    expires_in = response_data.get('expires_in') or response_data.get('expiresIn')
                                    logger.info("成功获取token")
                                    self.save_token(token, expires_in)
                                    return token
                                else:
                                    # 如果没有token，检查是否使用cookie认证
                                    cookies = self.session.cookies
                                    if cookies:
                                        logger.info("登录成功，使用cookie认证")
                                        # 将cookie信息保存为token（用于标识已登录）
                                        cookie_str = '; '.join([f"{k}={v}" for k, v in cookies.items()])
                                        self.save_token(f"cookie:{cookie_str}")
                                        return "cookie_auth"  # 返回特殊标识表示使用cookie
                                    else:
                                        logger.warning("登录成功但未找到token或cookie")
                                        return "session_auth"  # 使用session认证
                        except Exception as e:
                            logger.debug(f"解析响应失败: {e}")
                            # 检查响应头
                            token = response.headers.get('Authorization') or response.headers.get('X-Auth-Token')
                            if token:
                                logger.info("从响应头获取token")
                                self.save_token(token)
                                return token
                            
                            # 检查cookie
                            cookies = self.session.cookies
                            if cookies:
                                logger.info("登录成功，使用cookie认证")
                                cookie_str = '; '.join([f"{k}={v}" for k, v in cookies.items()])
                                self.save_token(f"cookie:{cookie_str}")
                                return "cookie_auth"
                    
                    # 如果状态码是401或403，说明格式不对，继续尝试下一个
                    if response.status_code in [401, 403]:
                        logger.debug(f"认证失败，尝试下一个格式")
                        continue
                    elif response.status_code == 405:
                        logger.debug(f"方法不允许，尝试下一个端点")
                        break
                        
                except Exception as e:
                    logger.debug(f"尝试登录格式失败: {e}")
                    continue
            
            logger.error("无法获取token，请检查登录API端点或数据格式")
            logger.info("提示: 请查看浏览器开发者工具中的网络请求，找到实际的登录API")
            return None
                
        except Exception as e:
            logger.error(f"获取token过程出错: {str(e)}")
            return None
    
    def set_token_auth(self, token: str):
        """
        设置token认证头或cookie认证
        
        Args:
            token: token字符串或cookie认证标识
        """
        if token == "cookie_auth" or token == "session_auth":
            # 使用cookie/session认证，不需要设置header
            self.token = token
            logger.info("已设置cookie/session认证")
            return
        
        if token.startswith("cookie:"):
            # 从保存的cookie字符串恢复cookie
            cookie_str = token[7:]  # 去掉"cookie:"前缀
            # 这里cookie已经在session中，不需要额外设置
            self.token = token
            logger.info("已恢复cookie认证")
            return
        
        token_type = self.config.get('token_type', 'Bearer')
        auth_header = self.config.get('api_auth_header', 'Authorization')
        
        if token_type:
            auth_value = f"{token_type} {token}"
        else:
            auth_value = token
        
        self.session.headers.update({auth_header: auth_value})
        self.token = token
        logger.info("已设置token认证")
    
    def login(self) -> bool:
        """
        登录CGMCC网站（使用token或用户名密码）
        
        Returns:
            登录是否成功
        """
        # 首先尝试加载已保存的token
        token = self.load_token()
        
        if token:
            self.set_token_auth(token)
            # 验证token是否有效
            if self.verify_token():
                logger.info("使用已保存的token登录成功")
                return True
            else:
                logger.warning("已保存的token无效，尝试重新获取")
        
        # 如果没有token或token无效，尝试通过用户名密码获取
        token = self.get_token_from_login()
        
        if token:
            self.set_token_auth(token)
            logger.info("使用新获取的token登录成功")
            return True
        else:
            # 如果没有配置用户名密码，尝试不使用token
            username = self.config.get('username')
            password = self.config.get('password')
            
            if not username or not password:
                logger.info("未配置用户名和密码，跳过登录")
                return True
            
            logger.error("无法获取token，登录失败")
            logger.info("提示: 由于网站使用JavaScript处理登录，建议:")
            logger.info("  1. 手动登录网站，从浏览器开发者工具中获取token")
            logger.info("  2. 运行 python extract_token.py 获取帮助")
            logger.info("  3. 或者查看 get_token_from_browser.md 文件")
            return False
    
    def verify_token(self) -> bool:
        """
        验证token是否有效
        
        Returns:
            token是否有效
        """
        # 检查是否有cookie认证
        if self.session.cookies:
            return True
        
        if not self.token:
            return False
        
        # 如果是cookie认证标识，直接返回True
        if self.token in ["cookie_auth", "session_auth"] or self.token.startswith("cookie:"):
            return True
        
        base_url = self.config.get('base_url')
        # 尝试访问一个需要认证的端点来验证token
        verify_urls = [
            f"{base_url}/api/user/info",
            f"{base_url}/api/auth/verify",
            f"{base_url}/api/profile",
        ]
        
        for url in verify_urls:
            try:
                response = self.session.get(url, timeout=5)
                if response.status_code == 200:
                    return True
                elif response.status_code == 401:
                    return False
            except:
                continue
        
        # 如果无法验证，假设token有效（可能是端点不存在）
        return True
    
    def download_file_http(self, url: str, filename: Optional[str] = None) -> bool:
        """
        通过HTTP/HTTPS下载文件
        
        Args:
            url: 下载链接
            filename: 保存的文件名（可选）
            
        Returns:
            下载是否成功
        """
        try:
            logger.info(f"开始下载: {url}")
            
            # 如果没有指定文件名，从URL中提取
            if not filename:
                filename = os.path.basename(urlparse(url).path) or "download_file"
            
            filepath = self.download_dir / filename
            
            # 流式下载大文件
            response = self.session.get(
                url,
                stream=True,
                timeout=self.config.get('timeout', 30)
            )
            response.raise_for_status()
            
            # 获取文件大小
            total_size = int(response.headers.get('content-length', 0))
            
            # 下载文件
            downloaded = 0
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            print(f"\r进度: {percent:.1f}% ({downloaded}/{total_size} bytes)", end='', flush=True)
            
            print()  # 换行
            logger.info(f"文件已保存至: {filepath}")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"下载失败 {url}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"下载过程出错 {url}: {str(e)}")
            return False
    
    def download_file_ftp(self, remote_path: str, local_filename: Optional[str] = None) -> bool:
        """
        通过FTP下载文件
        
        Args:
            remote_path: FTP服务器上的文件路径
            local_filename: 本地保存的文件名（可选）
            
        Returns:
            下载是否成功
        """
        if FTP is None:
            logger.error("FTP功能不可用")
            return False
        
        ftp_config = self.config.get('ftp_config', {})
        host = ftp_config.get('host')
        port = ftp_config.get('port', 21)
        username = ftp_config.get('username')
        password = ftp_config.get('password')
        
        if not host:
            logger.error("FTP配置不完整")
            return False
        
        try:
            logger.info(f"连接FTP服务器: {host}:{port}")
            ftp = FTP()
            ftp.connect(host, port)
            
            if username and password:
                ftp.login(username, password)
            else:
                ftp.login()
            
            # 切换到远程目录
            remote_dir = os.path.dirname(remote_path) or ftp_config.get('remote_path', '/')
            if remote_dir:
                ftp.cwd(remote_dir)
            
            # 确定本地文件名
            if not local_filename:
                local_filename = os.path.basename(remote_path)
            
            filepath = self.download_dir / local_filename
            
            logger.info(f"开始下载FTP文件: {remote_path}")
            
            # 下载文件
            with open(filepath, 'wb') as f:
                ftp.retrbinary(f'RETR {os.path.basename(remote_path)}', f.write)
            
            ftp.quit()
            logger.info(f"文件已保存至: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"FTP下载失败 {remote_path}: {str(e)}")
            return False
    
    def download_all(self) -> Dict[str, bool]:
        """
        下载所有配置的文件
        
        Returns:
            下载结果字典 {文件名: 是否成功}
        """
        results = {}
        
        # 登录（如果需要）
        if not self.login():
            logger.warning("登录失败，继续尝试下载...")
        
        # HTTP/HTTPS下载
        download_urls = self.config.get('download_urls', [])
        for url in download_urls:
            filename = os.path.basename(urlparse(url).path) or f"file_{int(time.time())}"
            success = self.download_file_http(url, filename)
            results[filename] = success
            time.sleep(1)  # 避免请求过快
        
        # FTP下载
        ftp_config = self.config.get('ftp_config', {})
        ftp_files = ftp_config.get('files', [])
        for remote_file in ftp_files:
            success = self.download_file_ftp(remote_file)
            results[remote_file] = success
            time.sleep(1)
        
        return results
    
    def download_single(self, url: str, filename: Optional[str] = None) -> bool:
        """
        下载单个文件
        
        Args:
            url: 下载链接或FTP路径
            filename: 保存的文件名（可选）
            
        Returns:
            下载是否成功
        """
        # 判断是HTTP还是FTP
        parsed = urlparse(url)
        
        if parsed.scheme in ['http', 'https']:
            return self.download_file_http(url, filename)
        elif parsed.scheme == 'ftp':
            return self.download_file_ftp(url, filename)
        else:
            logger.error(f"不支持的协议: {parsed.scheme}")
            return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='CGMCC数据库自动下载工具')
    parser.add_argument('-c', '--config', default='config.json', help='配置文件路径')
    parser.add_argument('-u', '--url', help='单个文件下载URL')
    parser.add_argument('-o', '--output', help='输出文件名')
    parser.add_argument('--no-login', action='store_true', help='跳过登录步骤')
    
    args = parser.parse_args()
    
    try:
        downloader = CGMCCDownloader(args.config)
        
        if args.url:
            # 下载单个文件
            success = downloader.download_single(args.url, args.output)
            sys.exit(0 if success else 1)
        else:
            # 下载所有配置的文件
            results = downloader.download_all()
            
            # 统计结果
            total = len(results)
            success_count = sum(1 for v in results.values() if v)
            
            logger.info(f"\n下载完成: {success_count}/{total} 个文件成功")
            
            if success_count < total:
                logger.warning("部分文件下载失败，请查看日志")
                sys.exit(1)
            else:
                sys.exit(0)
                
    except KeyboardInterrupt:
        logger.info("\n用户中断下载")
        sys.exit(1)
    except Exception as e:
        logger.error(f"程序出错: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()
