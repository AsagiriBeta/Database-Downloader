# 数据库下载工具

这是一个用于从CGMCC（中国普通微生物菌种保藏管理中心）和NCBI数据库自动下载数据的Python工具集。

## 功能特性

- ✅ **CGMCC数据库下载**：支持HTTP/HTTPS和FTP协议下载，支持Token和Cookie认证
- ✅ **NCBI基因组下载**：基于CSV文件中的Tax ID批量下载基因组数据
- ✅ 自动重试机制和下载进度显示
- ✅ 完整的日志记录
- ✅ 配置文件支持

## 安装

### 1. 环境要求

- Python 3.7 或更高版本

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 可选依赖（推荐）

为了获得更好的NCBI基因组下载体验，建议安装：

```bash
pip install ncbi-genome-download
```

## 快速开始

### CGMCC数据库下载

#### 1. 配置

复制配置文件模板：

```bash
copy config.json.example config.json
```

编辑 `config.json`，配置下载链接和认证信息。

⚠️ **重要**：`config.json` 包含敏感信息，不会被提交到Git。请参考 `SECURITY.md` 了解安全注意事项。

#### 2. 认证方式

**方式1：使用Cookie（推荐）**

1. 在浏览器中登录 https://www.cgmcc.net
2. 按F12打开开发者工具，切换到Application/Storage标签
3. 选择Cookies -> https://www.cgmcc.net
4. 复制cookie值（如JSESSIONID）
5. 在 `config.json` 中添加：

```json
{
  "cookies": {
    "JSESSIONID": "你的cookie值"
  }
}
```

或运行辅助工具：

```bash
python setup_cookie_auth.py
```

**方式2：使用Token**

1. 在浏览器中登录网站
2. 从开发者工具的Network标签或Local Storage中获取token
3. 在 `config.json` 中添加：

```json
{
  "token": "你的token值"
}
```

或运行辅助工具：

```bash
python extract_token.py
```

**方式3：使用用户名密码（自动获取token）**

```json
{
  "username": "你的用户名",
  "password": "你的密码",
  "api_login_url": "/api/login"
}
```

#### 3. 运行下载

批量下载（使用配置文件）：

```bash
python cgmcc_downloader.py
```

下载单个文件：

```bash
python cgmcc_downloader.py -u https://www.cgmcc.net/download/file.csv -o output.csv
```

跳过登录：

```bash
python cgmcc_downloader.py --no-login
```

### NCBI基因组下载

#### 1. 准备CSV文件

将CSV文件放入 `input/` 目录中。CSV文件应包含以下列：
- `Culture collection no.`: CGMCC编号
- `Genome Sequence associated NCBI tax ID`: NCBI Tax ID
- `species`: 物种名称（可选）

**注意**：`input/` 目录已添加到 `.gitignore`，不会被提交到Git。

#### 2. 运行下载

只解析CSV文件（不下载）：

```bash
python download_ncbi_genomes.py "input/advsearch_bacdive_CGMCC_放线菌.csv" --no-download
```

下载所有基因组：

```bash
python download_ncbi_genomes.py "input/advsearch_bacdive_CGMCC_放线菌.csv" -o ./genomes
```

强制使用Entrez API：

```bash
python download_ncbi_genomes.py "input/advsearch_bacdive_CGMCC_放线菌.csv" --use-api
```

## 配置文件说明

### config.json 示例

```json
{
  "base_url": "https://www.cgmcc.net",
  "download_dir": "./downloads",
  "username": "your_username",
  "password": "your_password",
  "token": "",
  "cookies": {
    "JSESSIONID": "your_session_id"
  },
  "api_login_url": "/api/login",
  "api_auth_header": "Authorization",
  "token_type": "Bearer",
  "timeout": 30,
  "retry_times": 3,
  "retry_delay": 5,
  "download_urls": [
    "https://www.cgmcc.net/download/data1.csv",
    "https://www.cgmcc.net/download/data2.xlsx"
  ],
  "ftp_config": {
    "host": "ftp.cgmcc.net",
    "port": 21,
    "username": "your_ftp_username",
    "password": "your_ftp_password",
    "remote_path": "/data",
    "files": [
      "/data/file1.txt"
    ]
  }
}
```

### 配置项说明

- `base_url`: CGMCC网站基础URL
- `download_dir`: 文件下载保存目录
- `username` / `password`: 登录用户名和密码（用于自动获取token）
- `token`: 直接使用token（如果已有）
- `cookies`: Cookie认证信息（推荐方式）
- `api_login_url`: 登录API端点（默认: `/api/login`）
- `api_auth_header`: 认证头名称（默认: `Authorization`）
- `token_type`: Token类型（默认: `Bearer`）
- `timeout`: 请求超时时间（秒）
- `retry_times`: 重试次数
- `retry_delay`: 重试延迟（秒）
- `download_urls`: HTTP/HTTPS下载链接列表
- `ftp_config`: FTP服务器配置

## 命令行参数

### cgmcc_downloader.py

- `-c, --config`: 指定配置文件路径（默认: config.json）
- `-u, --url`: 下载单个文件的URL
- `-o, --output`: 指定输出文件名
- `--no-login`: 跳过登录步骤

