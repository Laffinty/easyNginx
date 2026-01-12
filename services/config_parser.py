#!/usr/bin/env python3
"""Nginx configuration file parser."""

import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from loguru import logger
from models.site_config import (
    SiteConfigBase, StaticSiteConfig, PHPSiteConfig, ProxySiteConfig,
    SITE_CONFIG_TYPES
)
from models.nginx_status import SiteListItem
from utils.encoding_utils import read_file_robust


class ConfigParser:
    """Nginx配置文件解析器."""
    
    def __init__(self):
        """初始化配置解析器."""
        self.server_block_pattern = re.compile(
            r'(server\s*{[^}]*(?:{[^}]*}[^}]*)*})',
            re.MULTILINE | re.DOTALL
        )
        self.directive_pattern = re.compile(
            r'(\w+)\s+(.+?)(?=\s*;|\s*\{)',
            re.MULTILINE | re.DOTALL
        )
        # 注意：这个简单的正则表达式不能正确处理嵌套的大括号
        # location解析现在使用手动方法，见 _extract_locations 方法
    
    def _extract_server_blocks(self, content: str) -> List[str]:
        """
        提取所有server块内容（使用手动方法，更可靠）
        
        Args:
            content: 配置内容
            
        Returns:
            server块内容列表
        """
        blocks = []
        pos = 0
        
        while pos < len(content):
            # 查找server关键字
            server_pos = content.find('server', pos)
            if server_pos == -1:
                break
            
            # 确认是server块开始（后面是空格或{）
            next_char_pos = server_pos + 6
            if next_char_pos < len(content):
                next_char = content[next_char_pos]
                if next_char.isspace() or next_char == '{':
                    # 找到server块开始
                    bracket_pos = content.find('{', server_pos)
                    if bracket_pos != -1:
                        # 使用栈来查找匹配的结束括号
                        depth = 1
                        search_pos = bracket_pos + 1
                        while search_pos < len(content) and depth > 0:
                            if content[search_pos] == '{':
                                depth += 1
                            elif content[search_pos] == '}':
                                depth -= 1
                            search_pos += 1
                        
                        if depth == 0:
                            # 提取完整的server块
                            block = content[server_pos:search_pos]
                            blocks.append(block)
                            pos = search_pos
                            continue
            
            # 如果没找到，继续搜索下一个位置
            pos = server_pos + 6
        
        return blocks
    
    def _extract_locations(self, server_block: str) -> List[Dict[str, str]]:
        """
        手动提取location块（处理嵌套大括号）
        
        Args:
            server_block: server块内容
            
        Returns:
            location块列表，每个元素包含path和body
        """
        locations = []
        pos = 0
        
        while pos < len(server_block):
            # 查找location关键字
            loc_pos = server_block.find('location', pos)
            if loc_pos == -1:
                break
            
            # 确认是location块开始（后面是空格或{）
            next_char_pos = loc_pos + 8
            if next_char_pos < len(server_block):
                next_char = server_block[next_char_pos]
                if next_char.isspace() or next_char == '{':
                    # 提取location路径
                    path_start = loc_pos + 8
                    path_end = server_block.find('{', path_start)
                    if path_end != -1:
                        location_path = server_block[path_start:path_end].strip()
                        
                        # 找到location块开始
                        bracket_pos = path_end
                        depth = 1
                        search_pos = bracket_pos + 1
                        
                        # 查找匹配的结束括号
                        while search_pos < len(server_block) and depth > 0:
                            if server_block[search_pos] == '{':
                                depth += 1
                            elif server_block[search_pos] == '}':
                                depth -= 1
                            search_pos += 1
                        
                        if depth == 0:
                            # 提取完整的location块
                            location_body = server_block[bracket_pos+1:search_pos-1]
                            locations.append({
                                "path": location_path,
                                "body": location_body
                            })
                            pos = search_pos
                            continue
            
            # 如果没找到，继续搜索下一个位置
            pos = loc_pos + 8
        
        return locations
    
    def parse_config_file(self, config_path: Path, config_registry=None) -> List[SiteConfigBase]:
        """
        解析nginx.conf文件和站点配置目录中的所有配置文件
        
        Args:
            config_path: 主配置文件路径(nginx.conf)
            config_registry: 注册表管理器实例（可选），用于获取随机数命名的目录
            
        Returns:
            站点配置对象列表
        """
        if not config_path.exists():
            logger.error(f"Config file not found: {config_path}")
            return []
        
        all_sites = []
        
        try:
            # 1. 解析主配置文件
            main_content = read_file_robust(config_path)
            if main_content is None:
                logger.error(f"无法读取主配置文件: {config_path}")
            else:
                logger.debug(f"Parsing main config: {config_path} (size: {len(main_content)} bytes)")
                main_sites = self.parse_config_content(main_content)
                all_sites.extend(main_sites)
                logger.info(f"[OK] Parsed {len(main_sites)} sites from main config")
            
            # 2. 解析站点配置目录中的所有配置文件
            # 首先尝试从注册表获取随机数命名的目录
            site_conf_dir = None
            
            if config_registry is not None:
                try:
                    site_conf_dir = config_registry.get_site_conf_dir(config_path.parent)
                    logger.info(f"Using site config directory from registry: {site_conf_dir}")
                except Exception as e:
                    logger.warning(f"Failed to get site conf dir from registry: {e}")
            
            # 如果无法从注册表获取，回退到默认的conf.d
            if site_conf_dir is None or not site_conf_dir.exists():
                site_conf_dir = config_path.parent / "conf.d"
                logger.info(f"Falling back to default site config directory: {site_conf_dir}")
            
            # 检查站点配置目录是否存在
            if site_conf_dir.exists() and site_conf_dir.is_dir():
                conf_files = list(site_conf_dir.glob("*.conf"))
                
                if conf_files:
                    for conf_file in conf_files:
                        try:
                            conf_content = read_file_robust(conf_file)
                            if conf_content is None:
                                logger.error(f"无法读取站点配置文件: {conf_file}")
                                continue
                            
                            logger.debug(f"Parsing site config: {conf_file} (size: {len(conf_content)} bytes)")
                            conf_sites = self.parse_config_content(conf_content, source_filename=conf_file.name)
                            all_sites.extend(conf_sites)
                            logger.info(f"[OK] Parsed {len(conf_sites)} sites from {conf_file.name}")
                            
                        except Exception as e:
                            logger.warning(f"Failed to parse site config {conf_file}: {e}")
                            continue
                else:
                    logger.info(f"No .conf files found in {site_conf_dir}")
            else:
                logger.info(f"Site config directory not found: {site_conf_dir}")
            
            logger.info(f"[OK] Total parsed {len(all_sites)} sites from all config files")
            return all_sites
            
        except Exception as e:
            logger.exception(f"Failed to parse config files: {e}")
            return all_sites  # 返回已解析的站点，不要完全失败
    
    def parse_config_content(self, content: str, source_filename: Optional[str] = None) -> List[SiteConfigBase]:
        """
        解析配置内容
        
        Args:
            content: 配置内容
            source_filename: 源文件名（可选），用于从文件名提取站点名称
            
        Returns:
            站点配置对象列表
        """
        sites = []
        
        # 查找所有server块（使用更可靠的手动提取方法）
        server_blocks = self._extract_server_blocks(content)
        
        for i, server_block in enumerate(server_blocks):
            try:
                site_config = self._parse_server_block(server_block, source_filename)
                if site_config:
                    sites.append(site_config)
            except Exception as e:
                logger.warning(f"Failed to parse server block {i}: {e}")
                continue
        
        return sites
    
    def _parse_server_block(self, server_block: str, source_filename: Optional[str] = None) -> Optional[SiteConfigBase]:
        """
        解析单个server块，增强健壮性和错误处理
        
        Args:
            server_block: server块内容
            source_filename: 源文件名（可选），用于从文件名提取站点名称
            
        Returns:
            站点配置对象或None
        """
        try:
            logger.debug("Parsing server block...")
            
            # 清理注释（以#开头的行），避免中文字符干扰正则表达式
            # 只删除纯粹的注释行（不以nginx指令开头）和空行
            lines = server_block.split('\n')
            cleaned_lines = []
            for line in lines:
                stripped = line.strip()
                # 如果是纯粹注释行（以#开头）或是空行，跳过
                if stripped.startswith('#') or len(stripped) == 0:
                    continue
                # 检查是否是包含nginx指令的行（不以#开头，且有内容）
                # 如果该行有实际内容（不只是注释），保留
                cleaned_lines.append(line)
            
            server_block_clean = '\n'.join(cleaned_lines)
            
            # 移除server块的开始标记（server {）以避免干扰指令提取
            server_block_clean = re.sub(r'^\s*server\s*\{', '', server_block_clean, flags=re.MULTILINE)
            
            # 先提取location块（从server块中移除它们，避免干扰指令提取）
            server_block_for_directives = server_block_clean
            locations = self._extract_locations(server_block_clean)
            
            logger.debug(f"Extracted {len(locations)} location blocks")
            
            # 从server块中移除location块，避免干扰其他指令的提取
            for loc in locations:
                # 重建完整的location块文本以进行替换
                loc_text = f"location {loc['path']} {{{loc['body']}}}"
                server_block_for_directives = server_block_for_directives.replace(loc_text, '')
            
            # 提取所有指令（跳过server指令本身）
            directives = {}
            for match in self.directive_pattern.finditer(server_block_for_directives):
                key = match.group(1)
                value = match.group(2).strip()
                logger.debug(f"Found directive: {key} = {repr(value)}")
                # 跳过server指令（server块的开始标记）
                if key == 'server':
                    logger.debug("Skipping 'server' directive")
                    continue
                directives[key] = value
            
            logger.debug(f"Extracted {len(directives)} directives")
            
            # Location blocks were already extracted above
            
            # 检查是否是80端口重定向server块（应该跳过，不解析为独立站点）
            # 重定向server块的特征是：包含return 301/302到https，且没有实际内容
            if self._is_redirect_server_block(directives, locations):
                logger.debug("Skipping redirect server block (not a real site)")
                return None
            
            # 检测站点类型
            site_type = self._detect_site_type(directives, locations)
            logger.debug(f"Detected site type: {site_type}")
            
            # 构建基础配置
            # 尝试从文件名提取站点名称，如果失败则根据内容生成
            site_name_from_file = self._extract_site_name_from_filename(source_filename)
            base_config = {
                "site_name": site_name_from_file or self._generate_site_name(directives),
                "listen_port": self._parse_listen_port(directives.get("listen", "80")),
                "server_name": self._parse_server_name(directives.get("server_name", "localhost")),
                "enable_https": "ssl" in directives.get("listen", ""),
                "ssl_cert_path": directives.get("ssl_certificate", "").strip('"\'') if directives.get("ssl_certificate") else None,
                "ssl_key_path": directives.get("ssl_certificate_key", "").strip('"\'') if directives.get("ssl_certificate_key") else None
            }
            
            # 检查是否启用了80端口重定向（从注释中读取）
            base_config["enable_http_redirect"] = self._check_http_redirect_enabled(server_block)
            
            logger.debug(f"Base config: {base_config}")
            
            # 根据类型创建特定配置
            if site_type == "static":
                config = self._build_static_config(base_config, directives)
            elif site_type == "php":
                config = self._build_php_config(base_config, directives, locations)
            elif site_type == "proxy":
                config = self._build_proxy_config(base_config, directives, locations)
            else:
                logger.warning(f"Unknown site type: {site_type}")
                return None
            
            if config:
                # 检查SSL文件是否存在（仅警告，不阻止加载）
                if config.get("enable_https"):
                    cert_path = config.get("ssl_cert_path")
                    key_path = config.get("ssl_key_path")
                    if cert_path:
                        cert_file = Path(cert_path)
                        if not cert_file.exists():
                            logger.warning(f"SSL certificate file not found: {cert_path}")
                    if key_path:
                        key_file = Path(key_path)
                        if not key_file.exists():
                            logger.warning(f"SSL key file not found: {key_path}")
                
                site_config = SITE_CONFIG_TYPES[site_type](**config)
                logger.info(f"[OK] Successfully parsed site: {config['site_name']} (type: {site_type})")
                return site_config
            else:
                logger.warning("Failed to build site configuration")
                return None
                
        except Exception as e:
            logger.exception(f"Error parsing server block: {e}")
            return None
    
    def _detect_site_type(self, directives: Dict[str, str], locations: List[Dict[str, str]]) -> str:
        """
        检测站点类型
        
        Args:
            directives: 指令字典
            locations: location块列表
            
        Returns:
            站点类型（static/php/proxy）
        """
        # 检查PHP相关配置
        for directive in directives:
            if "php" in directive.lower():
                return "php"
        
        for location in locations:
            if "fastcgi_pass" in location["body"].lower():
                return "php"
            if "proxy_pass" in location["body"].lower():
                return "proxy"
        
        # 检查是否有root指令（静态站点特征）
        if "root" in directives:
            return "static"
        
        # 默认返回static
        return "static"
    
    def _build_static_config(self, base_config: Dict[str, Any], directives: Dict[str, str]) -> Dict[str, Any]:
        """构建静态站点配置."""
        config = base_config.copy()
        config["site_type"] = "static"
        
        # 解析root路径
        if "root" in directives:
            root_path = directives["root"].strip('"\'')
            config["root_path"] = root_path
        else:
            config["root_path"] = "."
        
        # 解析index
        config["index_file"] = directives.get("index", "index.html")
        
        return config
    
    def _build_php_config(self, base_config: Dict[str, Any], directives: Dict[str, str], 
                         locations: List[Dict[str, str]]) -> Dict[str, Any]:
        """构建PHP站点配置."""
        config = base_config.copy()
        config["site_type"] = "php"
        
        # 解析root路径
        if "root" in directives:
            root_path = directives["root"].strip('"\'')
            config["root_path"] = root_path
        else:
            config["root_path"] = "."
        
        # 解析PHP-FPM配置
        php_fpm_found = False
        for location in locations:
            if "fastcgi_pass" in location["body"]:
                fastcgi_pass = self._extract_directive("fastcgi_pass", location["body"])
                if fastcgi_pass:
                    php_fpm_found = True
                    # 判断是Unix socket还是TCP
                    if fastcgi_pass.startswith("/"):  # Unix socket
                        config["php_fpm_mode"] = "unix"
                        config["php_fpm_socket"] = fastcgi_pass.strip('"\'')
                    elif fastcgi_pass.startswith("$") or ":" not in fastcgi_pass:
                        # 是变量（如$php_fpm）或格式不正确，尝试从set指令解析
                        # 查找server块中的set指令
                        set_php_fpm = directives.get("set", "")
                        if '$php_fpm' in set_php_fpm and '"' in set_php_fpm:
                            # 提取变量值
                            import re
                            var_match = re.search(r'\$php_fpm\s+"([^"]+)"', set_php_fpm)
                            if var_match:
                                actual_value = var_match.group(1)
                                if actual_value.startswith("/"):  # Unix socket
                                    config["php_fpm_mode"] = "unix"
                                    config["php_fpm_socket"] = actual_value
                                else:  # TCP
                                    config["php_fpm_mode"] = "tcp"
                                    if ":" in actual_value:
                                        host, port = actual_value.split(":")
                                        config["php_fpm_host"] = host
                                        config["php_fpm_port"] = int(port)
                                    else:
                                        # 默认值
                                        config["php_fpm_host"] = "127.0.0.1"
                                        config["php_fpm_port"] = 9000
                            else:
                                # 无法解析变量，使用默认值
                                config["php_fpm_mode"] = "tcp"
                                config["php_fpm_host"] = "127.0.0.1"
                                config["php_fpm_port"] = 9000
                        else:
                            # 无法解析，使用默认值
                            config["php_fpm_mode"] = "tcp"
                            config["php_fpm_host"] = "127.0.0.1"
                            config["php_fpm_port"] = 9000
                    else:  # TCP
                        config["php_fpm_mode"] = "tcp"
                        host, port = fastcgi_pass.split(":")
                        config["php_fpm_host"] = host.strip('"\'')
                        config["php_fpm_port"] = int(port)
                break
        
        if not php_fpm_found:
            # 使用默认值
            config["php_fpm_mode"] = "unix"
            config["php_fpm_socket"] = "/run/php/php-fpm.sock"
        
        return config
    
    def _build_proxy_config(self, base_config: Dict[str, Any], directives: Dict[str, str], 
                          locations: List[Dict[str, str]]) -> Dict[str, Any]:
        """构建反向代理配置."""
        config = base_config.copy()
        config["site_type"] = "proxy"
        
        # 解析proxy_pass
        proxy_pass_url = None
        location_path = "/"
        enable_websocket = False
        
        for location in locations:
            if "proxy_pass" in location["body"]:
                proxy_pass = self._extract_directive("proxy_pass", location["body"])
                if proxy_pass:
                    proxy_pass_url = proxy_pass.strip('"\'').rstrip("/")
                    location_path = location["path"].strip('"\'')
                    
                    # 检查WebSocket支持
                    if "Upgrade" in location["body"] or "upgrade" in location["body"]:
                        enable_websocket = True
                    break
        
        if not proxy_pass_url:
            proxy_pass_url = "http://localhost:8080"  # 默认值
        
        config["proxy_pass_url"] = proxy_pass_url
        config["location_path"] = location_path
        config["enable_websocket"] = enable_websocket
        
        return config
    
    def _is_redirect_server_block(self, directives: Dict[str, str], locations: List[Dict]) -> bool:
        """
        检测server块是否是HTTP到HTTPS的重定向块
        
        重定向块的特征：
        1. 包含 return 301/302 https://...
        2. 没有location块（或者location块也只是重定向）
        3. 没有root、proxy_pass等实际内容
        
        Args:
            directives: server块中的指令
            locations: location块列表
            
        Returns:
            是否是重定向server块
        """
        try:
            # 检查是否有return指令
            has_return = False
            for key, value in directives.items():
                if key == 'return' and ('https://' in value or '301' in value or '302' in value):
                    has_return = True
                    break
            
            # 如果没有return指令，不是重定向块
            if not has_return:
                return False
            
            # 检查是否有实际内容（root、proxy_pass等）
            has_content = False
            for key in directives.keys():
                if key in ['root', 'proxy_pass', 'fastcgi_pass']:
                    has_content = True
                    break
            
            # 如果有实际内容，不是重定向块
            if has_content:
                return False
            
            # 检查location块是否有实际内容
            for loc in locations:
                loc_body = loc.get('body', '')
                if any(keyword in loc_body for keyword in ['root', 'proxy_pass', 'fastcgi_pass']):
                    return False
            
            # 如果只有return指令且没有实际内容，认为是重定向块
            return True
            
        except Exception as e:
            logger.debug(f"Error checking redirect server block: {e}")
            return False
    
    def _check_http_redirect_enabled(self, server_block: str) -> bool:
        """
        检查server块是否启用了80端口重定向（从注释中读取）
        
        Args:
            server_block: server块完整内容
            
        Returns:
            是否启用了80端口重定向
        """
        try:
            # 查找 easyNginx 注释中的 "启用80端口重定向" 标记
            # 支持中文和英文
            for line in server_block.split('\n'):
                if '启用80端口重定向' in line and '是' in line:
                    return True
                if 'Enable 80 port redirect' in line and 'Yes' in line:
                    return True
            return False
        except Exception as e:
            logger.debug(f"Error checking http redirect flag from comments: {e}")
            return False
    
    def _generate_site_name(self, directives: Dict[str, str]) -> str:
        """生成站点名称."""
        server_name = directives.get("server_name", "localhost")
        listen_port = directives.get("listen", "80")
        
        # 从server_name提取第一个域名
        server_name = server_name.split()[0]
        
        # 生成站点名称
        return f"{server_name}_{listen_port}"
    
    def _parse_listen_port(self, listen_value: str) -> int:
        """解析监听端口."""
        # 移除SSL标记
        listen_value = listen_value.replace("ssl", "").strip()
        # 提取端口号
        parts = listen_value.split()
        for part in parts:
            if part.isdigit():
                return int(part)
        return 80
    
    def _parse_server_name(self, server_name_value: str) -> str:
        """解析server_name."""
        # 取第一个域名
        names = server_name_value.split()
        if names:
            return names[0].strip('"\'')
        return "localhost"
    
    def _extract_directive(self, directive_name: str, content: str) -> Optional[str]:
        """提取指令值."""
        pattern = re.compile(rf"{directive_name}\s+([^;]+);", re.IGNORECASE)
        match = pattern.search(content)
        if match:
            return match.group(1).strip()
        return None
    
    def _extract_site_name_from_filename(self, filename: Optional[str]) -> Optional[str]:
        """
        从文件名提取站点名称
        
        Args:
            filename: 文件名（如: testsite.conf）
            
        Returns:
            站点名称或None
        """
        if not filename:
            return None
        
        try:
            # 提取文件名（不含路径）
            filename_only = Path(filename).name
            
            # 如果是.conf文件，去掉扩展名作为站点名称
            if filename_only.endswith('.conf'):
                site_name = filename_only[:-5]  # 移除.conf
                return site_name
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to extract site name from filename '{filename}': {e}")
            return None
    
    def build_site_list(self, sites: List[SiteConfigBase]) -> List[SiteListItem]:
        """构建站点列表项 - 所有站点都被视为可管理的.
        
        Args:
            sites: 站点配置列表
        """
        items = []
        
        for site in sites:
            item = SiteListItem(
                id=f"{site.site_name}_{site.listen_port}",
                site_name=site.site_name,
                site_type=site.site_type,
                listen_port=site.listen_port,
                server_name=site.server_name,
                enable_https=site.enable_https,
                enable_http_redirect=getattr(site, 'enable_http_redirect', False),
                status="configured",
                is_managed=True  # 所有站点都被视为可管理
            )
            items.append(item)
        
        return items
    
    def extract_server_blocks(self, content: str) -> List[str]:
        """提取所有server块内容."""
        blocks = []
        pos = 0
        depth = 0
        start = -1
        
        while pos < len(content):
            if content[pos:pos+6] == "server":
                # 检查后面是否是空格或{，避免匹配到其他包含server的词
                next_char = content[pos+6:pos+7]
                if next_char.isspace() or next_char == "{":
                    # 找到server块开始
                    bracket_pos = content.find("{", pos)
                    if bracket_pos != -1:
                        start = pos
                        pos = bracket_pos
                        depth = 1
                        
                        # 查找匹配的结束括号
                        pos += 1
                        while pos < len(content) and depth > 0:
                            if content[pos] == "{":
                                depth += 1
                            elif content[pos] == "}":
                                depth -= 1
                            pos += 1
                        
                        if depth == 0:
                            # 提取完整的server块
                            block = content[start:pos]
                            blocks.append(block)
                            continue
            
            pos += 1
        
        return blocks
    
    def get_include_files(self, config_path: Path) -> List[Path]:
        """获取include指令包含的文件."""
        include_files = []
        
        try:
            # 使用健壮的编码检测读取文件
            content = read_file_robust(config_path)
            if content is None:
                logger.error(f"无法读取配置文件: {config_path}")
                return []
            
            # 匹配include指令
            pattern = re.compile(r'include\s+([^;]+);', re.IGNORECASE)
            
            for match in pattern.finditer(content):
                include_path = match.group(1).strip('"\'')
                
                # 处理通配符
                if "*" in include_path:
                    # 相对路径解析
                    if not Path(include_path).is_absolute():
                        base_dir = config_path.parent
                        glob_path = base_dir / include_path
                        include_files.extend(glob_path.parent.glob(glob_path.name))
                    else:
                        include_files.extend(Path().glob(include_path))
                else:
                    # 单个文件
                    path = Path(include_path)
                    if not path.is_absolute():
                        path = config_path.parent / path
                    
                    if path.exists():
                        include_files.append(path)
            
            logger.info(f"Found {len(include_files)} include files")
            
        except Exception as e:
            logger.error(f"Failed to get include files: {e}")
        
        return include_files
