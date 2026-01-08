"""
Nginx Configuration Manager - 配置管理器

核心职责：
1. 只管理server块，保留用户的其他配置
2. 给管理的server块添加标记，便于识别和删除
3. 增量更新配置，而不是全量覆盖
4. 支持include文件的读取和写入
"""

import re
from pathlib import Path
from typing import List, Optional, Dict, Any
from loguru import logger
from models.site_config import SiteConfigBase
from utils.encoding_utils import read_file_robust


class ConfigManager:
    """配置管理器 - 只管理server块，保留用户配置"""
    
    # 标记用于识别我们管理的server块
    MANAGED_MARKER = "# easyNginx-managed-site"
    MANAGED_START = "# easyNginx-MANAGED-START"
    MANAGED_END = "# easyNginx-MANAGED-END"
    
    def __init__(self, config_path: Optional[Path] = None):
        """初始化配置管理器."""
        self.config_path = config_path
        self.server_block_pattern = re.compile(
            r'(server\s*{[^}]*(?:{[^}]*}[^}]*)*})',
            re.MULTILINE | re.DOTALL
        )
        
    def load_original_config(self, config_path: Optional[Path] = None) -> str:
        """
        加载原始配置文件内容
        
        Args:
            config_path: 配置文件路径（可选）
            
        Returns:
            配置文件内容
        """
        if config_path is None:
            config_path = self.config_path
        
        if config_path is None:
            logger.error("Config path not specified")
            return ""
        
        if not config_path.exists():
            logger.warning(f"Config file not found: {config_path}, creating default")
            return self._create_default_config()
        
        # 使用健壮的编码检测读取文件
        content = read_file_robust(config_path)
        if content is None:
            logger.error(f"无法读取配置文件: {config_path}")
            return self._create_default_config()
        
        logger.info(f"Loaded config file: {config_path} ({len(content)} bytes)")
        return content
    
    def extract_managed_sites(self, content: str) -> str:
        """
        提取由我们管理的配置部分，保留其他配置
        
        Args:
            content: 完整配置内容
            
        Returns:
            去除管理server块后的配置内容
        """
        # 查找所有被标记的管理server块
        managed_pattern = re.compile(
            rf"{re.escape(self.MANAGED_START)}.*?{re.escape(self.MANAGED_END)}\n",
            re.MULTILINE | re.DOTALL
        )
        
        # 移除所有管理的server块
        cleansed_content = managed_pattern.sub("", content)
        
        logger.info("Removed managed server blocks from config")
        
        return cleansed_content
    
    def build_managed_site_block(self, site: SiteConfigBase, config_generator) -> str:
        """
        构建标记为管理的server块
        
        Args:
            site: 站点配置对象
            config_generator: 配置生成器实例
            
        Returns:
            带有管理标记的server块
        """
        # 生成标准的server配置
        server_config = config_generator.generate_config(site)
        
        # 添加管理标记
        marked_config = []
        marked_config.append(self.MANAGED_START)
        marked_config.append(f"{self.MANAGED_MARKER}: {site.site_name}")
        marked_config.append(server_config)
        marked_config.append(self.MANAGED_END)
        marked_config.append("")  # 添加空行
        
        return "\n".join(marked_config)
    
    def update_config(self, sites: List[SiteConfigBase], config_path: Optional[Path] = None, 
                     config_generator=None) -> bool:
        """
        更新配置文件 - 增量更新，保留其他配置
        
        Args:
            sites: 站点配置列表
            config_path: 配置文件路径（可选）
            config_generator: 配置生成器实例
            
        Returns:
            是否成功
        """
        try:
            if config_path is None:
                config_path = self.config_path
            
            if config_path is None:
                logger.error("No config path specified")
                return False
            
            if config_generator is None:
                logger.error("Config generator required")
                return False
            
            # 1. 加载原始配置
            original_content = self.load_original_config(config_path)
            
            # 2. 移除之前管理的server块
            cleansed_content = self.extract_managed_sites(original_content)
            
            # 3. 确保配置末尾有换行符
            if not cleansed_content.endswith("\n"):
                cleansed_content += "\n"
            
            # 4. 构建新的管理server块
            managed_blocks = []
            for site in sites:
                managed_block = self.build_managed_site_block(site, config_generator)
                managed_blocks.append(managed_block)
            
            # 5. 找出插入位置（在http块内的合适位置）
            # 如果没有http块，创建默认的
            if "http {" not in cleansed_content:
                logger.warning("No http block found, creating default")
                new_config = self._create_config_with_http_block(cleansed_content, managed_blocks)
            else:
                # 在http块内插入管理的server块
                new_config = self._insert_managed_blocks(cleansed_content, managed_blocks)
            
            # 6. 创建备份
            backup_path = self.backup_config(config_path)
            if backup_path:
                logger.info(f"Backup created: {backup_path}")
            
            # 7. 写入新配置
            config_path.write_text(new_config, encoding="utf-8")
            
            logger.info(f"Config updated successfully: {config_path}")
            logger.info(f"Managed sites: {len(sites)}")
            
            return True
            
        except Exception as e:
            logger.exception(f"Failed to update config: {e}")
            return False
    
    def _insert_managed_blocks(self, content: str, managed_blocks: List[str]) -> str:
        """
        在http块内插入管理的server块
        
        Args:
            content: 清洗后的配置内容
            managed_blocks: 管理的server块列表
            
        Returns:
            完整的配置内容
        """
        # 查找http块的最后一个}之前
        # 策略：在http块内的最后位置插入server块
        
        lines = content.splitlines()
        http_block_start = -1
        http_block_end = -1
        
        # 查找http块的开始和结束
        depth = 0
        in_http = False
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            if stripped.startswith("http {"):
                in_http = True
                http_block_start = i
                depth = 1
                continue
            
            if in_http:
                if "{" in stripped and not stripped.startswith("#"):
                    depth += stripped.count("{")
                if "}" in stripped and not stripped.startswith("#"):
                    depth -= stripped.count("}")
                
                if depth == 0:
                    http_block_end = i
                    break
        
        # 如果找到http块，在最后插入server块
        if http_block_start >= 0 and http_block_end > http_block_start:
            # 在http块结束前插入server块
            new_lines = []
            new_lines.extend(lines[:http_block_end])
            
            # 添加空行
            new_lines.append("")
            
            # 添加管理的server块
            for block in managed_blocks:
                block_lines = block.splitlines()
                for line in block_lines:
                    # 保持原有缩进
                    new_lines.append(line)
            
            # 添加http块结束
            new_lines.extend(lines[http_block_end:])
            
            return "\n".join(new_lines)
        else:
            # 如果没有找到http块，创建默认的
            logger.warning("Could not find proper http block location")
            
            # 在文件末尾添加http块
            new_content = content
            if not new_content.endswith("\n"):
                new_content += "\n"
            
            new_content += "\nhttp {\n"
            new_content += "    include mime.types;\n"
            new_content += "    default_type application/octet-stream;\n"
            new_content += "\n"
            
            # 添加管理的server块
            for block in managed_blocks:
                block_lines = block.splitlines()
                for line in block_lines:
                    if line.strip():
                        new_content += f"    {line}\n"
                    else:
                        new_content += "\n"
            
            new_content += "}\n"
            return new_content
    
    def _create_config_with_http_block(self, content: str, managed_blocks: List[str]) -> str:
        """
        创建包含http块的完整配置
        
        Args:
            content: 原始配置内容
            managed_blocks: 管理的server块列表
            
        Returns:
            完整的配置内容
        """
        new_content = content
        if not new_content.endswith("\n"):
            new_content += "\n"
        
        new_content += "\nhttp {\n"
        new_content += "    include mime.types;\n"
        new_content += "    default_type application/octet-stream;\n"
        new_content += "\n"
        
        # 添加管理的server块
        for block in managed_blocks:
            block_lines = block.splitlines()
            for line in block_lines:
                if line.strip():
                    new_content += f"    {line}\n"
                else:
                    new_content += "\n"
        
        new_content += "}\n"
        return new_content
    
    def parse_managed_sites(self, content: str, config_parser) -> List[SiteConfigBase]:
        """
        解析标记为管理的server块
        
        Args:
            content: 配置内容
            config_parser: 配置解析器实例
            
        Returns:
            管理的站点配置列表
        """
        sites = []
        
        # 查找所有被标记的部分
        managed_pattern = re.compile(
            rf"{re.escape(self.MANAGED_START)}.*?\n({self.MANAGED_MARKER}: (\w+).*?\n)(server\s*{{[^}}]*(?:{{[^}}]*}}[^}}]*)*}})\n{re.escape(self.MANAGED_END)}",
            re.MULTILINE | re.DOTALL
        )
        
        for match in managed_pattern.finditer(content):
            server_block = match.group(3)
            site = config_parser._parse_server_block(server_block)
            if site:
                sites.append(site)
        
        logger.info(f"Parsed {len(sites)} managed sites from config")
        return sites
    
    def backup_config(self, config_path: Optional[Path] = None) -> Optional[Path]:
        """
        备份配置文件
        
        Args:
            config_path: 配置文件路径（可选）
            
        Returns:
            备份文件路径
        """
        if config_path is None:
            config_path = self.config_path
        
        if config_path is None or not config_path.exists():
            logger.error(f"Config file not found: {config_path}")
            return None
        
        try:
            from datetime import datetime
            
            backup_dir = config_path.parent / "backups"
            backup_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{config_path.stem}_{timestamp}.conf.bak"
            backup_path = backup_dir / backup_name
            
            content = read_file_robust(config_path)
            if content is None:
                logger.error(f"无法读取配置文件进行备份: {config_path}")
                return None
            backup_path.write_text(content, encoding="utf-8")
            
            logger.info(f"Config backup created: {backup_path}")
            return backup_path
            
        except Exception as e:
            logger.exception(f"Failed to backup config: {e}")
            return None
    
    def _create_default_config(self) -> str:
        """
        创建默认的nginx配置
        
        Returns:
            默认配置内容
        """
        return '''# Nginx Default Configuration
# Generated by easyNginx

events {
    worker_connections 1024;
}

http {
    include mime.types;
    default_type application/octet-stream;
    
    # Default server
    server {
        listen 80;
        server_name localhost;
        root html;
        index index.html;
    }
}
'''