### download_ncbi_genomes.py

- `csv_file`: CSV文件路径（必需）
- `-o, --output`: 下载目录（默认: ./genomes）
- `--report`: 映射报告文件名（默认: mapping_report.json）
- `--no-download`: 只解析CSV文件，不下载基因组
- `--use-api`: 强制使用Entrez API而不是ncbi-genome-download

## 输出文件

### CGMCC下载

- `logs/cgmcc_downloader.log`: 下载日志文件
- `cgmcc_token.json`: 保存的token文件（如果使用token认证，位于项目根目录）
- `downloads/`: 下载的文件目录

### NCBI下载

- `logs/ncbi_genome_download.log`: 下载日志文件
- `output/mapping_report.json`: Tax ID和CGMCC编号的映射报告
- `output/download_results.json`: 下载结果统计
- `genomes/`: 下载的基因组文件目录

**注意**：所有日志文件保存在 `logs/` 目录，所有报告文件保存在 `output/` 目录。这些目录已添加到 `.gitignore`，不会被提交到Git。

## 映射问题处理

NCBI下载工具会自动识别并报告以下映射问题：

1. **一个Tax ID对应多个CGMCC编号**：脚本会报告所有映射关系
2. **一个CGMCC编号对应多个Tax ID**：脚本会报告所有映射关系
3. **只有Tax ID没有CGMCC编号**：这些Tax ID会被标记为 `NO_CGMCC_{tax_id}`

## 常见问题

### 1. 登录失败

**问题**：无法获取token或登录失败

**解决方案**：
- 使用Cookie认证（推荐）：从浏览器复制cookie到配置文件
- 检查用户名和密码是否正确
- 查看日志文件了解详细错误信息

### 2. 下载失败

**问题**：文件下载失败

**解决方案**：
- 检查网络连接
- 确认下载链接是否有效
- 某些链接可能需要登录后才能访问
- 查看日志文件获取详细错误信息

### 3. NCBI下载失败

**问题**：NCBI基因组下载失败

**解决方案**：
- 检查网络连接，确保能访问NCBI服务器
- 某些Tax ID可能没有可用的基因组数据
- 安装 `ncbi-genome-download` 工具以获得更好的下载体验
- 使用 `--use-api` 参数强制使用Entrez API

### 4. CSV文件解析错误

**问题**：无法解析CSV文件

**解决方案**：
- 确保CSV文件格式正确
- 使用绝对路径指定CSV文件
- 检查文件编码是否为UTF-8

## 安全提示

⚠️ **重要安全提示**：

1. **配置文件安全**：
   - `config.json` 和 `cgmcc_token.json` 已添加到 `.gitignore`，不会被提交到Git
   - 请勿在代码中硬编码账号密码或token
   - 使用 `config.json.example` 作为配置模板

2. **敏感信息处理**：
   - 不要将包含真实账号密码的配置文件提交到版本控制系统
   - Token和Cookie信息应保存在本地，不要分享
   - 如果意外提交了敏感信息，请立即更换密码和token

3. **环境变量（可选）**：
   - 对于生产环境，建议使用环境变量存储敏感信息
   - 可以通过环境变量覆盖配置文件中的值

## 注意事项

1. **遵守网站条款**：请确保遵守CGMCC和NCBI网站的使用条款
2. **请求频率**：避免过于频繁的请求，以免被封IP
3. **数据使用**：下载的数据请遵守相关使用协议
4. **存储空间**：NCBI基因组文件可能很大，确保有足够的磁盘空间
5. **配置文件**：首次使用前，请复制 `config.json.example` 为 `config.json` 并填入你的配置信息

## 项目结构

```
Database-Downloader/
├── cgmcc_downloader.py      # CGMCC数据库下载工具
├── download_ncbi_genomes.py # NCBI基因组下载工具
├── extract_token.py         # Token提取辅助工具
├── setup_cookie_auth.py     # Cookie认证设置工具
├── config.json.example      # 配置文件模板（请复制为config.json使用）
├── requirements.txt         # Python依赖包
├── README.md               # 项目说明文档
├── .gitignore             # Git忽略文件配置
├── input/                  # CSV输入文件目录（已忽略）
├── output/                 # 输出报告文件目录（已忽略）
│   ├── mapping_report.json
│   └── download_results.json
├── logs/                   # 日志文件目录（已忽略）
│   ├── cgmcc_downloader.log
│   └── ncbi_genome_download.log
├── downloads/              # CGMCC下载文件目录（已忽略）
├── genomes/                # NCBI下载基因组目录（已忽略）
└── tests/                  # 测试和调试脚本目录
    ├── test_*.py           # 各种测试脚本
    └── debug_login.py      # 登录调试脚本
```

**注意**：
- `config.json` 和 `cgmcc_token.json` 不在仓库中，需要根据 `config.json.example` 创建
- `input/`、`output/`、`logs/`、`downloads/`、`genomes/` 目录已添加到 `.gitignore`，不会被提交到Git

## 许可证

本项目仅供学习和研究使用。

## 贡献

欢迎提交Issue和Pull Request！
