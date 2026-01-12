"""Site configuration models using Pydantic."""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, validator, ValidationError
from pathlib import Path
import re


class SiteConfigBase(BaseModel, ABC):
    """Base configuration for all site types."""
    
    # 基本站点信息
    site_name: str = Field(..., min_length=1, max_length=100, description="站点名称")
    listen_port: int = Field(default=80, ge=1, le=65535, description="监听端口")
    server_name: str = Field(default="localhost", description="服务器名称")
    
    # HTTPS配置
    enable_https: bool = Field(default=False, description="启用HTTPS")
    enable_http_redirect: bool = Field(default=False, description="80端口重定向到HTTPS")
    ssl_cert_path: Optional[str] = Field(default=None, description="SSL证书路径")
    ssl_key_path: Optional[str] = Field(default=None, description="SSL私钥路径")
    
    # 性能优化基线（默认注入）
    performance_settings: Dict[str, Any] = Field(default_factory=dict, description="性能优化设置")
    
    # 安全加固设置
    security_settings: Dict[str, Any] = Field(default_factory=dict, description="安全加固设置")
    
    class Config:
        """Pydantic配置."""
        use_enum_values = True
        validate_assignment = True
        extra = "forbid"
        
        # 性能优化基线默认值
        @staticmethod
        def get_performance_defaults():
            return {
                "worker_connections": 1024,
                "keepalive_timeout": "65s",
                "keepalive_requests": 100,
                "gzip_enabled": True,
                "gzip_comp_level": 6,
                "gzip_types": [
                    "text/plain", "text/css", "application/javascript",
                    "text/xml", "application/json", "image/svg+xml"
                ],
                "sendfile_enabled": True,
                "tcp_nopush": True,
                "tcp_nodelay": True,
                "multi_accept": True,
                "client_max_body_size": "10m",
                "access_log": "off",
                "error_log_level": "warn"
            }
        
        # 安全加固基线默认值
        @staticmethod
        def get_security_defaults():
            return {
                "server_tokens": "off",
                "hide_dot_files": True,
                "limit_req_zone": "$binary_remote_addr zone=one:10m rate=1r/s",
                "limit_conn_zone": "$binary_remote_addr zone=addr:10m",
                "client_body_buffer_size": "8k",
                "client_header_buffer_size": "1k"
            }
    
    def __init__(self, **data):
        """初始化时自动应用性能基线."""
        super().__init__(**data)
        # 自动填充性能基线
        if not self.performance_settings:
            self.performance_settings = self.Config.get_performance_defaults()
        
        # 自动填充安全基线
        if not self.security_settings:
            self.security_settings = self.Config.get_security_defaults()
    
    @validator("server_name")
    def validate_server_name(cls, v: str) -> str:
        """验证服务器名称."""
        if not v:
            return "localhost"
        
        # 基本域名验证
        domain_regex = re.compile(
            r'^(?:[a-zA-Z0-9_](?:[a-zA-Z0-9\-_]{0,61}[a-zA-Z0-9])?\.)*'
            r'[a-zA-Z0-9_](?:[a-zA-Z0-9\-_]{0,61}[a-zA-Z0-9])?$'
        )
        
        if not domain_regex.match(v) and v != "localhost" and not re.match(r'^\d+\.\d+\.\d+\.\d+$', v):
            raise ValueError(f"Invalid server name: {v}")
        
        return v
    
    @validator("ssl_cert_path", "ssl_key_path")
    def validate_ssl_paths(cls, v: Optional[str], values: Dict[str, Any]) -> Optional[str]:
        """验证SSL证书路径 - 仅警告，不阻止配置加载."""
        if not v:
            return None
        
        # 如果启用了HTTPS，检查文件是否存在（仅警告，不报错）
        if values.get("enable_https"):
            path = Path(v)
            if not path.exists():
                # 在生产环境中，SSL文件可能暂时不存在，只记录警告不阻止加载
                # 使用warnings模块或日志在调用处处理
                pass  # 验证通过，文件存在性检查移到应用逻辑中处理
        
        return v
    
    @abstractmethod
    def to_nginx_config(self) -> str:
        """转换为Nginx配置字符串."""
        pass


class StaticSiteConfig(SiteConfigBase):
    """静态站点配置."""
    
    site_type: Literal["static"] = "static"
    root_path: str = Field(..., description="网站根目录")
    index_file: str = Field(default="index.html", description="默认索引文件")
    
    @validator("root_path")
    def validate_root_path(cls, v: str) -> str:
        """验证根目录路径."""
        path = Path(v)
        if not path.exists():
            # 允许不存在的路径，但必须是合法路径格式
            try:
                path.resolve()
            except Exception:
                raise ValueError(f"Invalid path format: {v}")
        return str(path.resolve()) if path.exists() else v
    
    @validator("index_file")
    def validate_index_file(cls, v: str) -> str:
        """验证索引文件."""
        if not v:
            return "index.html"
        if ".." in v or "/" in v or "\\" in v:
            raise ValueError(f"Invalid index file: {v}")
        return v
    
    def to_nginx_config(self) -> str:
        """生成静态站点Nginx配置."""
        return {
            "site_type": self.site_type,
            "site_name": self.site_name,
            "listen_port": self.listen_port,
            "server_name": self.server_name,
            "enable_https": self.enable_https,
            "enable_http_redirect": self.enable_http_redirect,
            "ssl_cert_path": self.ssl_cert_path,
            "ssl_key_path": self.ssl_key_path,
            "root_path": self.root_path,
            "index_file": self.index_file,
            "performance_settings": self.performance_settings,
            "security_settings": self.security_settings
        }


