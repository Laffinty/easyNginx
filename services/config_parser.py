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
        self.location_pattern = re.compile(
            r'location\s+([^\s{]+)\s*\{([^}]*)\}',
            re.MULTILINE | re.DOTALL
        )
    
    def parse_config_file(self, config_path: Path) -> List[SiteConfigBase]:
        """
        解析nginx.conf文件，支持include指令和各种格式
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            站点配置对象列表
        """
        if not config_path.exists():
            logger.error(f"Config file not found: {config_path}")
            return []
        
        try:
            # 使用健壮的编码检测读取文件
            content = read_file_robust(config_path)
            if content is None:
                logger.error(f"无法读取配置文件: {config_path}")
                return []
            
            logger.debug(f"Parsing config file: {config_path} (size: {len(content)} bytes)")
            sites = self.parse_config_content(content)
            
            logger.info(f"✓ Parsed {len(sites)} sites from {config_path.name}")
            return sites
            
        except Exception as e:
            logger.exception(f"Failed to parse config file {config_path}: {e}")
            return []
    
    def parse_config_content(self, content: str) -> List[SiteConfigBase]:
        """
        解析配置内容
        
        Args:
            content: 配置内容
            
        Returns:
            站点配置对象列表
        """
        sites = []
        
        # 查找所有server块
        server_blocks = self.server_block_pattern.findall(content)
        
        for i, server_block in enumerate(server_blocks):
            try:
                site_config = self._parse_server_block(server_block)
                if site_config:
                    sites.append(site_config)
            except Exception as e:
                logger.warning(f"Failed to parse server block {i}: {e}")
                continue
        
        return sites
    
    def _parse_server_block(self, server_block: str) -> Optional[SiteConfigBase]:
        """
        解析单个server块，增强健壮性和错误处理
        
        Args:
            server_block: server块内容
            
        Returns:
            站点配置对象或None
        """
        try:
            logger.debug("Parsing server block...")
            
            # 提取所有指令
            directives = {}
            for match in self.directive_pattern.finditer(server_block):
                key = match.group(1)
                value = match.group(2).strip()
                directives[key] = value
            
            logger.debug(f"Extracted {len(directives)} directives")
            
            # 提取location块
            locations = []
            for match in self.location_pattern.finditer(server_block):
                location_path = match.group(1)
                location_body = match.group(2)
                locations.append({"path": location_path, "body": location_body})
            
            logger.debug(f"Extracted {len(locations)} location blocks")
            
            # 检测站点类型
            site_type = self._detect_site_type(directives, locations)
            logger.debug(f"Detected site type: {site_type}")
            
            # 构建基础配置
            base_config = {
                "site_name": self._generate_site_name(directives),
                "listen_port": self._parse_listen_port(directives.get("listen", "80")),
                "server_name": self._parse_server_name(directives.get("server_name", "localhost")),
                "enable_https": "ssl" in directives.get("listen", ""),
                "ssl_cert_path": directives.get("ssl_certificate"),
                "ssl_key_path": directives.get("ssl_certificate_key")
            }
            
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
                site_config = SITE_CONFIG_TYPES[site_type](**config)
                logger.info(f"✓ Successfully parsed site: {config['site_name']} (type: {site_type})")
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
    
    def build_site_list(self, sites: List[SiteConfigBase], is_managed: bool = True) -> List[SiteListItem]:
        """构建站点列表项.
        
        Args:
            sites: 站点配置列表
            is_managed: 是否由easyNginx管理
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
                status="configured",
                is_managed=is_managed
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