#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从NCBI下载基因组的脚本
根据CSV文件中的Tax ID下载对应的基因组
处理CGMCC编号和Tax ID不一一对应的情况
"""

import os
import sys
import csv
import json
import logging
import argparse
import subprocess
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
from collections import defaultdict
import time

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError:
    print("错误: 请先安装requests库: pip install requests")
    sys.exit(1)

# 配置日志
logs_dir = Path('logs')
logs_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(logs_dir / 'ncbi_genome_download.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class NCBIGenomeDownloader:
    """NCBI基因组下载器"""
    
    def __init__(self, download_dir: str = "./genomes"):
        """
        初始化下载器
        
        Args:
            download_dir: 下载目录
        """
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.session = self.create_session()
        
        # 存储映射关系
        self.taxid_to_cgmcc: Dict[int, List[str]] = defaultdict(list)
        self.cgmcc_to_taxid: Dict[str, List[int]] = defaultdict(list)
        self.taxid_to_species: Dict[int, str] = {}
        
    def create_session(self) -> requests.Session:
        """创建带重试机制的会话"""
        session = requests.Session()
        
        retry_strategy = Retry(
            total=3,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        return session
    
    def parse_csv(self, csv_file: str) -> Tuple[Dict[int, List[str]], Dict[str, List[int]]]:
        """
        解析CSV文件，提取Tax ID和CGMCC编号的映射关系
        
        Args:
            csv_file: CSV文件路径
            
        Returns:
            (taxid_to_cgmcc, cgmcc_to_taxid) 映射字典
        """
        logger.info(f"开始解析CSV文件: {csv_file}")
        
        taxid_to_cgmcc = defaultdict(list)
        cgmcc_to_taxid = defaultdict(list)
        taxid_to_species = {}
        
        # 处理文件路径，支持相对路径和绝对路径
        csv_path = Path(csv_file)
        if not csv_path.is_absolute():
            csv_path = Path.cwd() / csv_path
        
        if not csv_path.exists():
            # 尝试使用glob查找
            csv_name = csv_path.name
            parent_dir = csv_path.parent
            found_files = list(parent_dir.glob(csv_name))
            if found_files:
                csv_path = found_files[0]
                logger.info(f"找到CSV文件: {csv_path}")
            else:
                raise FileNotFoundError(f"CSV文件不存在: {csv_file}")
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            # 跳过前3行（注释和空行）
            for _ in range(3):
                next(f, None)
            
            reader = csv.DictReader(f)
            
            for row_num, row in enumerate(reader, start=4):
                # 提取CGMCC编号
                cgmcc_col = row.get('Culture collection no.', '').strip()
                # 提取Tax ID
                taxid_col = row.get('Genome Sequence associated NCBI tax ID', '').strip()
                # 提取物种名称
                species = row.get('species', '').strip()
                
                # 处理CGMCC编号（可能有多个，用逗号分隔）
                cgmcc_numbers = []
                if cgmcc_col:
                    # 从字符串中提取所有CGMCC编号
                    import re
                    cgmcc_pattern = r'CGMCC\s+([\d\.AS]+)'
                    matches = re.findall(cgmcc_pattern, cgmcc_col, re.IGNORECASE)
                    for match in matches:
                        cgmcc_num = f"CGMCC {match}"
                        cgmcc_numbers.append(cgmcc_num)
                
                # 处理Tax ID
                tax_ids = []
                if taxid_col:
                    try:
                        tax_id = int(taxid_col)
                        tax_ids.append(tax_id)
                        if species:
                            taxid_to_species[tax_id] = species
                    except ValueError:
                        logger.warning(f"第{row_num}行: 无效的Tax ID: {taxid_col}")
                
                # 建立映射关系
                for tax_id in tax_ids:
                    for cgmcc in cgmcc_numbers:
                        if cgmcc not in taxid_to_cgmcc[tax_id]:
                            taxid_to_cgmcc[tax_id].append(cgmcc)
                        if tax_id not in cgmcc_to_taxid[cgmcc]:
                            cgmcc_to_taxid[cgmcc].append(tax_id)
                
                # 如果只有Tax ID没有CGMCC编号
                if tax_ids and not cgmcc_numbers:
                    for tax_id in tax_ids:
                        taxid_to_cgmcc[tax_id].append(f"NO_CGMCC_{tax_id}")
        
        self.taxid_to_cgmcc = taxid_to_cgmcc
        self.cgmcc_to_taxid = cgmcc_to_taxid
        self.taxid_to_species = taxid_to_species
        
        logger.info(f"解析完成:")
        logger.info(f"  - 找到 {len(taxid_to_cgmcc)} 个唯一的Tax ID")
        logger.info(f"  - 找到 {len(cgmcc_to_taxid)} 个唯一的CGMCC编号")
        
        # 检查不一一对应的情况
        self.check_mapping_issues()
        
        return taxid_to_cgmcc, cgmcc_to_taxid
    
    def check_mapping_issues(self):
        """检查并报告映射问题"""
        logger.info("\n检查映射关系...")
        
        # 一个Tax ID对应多个CGMCC编号
        multi_cgmcc = {tid: cgmccs for tid, cgmccs in self.taxid_to_cgmcc.items() if len(cgmccs) > 1}
        if multi_cgmcc:
            logger.warning(f"发现 {len(multi_cgmcc)} 个Tax ID对应多个CGMCC编号:")
            for tid, cgmccs in list(multi_cgmcc.items())[:10]:  # 只显示前10个
                species = self.taxid_to_species.get(tid, "未知")
                logger.warning(f"  Tax ID {tid} ({species}) -> {', '.join(cgmccs)}")
            if len(multi_cgmcc) > 10:
                logger.warning(f"  ... 还有 {len(multi_cgmcc) - 10} 个")
        
        # 一个CGMCC编号对应多个Tax ID
        multi_taxid = {cgmcc: tids for cgmcc, tids in self.cgmcc_to_taxid.items() if len(tids) > 1}
        if multi_taxid:
            logger.warning(f"发现 {len(multi_taxid)} 个CGMCC编号对应多个Tax ID:")
            for cgmcc, tids in list(multi_taxid.items())[:10]:  # 只显示前10个
                logger.warning(f"  {cgmcc} -> Tax IDs: {', '.join(map(str, tids))}")
            if len(multi_taxid) > 10:
                logger.warning(f"  ... 还有 {len(multi_taxid) - 10} 个")
        
        # 只有Tax ID没有CGMCC编号
        no_cgmcc = [tid for tid, cgmccs in self.taxid_to_cgmcc.items() 
                   if any(cgmcc.startswith("NO_CGMCC_") for cgmcc in cgmccs)]
        if no_cgmcc:
            logger.info(f"发现 {len(no_cgmcc)} 个Tax ID没有对应的CGMCC编号")
    
    def save_mapping_report(self, output_file: str = "mapping_report.json"):
        """保存映射关系报告"""
        # 确保输出目录存在
        output_path = Path(output_file)
        if output_path.parent.name != 'output':
            # 如果不在output目录，则移动到output目录
            output_dir = Path('output')
            output_dir.mkdir(exist_ok=True)
            output_path = output_dir / output_path.name
        
        report = {
            "taxid_to_cgmcc": {str(k): v for k, v in self.taxid_to_cgmcc.items()},
            "cgmcc_to_taxid": {k: [str(tid) for tid in v] for k, v in self.cgmcc_to_taxid.items()},
            "taxid_to_species": {str(k): v for k, v in self.taxid_to_species.items()},
            "statistics": {
                "total_taxids": len(self.taxid_to_cgmcc),
                "total_cgmcc": len(self.cgmcc_to_taxid),
                "taxids_without_cgmcc": len([tid for tid, cgmccs in self.taxid_to_cgmcc.items() 
                                            if any(cgmcc.startswith("NO_CGMCC_") for cgmcc in cgmccs)])
            }
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"映射报告已保存到: {output_path}")
    
    def check_ncbi_genome_download(self) -> bool:
        """检查是否安装了ncbi-genome-download"""
        try:
            result = subprocess.run(
                ['ncbi-genome-download', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    def download_genome_ncbi_genome_download(self, tax_id: int, output_dir: Optional[Path] = None) -> bool:
        """
        使用ncbi-genome-download工具下载基因组
        
        Args:
            tax_id: NCBI Tax ID
            output_dir: 输出目录
            
        Returns:
            是否成功
        """
        if output_dir is None:
            output_dir = self.download_dir
        
        try:
            logger.info(f"使用ncbi-genome-download下载Tax ID {tax_id}的基因组...")
            
            # ncbi-genome-download需要指定组（bacteria, archaea, fungi等）
            # 由于CSV文件中的都是放线菌，属于bacteria组
            cmd = [
                'ncbi-genome-download',
                'bacteria',  # 必需的位置参数：组名
                '--taxids', str(tax_id),  # 注意是--taxids（复数）
                '-o', str(output_dir),  # 使用-o而不是--output-folder
                '-F', 'fasta',  # 使用-F而不是--format
                '-l', 'complete,chromosome,scaffold,contig',  # 使用-l而不是--assembly-level
                '-p', '1'  # 使用-p而不是--parallel
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10分钟超时
            )
            
            if result.returncode == 0:
                logger.info(f"Tax ID {tax_id}的基因组下载成功")
                return True
            else:
                # 检查是否有实际下载的文件（即使返回码非0，有时也会下载成功）
                # ncbi-genome-download在某些情况下会返回非0但实际已下载
                error_msg = result.stderr if result.stderr else result.stdout
                logger.warning(f"Tax ID {tax_id}下载命令返回非0: {error_msg[:200]}")
                # 检查是否实际下载了文件
                # 文件通常保存在 refseq/bacteria/ 或 genbank/bacteria/ 目录下
                refseq_dir = output_dir / 'refseq' / 'bacteria'
                genbank_dir = output_dir / 'genbank' / 'bacteria'
                if refseq_dir.exists() or genbank_dir.exists():
                    logger.info(f"Tax ID {tax_id}可能已下载（检查输出目录）")
                    return True
                return False
                
        except subprocess.TimeoutExpired:
            logger.error(f"Tax ID {tax_id}下载超时")
            return False
        except Exception as e:
            logger.error(f"Tax ID {tax_id}下载出错: {str(e)}")
            return False
    
    def download_genome_entrez_api(self, tax_id: int, output_dir: Optional[Path] = None) -> bool:
        """
        使用NCBI Entrez API查找并下载基因组
        
        Args:
            tax_id: NCBI Tax ID
            output_dir: 输出目录
            
        Returns:
            是否成功
        """
        if output_dir is None:
            output_dir = self.download_dir
        
        try:
            logger.info(f"使用Entrez API查找Tax ID {tax_id}的基因组...")
            
            # 首先查找assembly accession
            base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
            
            # 搜索assembly
            search_url = f"{base_url}/esearch.fcgi"
            search_params = {
                'db': 'assembly',
                'term': f'txid{tax_id}[Organism:exp]',
                'retmode': 'json',
                'retmax': 10
            }
            
            response = self.session.get(search_url, params=search_params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            id_list = data.get('esearchresult', {}).get('idlist', [])
            if not id_list:
                logger.warning(f"Tax ID {tax_id}没有找到assembly记录")
                return False
            
            # 获取assembly信息
            summary_url = f"{base_url}/esummary.fcgi"
            summary_params = {
                'db': 'assembly',
                'id': ','.join(id_list[:5]),  # 只取前5个
                'retmode': 'json'
            }
            
            response = self.session.get(summary_url, params=summary_params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            # 选择最好的assembly（优先选择complete genome）
            best_assembly = None
            for uid, assembly in data.get('result', {}).items():
                if uid == 'uids':
                    continue
                
                assembly_level = assembly.get('assemblylevel', '').lower()
                if 'complete' in assembly_level:
                    best_assembly = assembly
                    break
            
            if not best_assembly:
                best_assembly = data.get('result', {}).get(id_list[0])
            
            if not best_assembly:
                logger.warning(f"Tax ID {tax_id}无法获取assembly信息")
                return False
            
            # 获取FTP路径
            ftp_path = best_assembly.get('ftppath_genbank', '') or best_assembly.get('ftppath_refseq', '')
            if not ftp_path:
                logger.warning(f"Tax ID {tax_id}没有FTP下载路径")
                return False
            
            # 下载基因组文件
            assembly_name = ftp_path.split('/')[-1]
            genome_file = f"{assembly_name}_genomic.fna.gz"
            genome_url = f"{ftp_path}/{genome_file}"
            
            logger.info(f"下载基因组文件: {genome_url}")
            
            local_file = output_dir / f"taxid_{tax_id}_{genome_file}"
            response = self.session.get(genome_url, stream=True, timeout=300)
            response.raise_for_status()
            
            with open(local_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            logger.info(f"Tax ID {tax_id}的基因组已下载到: {local_file}")
            return True
            
        except Exception as e:
            logger.error(f"Tax ID {tax_id}下载失败: {str(e)}")
            return False
    
    def download_all_genomes(self, use_ncbi_genome_download: bool = True) -> Dict[int, bool]:
        """
        下载所有Tax ID对应的基因组
        
        Args:
            use_ncbi_genome_download: 是否使用ncbi-genome-download工具（如果可用）
            
        Returns:
            下载结果字典 {Tax ID: 是否成功}
        """
        results = {}
        tax_ids = list(self.taxid_to_cgmcc.keys())
        total = len(tax_ids)
        
        logger.info(f"\n开始下载 {total} 个基因组的基因组...")
        
        # 检查是否可以使用ncbi-genome-download
        if use_ncbi_genome_download and self.check_ncbi_genome_download():
            logger.info("使用ncbi-genome-download工具下载")
            download_func = self.download_genome_ncbi_genome_download
        else:
            if use_ncbi_genome_download:
                logger.warning("ncbi-genome-download未安装，使用Entrez API下载")
                logger.info("提示: 安装ncbi-genome-download可以获得更好的下载体验: pip install ncbi-genome-download")
            download_func = self.download_genome_entrez_api
        
        for idx, tax_id in enumerate(tax_ids, 1):
            logger.info(f"\n[{idx}/{total}] 处理Tax ID: {tax_id}")
            cgmcc_list = self.taxid_to_cgmcc.get(tax_id, [])
            species = self.taxid_to_species.get(tax_id, "未知")
            logger.info(f"  CGMCC编号: {', '.join(cgmcc_list) if cgmcc_list else '无'}")
            logger.info(f"  物种: {species}")
            
            success = download_func(tax_id)
            results[tax_id] = success
            
            # 避免请求过快
            time.sleep(2)
        
        # 统计结果
        success_count = sum(1 for v in results.values() if v)
        logger.info(f"\n下载完成: {success_count}/{total} 个基因组成功")
        
        return results


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='从NCBI下载基因组（基于CSV文件中的Tax ID）')
    parser.add_argument('csv_file', help='包含Tax ID的CSV文件路径')
    parser.add_argument('-o', '--output', default='./genomes', help='下载目录（默认: ./genomes）')
    parser.add_argument('--report', default='mapping_report.json', help='映射报告文件（默认: mapping_report.json）')
    parser.add_argument('--no-download', action='store_true', help='只解析CSV文件，不下载基因组')
    parser.add_argument('--use-api', action='store_true', help='强制使用Entrez API而不是ncbi-genome-download')
    
    args = parser.parse_args()
    
    try:
        downloader = NCBIGenomeDownloader(args.output)
        
        # 解析CSV文件
        downloader.parse_csv(args.csv_file)
        
        # 保存映射报告
        downloader.save_mapping_report(args.report)
        
        if not args.no_download:
            # 下载基因组
            results = downloader.download_all_genomes(use_ncbi_genome_download=not args.use_api)
            
            # 保存下载结果到output目录
            output_dir = Path('output')
            output_dir.mkdir(exist_ok=True)
            results_file = output_dir / "download_results.json"
            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump({str(k): v for k, v in results.items()}, f, indent=2, ensure_ascii=False)
            logger.info(f"下载结果已保存到: {results_file}")
        else:
            logger.info("跳过下载步骤（--no-download）")
        
    except KeyboardInterrupt:
        logger.info("\n用户中断操作")
        sys.exit(1)
    except Exception as e:
        logger.error(f"程序出错: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