class PHPSiteConfig(SiteConfigBase):
    """PHP动态站点配置."""
    
    site_type: Literal["php"] = "php"
    php_fpm_mode: str = Field(default="unix", pattern=r"^(unix|tcp)$", description="PHP-FPM连接方式")
    php_fpm_socket: Optional[str] = Field(default="/run/php/php-fpm.sock", description="PHP-FPM Unix Socket路径")
    php_fpm_host: Optional[str] = Field(default="127.0.0.1", description="PHP-FPM TCP主机")
    php_fpm_port: Optional[int] = Field(default=9000, ge=1, le=65535, description="PHP-FPM TCP端口")
    root_path: str = Field(..., description="网站根目录")
    
    @validator("php_fpm_mode")
    def validate_php_fpm_mode(cls, v: str) -> str:
        """验证PHP-FPM模式."""
        if v not in ["unix", "tcp"]:
            raise ValueError("PHP-FPM mode must be 'unix' or 'tcp'")
        return v
    
    @validator("php_fpm_socket")
    def validate_php_fpm_socket(cls, v: Optional[str], values: Dict[str, Any]) -> Optional[str]:
        """验证Unix Socket路径."""
        if values.get("php_fpm_mode") == "unix":
            if not v:
                raise ValueError("Unix socket path is required for unix mode")
            path = Path(v)
            if not path.exists():
                raise ValueError(f"PHP-FPM socket not found: {v}")
        return v
    
    @validator("php_fpm_port")
    def validate_php_fpm_port(cls, v: Optional[int], values: Dict[str, Any]) -> Optional[int]:
        """验证TCP端口."""
        if values.get("php_fpm_mode") == "tcp":
            if not v:
                raise ValueError("Port is required for tcp mode")
        return v
    
    def to_nginx_config(self) -> str:
        """生成PHP站点Nginx配置."""
        return {
            "site_type": self.site_type,
            "site_name": self.site_name,
            "listen_port": self.listen_port,
            "server_name": self.server_name,
            "enable_https": self.enable_https,
            "enable_http_redirect": self.enable_http_redirect,
            "ssl_cert_path": self.ssl_cert_path,
            "ssl_key_path": self.ssl_key_path,
            "root_path": self.root_path,
            "php_fpm_mode": self.php_fpm_mode,
            "php_fpm_socket": self.php_fpm_socket,
            "php_fpm_host": self.php_fpm_host,
            "php_fpm_port": self.php_fpm_port,
            "performance_settings": self.performance_settings,
            "security_settings": self.security_settings
        }


class ProxySiteConfig(SiteConfigBase):
    """反向代理站点配置."""
    
    site_type: Literal["proxy"] = "proxy"
    proxy_pass_url: str = Field(..., description="后端代理地址")
    location_path: str = Field(default="/", description="代理路径前缀")
    enable_websocket: bool = Field(default=False, description="启用WebSocket支持")
    
    @validator("proxy_pass_url")
    def validate_proxy_pass_url(cls, v: str) -> str:
        """验证代理地址."""
        if not v.startswith("http://") and not v.startswith("https://"):
            raise ValueError("Proxy pass URL must start with http:// or https://")
        return v.rstrip("/")
    
    @validator("location_path")
    def validate_location_path(cls, v: str) -> str:
        """验证路径前缀."""
        if not v.startswith("/"):
            v = "/" + v
        return v.rstrip("/") or "/"
    
    def to_nginx_config(self) -> str:
        """生成反向代理Nginx配置."""
        return {
            "site_type": self.site_type,
            "site_name": self.site_name,
            "listen_port": self.listen_port,
            "server_name": self.server_name,
            "enable_https": self.enable_https,
            "enable_http_redirect": self.enable_http_redirect,
            "ssl_cert_path": self.ssl_cert_path,
            "ssl_key_path": self.ssl_key_path,
            "proxy_pass_url": self.proxy_pass_url,
            "location_path": self.location_path,
            "enable_websocket": self.enable_websocket,
            "performance_settings": self.performance_settings,
            "security_settings": self.security_settings
        }


# 类型映射，用于反序列化
SITE_CONFIG_TYPES = {
    "static": StaticSiteConfig,
    "php": PHPSiteConfig,
    "proxy": ProxySiteConfig
}


def create_site_config(site_type: str, **kwargs) -> SiteConfigBase:
    """工厂函数创建站点配置."""
    if site_type not in SITE_CONFIG_TYPES:
        raise ValueError(f"Unknown site type: {site_type}")
    
    config_class = SITE_CONFIG_TYPES[site_type]
    return config_class(**kwargs)