"""
Nginx Configuration Manager - 配置管理器

核心职责（变更后）：
1. 所有site块均可管理，无需区分
2. 直接重写所有server块，不再使用标记
3. 保留用户的其他非server配置（events, http设置等）
4. 支持include文件的读取和写入
5. 使用随机数命名的站点配置目录（如: J43R8_conf.d/）
"""

import re
from pathlib import Path
from typing import List, Optional, Dict, Any
from loguru import logger
from models.site_config import SiteConfigBase
from utils.encoding_utils import read_file_robust


class ConfigManager:
    """配置管理器 - 所有server块都可管理，无需标记"""
    
    def __init__(self, config_path: Optional[Path] = None, config_registry=None):
        """初始化配置管理器."""
        self.config_path = config_path
        self.config_registry = config_registry
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
    
    def _remove_all_server_blocks(self, content: str) -> str:
        """
        移除所有server块，保留其他配置
        
        Args:
            content: 配置内容
            
        Returns:
            移除server块后的内容
        """
        # 使用更精确的模式匹配server块
        # 匹配 server { ... } 结构，使用栈来正确处理嵌套
        
        result = []
        i = 0
        depth = 0
        in_server = False
        server_start = -1
        
        while i < len(content):
            # 查找server关键字
            if content[i:].startswith("server") and (i + 6 >= len(content) or content[i+6] in " {\t\n"):
                # 确认是server块开始
                next_pos = i + 6
                while next_pos < len(content) and content[next_pos] in " \t":
                    next_pos += 1
                
                if next_pos < len(content) and content[next_pos] == "{":
                    # 找到server块开始
                    if depth == 0:
                        in_server = True
                        server_start = i
                    depth += 1
                    i = next_pos + 1
                    continue
            
            # 处理大括号计数
            if content[i] == "{" and not in_server:
                depth += 1
            elif content[i] == "}" and not in_server:
                depth -= 1
            elif content[i] == "{" and in_server:
                depth += 1
            elif content[i] == "}" and in_server:
                depth -= 1
                if depth == 0:
                    # server块结束
                    in_server = False
                    # 跳过这个server块（不添加到结果）
                    i += 1
                    continue
            
            # 如果不在server块内，添加到结果
            if not in_server:
                result.append(content[i])
            
            i += 1
        
        cleaned_content = "".join(result)
        
        # 移除可能产生的多余空行
        cleaned_content = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned_content)
        
        logger.info("Removed all server blocks from config")
        
        return cleaned_content
    
    def _build_server_block(self, site: SiteConfigBase, config_generator) -> str:
        """
        构建server块（不再添加管理标记）
        
        Args:
            site: 站点配置对象
            config_generator: 配置生成器实例
            
        Returns:
            标准的server块
        """
        # 生成标准的server配置（不添加管理标记）
        server_config = config_generator.generate_config(site)
        
        # 添加空行分隔
        return server_config + "\n\n"
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
        确保配置中包含完整的默认server块（已禁用）
        
        注意：此方法已禁用，不再自动添加default server。
        如果配置中没有server块，Nginx启动时将正常报错，
        由用户自行创建server块。
        
        Args:
            content: 配置文件内容
            
        Returns:
            原始配置内容（不做修改）
        """
        logger.info("ensure_default_server is disabled, not adding default server block")
        return content
    
    def _get_site_conf_dir(self, config_path: Optional[Path] = None) -> Path:
        """
        获取站点配置目录路径（使用随机数命名）
        
        Args:
            config_path: 配置文件路径（可选）
            
        Returns:
            站点配置目录路径
        """
        if config_path is None:
            config_path = self.config_path
        
        if config_path is None:
            raise ValueError("Config path not specified")
        
        # 获取conf目录
        conf_dir = config_path.parent
        
        # 如果设置了config_registry，使用其中的随机数
        if self.config_registry is not None:
            try:
                return self.config_registry.get_site_conf_dir(conf_dir)
            except Exception as e:
                logger.warning(f"Failed to get site conf dir from registry: {e}")
                # 回退到默认值
                return conf_dir / "EN000_conf.d"
        else:
            # 如果没有config_registry，使用默认值
            logger.warning("ConfigRegistry not set, using default site conf dir: EN000_conf.d")
            return conf_dir / "EN000_conf.d"
    
    def update_config(self, sites: List[SiteConfigBase], config_path: Optional[Path] = None, 
                     config_generator=None) -> bool:
        """
        更新配置文件 - 将站点配置保存为独立文件到conf.d目录
        
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
            
            # 1. 创建备份
            backup_path = self.backup_config(config_path)
            if backup_path:
                logger.info(f"Main config backup created: {backup_path}")
            
            # 2. 确保主配置包含正确的include语句
            # 注意：现在使用随机数命名的目录，include指令已由接管时生成
            # self._ensure_include_directive(config_path)
            
            # 3. 确保站点配置目录存在（使用随机数命名）
            site_conf_dir = self._get_site_conf_dir(config_path)
            site_conf_dir.mkdir(exist_ok=True)
            logger.info(f"Using site config directory: {site_conf_dir}")
            
            # 4. 将每个站点配置保存为独立文件
            saved_files = []
            for site in sites:
                site_config_content = config_generator.generate_config(site)
                site_file = site_conf_dir / f"{site.site_name}.conf"
                
                # 备份已存在的站点配置文件
                if site_file.exists():
                    self._backup_site_config(site_file)
                
                # 写入新的站点配置
                site_file.write_text(site_config_content, encoding="utf-8")
                saved_files.append(site_file.name)
                
                logger.info(f"Site config saved: {site_file}")
            
            # 5. 清理站点配置目录中不再使用的配置文件（可选）
            # 保留不在当前站点列表中的配置文件
            current_site_files = {f"{site.site_name}.conf" for site in sites}
            for conf_file in site_conf_dir.glob("*.conf"):
                if conf_file.name not in current_site_files:
                    # 备份并删除旧配置文件
                    self._backup_site_config(conf_file)
                    conf_file.unlink()
                    logger.info(f"Removed obsolete site config: {conf_file}")
            
            logger.info(f"Config updated successfully. Total sites: {len(sites)}")
            logger.info(f"Site configs saved to: {site_conf_dir}")
            logger.info(f"Saved files: {saved_files}")
            
            return True
            
        except Exception as e:
            logger.exception(f"Failed to update config: {e}")
            return False
    
    def _insert_server_blocks(self, content: str, server_blocks: List[str]) -> str:
        """
        在http块内插入所有server块（重命名自 _insert_managed_blocks）
        
        Args:
            content: 清洗后的配置内容（已移除所有server块）
            server_blocks: 所有server块列表
            
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
            return self._create_config_with_http_block(content, server_blocks)
        
        # 从http块开始，找到对应的结束位置
        brace_count = 0
        
        for i in range(len(lines)):
            line = lines[i]
            stripped = line.strip()
            
            # Skip comments and empty lines for brace counting
            if not stripped or stripped.startswith("#"):
                continue
                
            if i == http_block_start:
                # Count braces in the http line
                brace_count += line.count("{")
                continue
            
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
            
            # 添加所有server块
            for block in server_blocks:
                block_lines = block.splitlines()
                for line in block_lines:
                    new_lines.append(line)
            
            # 添加http块结束以及剩余内容
            new_lines.extend(lines[http_block_end:])
            
            result = "\n".join(new_lines)
            logger.info(f"Successfully inserted {len(server_blocks)} server blocks into http block")
            return result
        else:
            # 没有找到正确的http块结束位置
            logger.warning("Could not find proper http block end, creating new http block")
            return self._create_config_with_http_block(content, server_blocks)
    
    def _create_config_with_http_block(self, content: str, server_blocks: List[str]) -> str:
        """
        创建包含http块的完整配置
        
        Args:
            content: 原始配置内容
            server_blocks: 所有server块列表
            
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
        
        # 添加所有server块
        for block in server_blocks:
            block_lines = block.splitlines()
            for line in block_lines:
                if line.strip():
                    new_content += f"    {line}\n"
                else:
                    new_content += "\n"
        
        new_content += "}\n"
        return new_content
    
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
    
    def _ensure_include_directive(self, config_path: Path):
        """
        确保主配置文件中包含正确的include语句
        
        Args:
            config_path: 主配置文件路径
        """
        try:
            if not config_path.exists():
                logger.error(f"Config file not found: {config_path}")
                return
            
            content = read_file_robust(config_path)
            if content is None:
                logger.error(f"无法读取配置文件: {config_path}")
                return
            
            # 检查是否已包含include语句
            include_pattern = re.compile(r'include\s+conf\.d/\*\.conf\s*;', re.MULTILINE)
            
            if not include_pattern.search(content):
                logger.info("Include directive not found, adding it to http block")
                
                # 如果找到http块，在http块内添加include语句
                if 'http {' in content:
                    # 在http块开始后找到插入位置
                    lines = content.splitlines()
                    new_lines = []
                    in_http = False
                    brace_depth = 0
                    include_added = False
                    
                    for line in lines:
                        new_lines.append(line)
                        
                        # 检测http块
                        stripped_line = line.strip()
                        if stripped_line.startswith('http') and '{' in line:
                            in_http = True
                            # 统计当前行的括号深度
                            brace_depth = line.count('{') - line.count('}')
                        elif in_http and not include_added:
                            # 更新括号深度
                            brace_depth += line.count('{') - line.count('}')
                            
                            # 如果括号深度为0，说明http块结束
                            if brace_depth <= 0 and '}' in line:
                                # 在http块结束前插入include语句
                                indent = '    '
                                new_lines.insert(-1, f'{indent}# Include site configurations managed by easyNginx')
                                new_lines.insert(-1, f'{indent}include conf.d/*.conf;')
                                include_added = True
                            # 如果找到了http块的第一行非注释、非空行，并且还没添加include
                            elif (brace_depth > 0 and stripped_line and 
                                  not stripped_line.startswith('#') and 
                                  not stripped_line.startswith('http')):
                                indent = '    '
                                new_lines.insert(-1, f'{indent}# Include site configurations managed by easyNginx')
                                new_lines.insert(-1, f'{indent}include conf.d/*.conf;')
                                new_lines.append('')
                                include_added = True
                    
                    content = '\n'.join(new_lines)
                else:
                    # 如果没有http块，创建一个包含include的http块
                    content += '''
http {
    include mime.types;
    default_type application/octet-stream;
    
    # Include site configurations managed by easyNginx
    include conf.d/*.conf;
}
'''
                
                # 创建主配置备份
                backup_path = self.backup_config(config_path)
                if backup_path:
                    logger.info(f"Backup created before updating include directive: {backup_path}")
                
                # 写入更新后的配置
                config_path.write_text(content, encoding="utf-8")
                logger.info("Added include directive to main config file")
            else:
                logger.info("Include directive already exists in config")
                
        except Exception as e:
            logger.exception(f"Failed to ensure include directive: {e}")
    
    def delete_site_config(self, site_name: str, config_path: Optional[Path] = None) -> bool:
        """
        删除指定站点的配置文件
        
        Args:
            site_name: 站点名称
            config_path: Nginx主配置文件路径（可选）
            
        Returns:
            是否成功删除
        """
        try:
            if config_path is None:
                config_path = self.config_path
            
            if config_path is None:
                logger.error("No config path specified")
                return False
            
            # 获取站点配置目录
            site_conf_dir = self._get_site_conf_dir(config_path)
            
            if not site_conf_dir.exists():
                logger.warning(f"Site config directory not found: {site_conf_dir}")
                return False
            
            # 构建站点配置文件路径
            site_config_file = site_conf_dir / f"{site_name}.conf"
            
            if not site_config_file.exists():
                logger.warning(f"Site config file not found: {site_config_file}")
                return False
            
            # 备份站点配置文件
            backup_path = self._backup_site_config(site_config_file)
            if backup_path:
                logger.info(f"Site config backup created before deletion: {backup_path}")
            
            # 删除配置文件
            site_config_file.unlink()
            logger.info(f"Deleted site config file: {site_config_file}")
            
            return True
            
        except Exception as e:
            logger.exception(f"Failed to delete site config for '{site_name}': {e}")
            return False
    
    def _backup_site_config(self, site_file: Path) -> Optional[Path]:
        """
        备份站点配置文件
        
        Args:
            site_file: 站点配置文件路径
            
        Returns:
            备份文件路径或None
        """
        try:
            if not site_file.exists():
                return None
            
            from datetime import datetime
            
            backup_dir = site_file.parent / "backups"
            backup_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{site_file.stem}_{timestamp}.conf.bak"
            backup_path = backup_dir / backup_name
            
            content = read_file_robust(site_file)
            if content is None:
                logger.error(f"无法读取站点配置文件进行备份: {site_file}")
                return None
            
            backup_path.write_text(content, encoding="utf-8")
            
            logger.info(f"Site config backup created: {backup_path}")
            return backup_path
            
        except Exception as e:
            logger.exception(f"Failed to backup site config {site_file}: {e}")
            return None
    
    def _create_default_config(self) -> str:
        """
        创建默认的nginx配置（不包含站点信息）
        
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
    
    # Include site configurations managed by easyNginx
    include conf.d/*.conf;
}
'''
