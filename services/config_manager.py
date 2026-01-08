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
        提取由我们管理的配置部分，保留其他配置（包括默认server占位块）
        
        Args:
            content: 完整配置内容
            
        Returns:
            去除管理server块后的配置内容（保留默认server占位块）
        """
        # 查找所有被标记的管理server块
        managed_pattern = re.compile(
            rf"{re.escape(self.MANAGED_START)}.*?{re.escape(self.MANAGED_END)}\n",
            re.MULTILINE | re.DOTALL
        )
        
        # 移除所有管理的server块
        cleansed_content = managed_pattern.sub("", content)
        
        # 移除可能产生的多余空行
        cleansed_content = re.sub(r'\n\s*\n\s*\n', '\n\n', cleansed_content)
        
        logger.info("Removed managed server blocks from config, kept default server placeholder")
        
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
    
    def ensure_default_server(self, content: str) -> str:
        """
        确保配置中包含默认的server占位块
        
        Args:
            content: 配置文件内容
            
        Returns:
            包含默认server占位块的配置内容
        """
        # 检查是否已包含默认server占位块
        # 搜索listen指令中包含default_server的server块
        default_server_pattern = re.compile(
            r'server\s*{[^}]*listen[^;]*default_server[^;]*;[^}]*server_name\s+_;[^}]*}',
            re.MULTILINE | re.DOTALL
        )
        
        if default_server_pattern.search(content):
            logger.info("Default server placeholder already exists")
            return content
        
        # 查找http块
        http_pattern = re.compile(r'(http\s*{[^}]*?)(?=\n\s*server\s*{|\n\s*#.*Default Server|$)', re.MULTILINE | re.DOTALL)
        http_match = http_pattern.search(content)
        
        default_server_block = '''\n    # Default Server (Placeholder - can be replaced by actual sites)\n    server {\n        listen 80 default_server;\n        server_name _;\n        \n        location / {\n            root html;\n            index index.html index.htm;\n        }\n        \n        error_page 500 502 503 504 /50x.html;\n        location = /50x.html {\n            root html;\n        }\n    }\n'''
        
        if http_match:
            # 在http块内插入默认server块
            insert_pos = http_match.end()
            content = content[:insert_pos] + default_server_block + content[insert_pos:]
            logger.info("Added default server placeholder to http block")
        else:
            # 如果没有找到合适的插入位置，在文件末尾添加
            content += '\nhttp {\n    include mime.types;\n    default_type application/octet-stream;' + default_server_block + '}\n'
            logger.info("Added http block with default server placeholder")
        
        return content
    
    def update_config(self, sites: List[SiteConfigBase], config_path: Optional[Path] = None, 
                     config_generator=None) -> bool:
        """
        更新配置文件 - 增量更新，保留其他配置（包括默认server占位块）
        
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
            
            # 6. 确保包含默认server占位块
            new_config = self.ensure_default_server(new_config)
            
            # 7. 创建备份
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
        
        策略：找到http块的正确结束位置，并在http块结束前插入server块
        
        Args:
            content: 清洗后的配置内容（已移除管理的server块）
            managed_blocks: 管理的server块列表
            
        Returns:
            完整的配置内容
        """
        lines = content.splitlines()
        http_block_start = -1
        http_block_end = -1
        
        # 查找http块的开始
        for i, line in enumerate(lines):
            if line.strip().startswith("http {"):
                http_block_start = i
                break
        
        if http_block_start == -1:
            # 没有找到http块，创建新的
            logger.warning("No http block found, creating one")
            return self._create_config_with_http_block(content, managed_blocks)
        
        # 从http块开始，找到对应的结束位置
        depth = 0
        in_http = False
        brace_count = 0
        
        for i in range(len(lines)):
            line = lines[i]
            stripped = line.strip()
            
            # Skip comments and empty lines for brace counting
            if not stripped or stripped.startswith("#"):
                continue
                
            if i == http_block_start:
                in_http = True
                # Count braces in the http line
                brace_count += line.count("{")
                continue
            
            if in_http:
                # Count opening braces
                brace_count += line.count("{")
                # Count closing braces
                brace_count -= line.count("}")
                
                # If brace count returns to 0, we found the end of http block
                if brace_count == 0 and i > http_block_start:
                    http_block_end = i
                    break
        
        # 如果找到http块的结束位置，在该位置之前插入server块
        if http_block_start >= 0 and http_block_end > http_block_start:
            logger.info(f"Found http block: start={http_block_start}, end={http_block_end}")
            
            # 构建新的配置内容
            new_lines = []
            # 添加http块开始到结束前的所有内容
            new_lines.extend(lines[:http_block_end])
            
            # 添加空行分隔
            if new_lines and new_lines[-1].strip():
                new_lines.append("")
            
            # 添加管理的server块
            for block in managed_blocks:
                block_lines = block.splitlines()
                for line in block_lines:
                    new_lines.append(line)
            
            # 添加http块结束以及剩余内容
            new_lines.extend(lines[http_block_end:])
            
            result = "\n".join(new_lines)
            logger.info("Successfully inserted managed server blocks into http block")
            return result
        else:
            # 没有找到正确的http块结束位置
            logger.warning("Could not find proper http block end, creating new http block")
            return self._create_config_with_http_block(content, managed_blocks)
    
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
