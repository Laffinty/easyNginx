"""Nginx configuration generator with performance baseline and security hardening."""

from pathlib import Path
from typing import Dict, Any, Optional
from jinja2 import Environment, FileSystemLoader, Template
from loguru import logger
from models.site_config import SiteConfigBase, StaticSiteConfig, PHPSiteConfig, ProxySiteConfig
import sys
import os


class ConfigGenerator:
    """
    Nginx配置生成器
    
    核心职责：
    1. 基于Jinja2模板生成Nginx配置
    2. 强制注入性能优化基线（F5/CIS最佳实践）
    3. 根据用户选择注入HTTPS安全加固
    4. 确保生成干净、可读、生产级的配置
    """
    
    def __init__(self, template_dir: Optional[str] = None):
        """初始化配置生成器."""
        if template_dir is None:
            # 默认模板目录
            if getattr(sys, 'frozen', False):
                # PyInstaller打包后的路径
                base_path = Path(sys._MEIPASS)
            else:
                # 开发环境路径
                base_path = Path(__file__).parent.parent
            
            template_dir = str(base_path / "templates")
        
        self.template_dir = Path(template_dir)
        self.template_dir.mkdir(exist_ok=True)
        
        # 初始化Jinja2环境
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True
        )
        
        # 注册自定义过滤器
        self._register_filters()
        
        logger.info(f"ConfigGenerator initialized with template dir: {template_dir}")
    
    def _register_filters(self):
        """注册Jinja2自定义过滤器."""
        
        def nginx_bool(value: bool) -> str:
            """将Python布尔值转换为Nginx的on/off."""
            return "on" if value else "off"
        
        def nginx_size(value: str) -> str:
            """验证并格式化Nginx大小单位."""
            if not value:
                return "10m"
            
            valid_units = ['k', 'K', 'm', 'M', 'g', 'G']
            match = str(value).strip()
            
            # 如果已经是有效格式（数字+单位）
            if any(match.endswith(unit) for unit in valid_units):
                return match
            
            # 默认添加m单位
            try:
                int(match)
                return f"{match}m"
            except ValueError:
                return "10m"
        
        def nginx_time(value: str) -> str:
            """验证并格式化Nginx时间单位."""
            if not value:
                return "65s"
            
            valid_units = ['ms', 's', 'm', 'h', 'd', 'w']
            match = str(value).strip()
            
            # 如果已经是有效格式
            if any(unit in match for unit in valid_units):
                return match
            
            # 默认添加s单位
            try:
                int(match)
                return f"{match}s"
            except ValueError:
                return "65s"
        
        self.jinja_env.filters["nginx_bool"] = nginx_bool
        self.jinja_env.filters["nginx_size"] = nginx_size
        self.jinja_env.filters["nginx_time"] = nginx_time
    
    def generate_config(self, site_config: SiteConfigBase) -> str:
        """
        生成完整的Nginx server块配置
        
        Args:
            site_config: 站点配置对象
            
        Returns:
            Nginx配置字符串
        """
        try:
            # 准备模板上下文（包含性能基线）
            context = self._prepare_template_context(site_config)
            
            # 根据站点类型选择模板
            template_name = f"{site_config.site_type}_site.conf.j2"
            
            # 确保模板存在，如果不存在则创建默认模板
            template_path = self.template_dir / template_name
            if not template_path.exists():
                self._create_default_template(site_config.site_type, template_name)
            
            # 渲染模板
            template = self.jinja_env.get_template(template_name)
            config_content = template.render(**context)
            
            logger.info(f"Generated config for site: {site_config.site_name}")
            
            return config_content
            
        except Exception as e:
            logger.error(f"Failed to generate config for {site_config.site_name}: {e}")
            raise
    
    def _prepare_template_context(self, site_config: SiteConfigBase) -> Dict[str, Any]:
        """
        准备模板上下文，注入性能基线和安全加固
        
        这是核心方法，确保所有生成的配置都符合基线要求
        """
        context = site_config.to_nginx_config()
        
        # 强制注入性能优化基线（F5/CIS最佳实践）
        context["performance_baseline"] = self._get_performance_baseline()
        
        # 注入安全加固（HTTPS相关为可选）
        if site_config.enable_https:
            context["https_security"] = self._get_https_security_hardening()
        
        # 注入通用安全设置
        context["common_security"] = self._get_common_security_settings()
        
        # 添加元数据
        context["generated_time"] = "2026-01-05"
        context["generator"] = "easyNginx v1.0"
        
        return context
    
    def _get_performance_baseline(self) -> Dict[str, Any]:
        """
        获取性能优化基线配置
        来源：F5 Tuning Guide、CIS Benchmarks、2025-2026最佳实践
        """
        return {
            # Worker配置
            "worker_connections": 1024,
            "worker_rlimit_nofile": 8192,
            
            # Keep-Alive优化
            "keepalive_timeout": "65s",
            "keepalive_requests": 1000,
            
            # Gzip压缩（Brotli可选）
            "gzip_enabled": True,
            "gzip_comp_level": 6,
            "gzip_min_length": "1024",
            "gzip_types": [
                "text/plain",
                "text/css",
                "text/xml",
                "text/javascript",
                "application/javascript",
                "application/xml+rss",
                "application/json",
                "image/svg+xml",
                "font/ttf",
                "font/otf"
            ],
            "gzip_vary": True,
            "gzip_proxied": "any",
            
            # 高效传输
            "sendfile_enabled": True,
            "tcp_nopush": True,
            "tcp_nodelay": True,
            "multi_accept": True,
            
            # 请求限制
            "client_max_body_size": "10m",
            "client_body_timeout": "12s",
            "client_header_timeout": "12s",
            "send_timeout": "10s",
            
            # 日志优化
            "access_log": "off",
            "error_log_level": "warn"
        }
    
    def _get_common_security_settings(self) -> Dict[str, Any]:
        """
        获取通用安全设置（HTTP/HTTPS都适用）
        这部分默认启用，用户无法关闭
        """
        return {
            # 隐藏版本信息
            "server_tokens": "off",
            
            # 访问控制：隐藏.开头文件
            "hide_dot_files": True,
            
            # 请求限制（防DDoS/爆破）
            "limit_req_zone": "$binary_remote_addr zone=one:10m rate=10r/s",
            "limit_conn_zone": "$binary_remote_addr zone=addr:10m",
            "limit_req": "zone=one burst=20 nodelay",
            "limit_conn": "addr 20",
            
            # 缓冲区限制（防缓冲区溢出）
            "client_body_buffer_size": "8k",
            "client_header_buffer_size": "1k",
            "large_client_header_buffers": "2 1k",
            
            # 安全头
            "security_headers": {
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "SAMEORIGIN",
                "X-XSS-Protection": "1; mode=block",
                "Referrer-Policy": "strict-origin-when-cross-origin"
            }
        }
    
    def _get_https_security_hardening(self) -> Dict[str, Any]:
        """
        获取HTTPS安全加固（仅在启用HTTPS时应用）
        这部分是可选的，由用户决定是否启用
        """
        return {
            # TLS协议版本（仅允许1.2和1.3）
            "ssl_protocols": ["TLSv1.2", "TLSv1.3"],
            
            # 强加密套件
            "ssl_ciphers": (
                "ECDHE-ECDSA-AES128-GCM-SHA256:"
                "ECDHE-RSA-AES128-GCM-SHA256:"
                "ECDHE-ECDSA-AES256-GCM-SHA384:"
                "ECDHE-RSA-AES256-GCM-SHA384:"
                "ECDHE-ECDSA-CHACHA20-POLY1305:"
                "ECDHE-RSA-CHACHA20-POLY1305:"
                "DHE-RSA-AES128-GCM-SHA256:"
                "DHE-RSA-AES256-GCM-SHA384"
            ),
            "ssl_prefer_server_ciphers": "on",
            
            # SSL会话缓存
            "ssl_session_cache": "shared:SSL:10m",
            "ssl_session_timeout": "10m",
            "ssl_session_tickets": "off",
            
            # OCSP Stapling
            "ssl_stapling": "on",
            "ssl_stapling_verify": "on",
            
            # HSTS（强制HTTP转HTTPS）
            "hsts_enabled": True,
            "hsts_max_age": "31536000",  # 1年
            "hsts_include_subdomains": True,
            "hsts_preload": True,
            
            # HTTP/2
            "http2_enabled": True,
            
            # 安全头（HTTPS专用）
            "https_security_headers": {
                "Content-Security-Policy": (
                    "default-src 'self'; "
                    "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                    "style-src 'self' 'unsafe-inline'; "
                    "img-src 'self' data: https:; "
                    "font-src 'self' data:; "
                    "connect-src 'self';"
                )
            }
        }
    
    def _create_default_template(self, site_type: str, template_name: str):
        """
        创建默认模板文件
        
        Args:
            site_type: 站点类型（static/php/proxy）
            template_name: 模板文件名
        """
        logger.warning(f"Template {template_name} not found, creating default...")
        
        if site_type == "static":
            template_content = self._get_static_template()
        elif site_type == "php":
            template_content = self._get_php_template()
        elif site_type == "proxy":
            template_content = self._get_proxy_template()
        else:
            raise ValueError(f"Unknown site type: {site_type}")
        
        template_path = self.template_dir / template_name
        template_path.write_text(template_content, encoding="utf-8")
        logger.info(f"Created default template: {template_name}")
    
    def _get_static_template(self) -> str:
        """静态站点默认模板."""
        return r'''# {{ site_name }} - Static Site Configuration
# Generated by {{ generator }} at {{ generated_time }}

server {
    listen {{ listen_port }}{% if enable_https and http2_enabled %} http2{% endif %};
    server_name {{ server_name }};
    
    # 性能优化基线（强制）
    {{ "# Performance Baseline" | comment }}
    keepalive_timeout {{ performance_baseline.keepalive_timeout }};
    keepalive_requests {{ performance_baseline.keepalive_requests }};
    
    {% if performance_baseline.gzip_enabled %}
    gzip on;
    gzip_comp_level {{ performance_baseline.gzip_comp_level }};
    gzip_min_length {{ performance_baseline.gzip_min_length }};
    gzip_vary {{ performance_baseline.gzip_vary | nginx_bool }};
    gzip_proxied {{ performance_baseline.gzip_proxied }};
    gzip_types {{ performance_baseline.gzip_types | join(' ') }};
    {% endif %}
    
    sendfile {{ performance_baseline.sendfile_enabled | nginx_bool }};
    tcp_nopush {{ performance_baseline.tcp_nopush | nginx_bool }};
    tcp_nodelay {{ performance_baseline.tcp_nodelay | nginx_bool }};
    
    client_max_body_size {{ performance_baseline.client_max_body_size }};
    
    {% if performance_baseline.access_log == "off" %}
    access_log off;
    {% endif %}
    
    # 通用安全设置
    {{ "# Security Settings" | comment }}
    server_tokens {{ common_security.server_tokens }};
    
    {% if common_security.hide_dot_files %}
    location ~ /\. {
        deny all;
        access_log off;
        log_not_found off;
    }
    {% endif %}
    
    # 请求限制
    limit_req zone=one burst=20 nodelay;
    limit_conn addr 20;
    
    # 根目录和索引
    root "{{ root_path }}";
    index {{ index_file }};
    
    # 主location
    location / {
        try_files $uri $uri/ =404;
    }
    
    # HTTPS配置（可选）
    {% if enable_https %}
    {{ "# HTTPS Configuration" | comment }}
    
    listen 443 ssl{% if https_security.http2_enabled %} http2{% endif %};
    
    ssl_certificate "{{ ssl_cert_path }}";
    ssl_certificate_key "{{ ssl_key_path }}";
    
    ssl_protocols {{ https_security.ssl_protocols | join(' ') }};
    ssl_ciphers {{ https_security.ssl_ciphers }};
    ssl_prefer_server_ciphers {{ https_security.ssl_prefer_server_ciphers }};
    
    ssl_session_cache {{ https_security.ssl_session_cache }};
    ssl_session_timeout {{ https_security.ssl_session_timeout }};
    
    {% if https_security.hsts_enabled %}
    add_header Strict-Transport-Security "max-age={{ https_security.hsts_max_age }}{% if https_security.hsts_include_subdomains %} ; includeSubDomains{% endif %}{% if https_security.hsts_preload %} ; preload{% endif %}" always;
    {% endif %}
    {% endif %}
}
'''
    
    def _get_php_template(self) -> str:
        """PHP站点默认模板."""
        return r'''# {{ site_name }} - PHP Site Configuration
# Generated by {{ generator }} at {{ generated_time }}

server {
    listen {{ listen_port }}{% if enable_https and http2_enabled %} http2{% endif %};
    server_name {{ server_name }};
    
    # 性能优化基线（强制）
    {{ "# Performance Baseline" | comment }}
    keepalive_timeout {{ performance_baseline.keepalive_timeout }};
    keepalive_requests {{ performance_baseline.keepalive_requests }};
    
    {% if performance_baseline.gzip_enabled %}
    gzip on;
    gzip_comp_level {{ performance_baseline.gzip_comp_level }};
    gzip_min_length {{ performance_baseline.gzip_min_length }};
    gzip_vary {{ performance_baseline.gzip_vary | nginx_bool }};
    gzip_proxied {{ performance_baseline.gzip_proxied }};
    gzip_types {{ performance_baseline.gzip_types | join(' ') }};
    {% endif %}
    
    sendfile {{ performance_baseline.sendfile_enabled | nginx_bool }};
    tcp_nopush {{ performance_baseline.tcp_nopush | nginx_bool }};
    tcp_nodelay {{ performance_baseline.tcp_nodelay | nginx_bool }};
    
    client_max_body_size {{ performance_baseline.client_max_body_size }};
    
    {% if performance_baseline.access_log == "off" %}
    access_log off;
    {% endif %}
    
    # 通用安全设置
    {{ "# Security Settings" | comment }}
    server_tokens {{ common_security.server_tokens }};
    
    {% if common_security.hide_dot_files %}
    location ~ /\. {
        deny all;
        access_log off;
        log_not_found off;
    }
    {% endif %}
    
    # 请求限制
    limit_req zone=one burst=20 nodelay;
    limit_conn addr 20;
    
    # 根目录和索引
    root "{{ root_path }}";
    index index.php index.html index.htm;
    
    # PHP-FPM配置
    {% if php_fpm_mode == "unix" %}
    set $php_fpm "{{ php_fpm_socket }}";
    {% else %}
    set $php_fpm "{{ php_fpm_host }}:{{ php_fpm_port }}";
    {% endif %}
    
    # 主location
    location / {
        try_files $uri $uri/ /index.php?$query_string;
    }
    
    # PHP处理
    location ~ \.php$ {
        fastcgi_pass $php_fpm;
        fastcgi_index index.php;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
        fastcgi_param QUERY_STRING $query_string;
        fastcgi_param REQUEST_METHOD $request_method;
        fastcgi_param CONTENT_TYPE $content_type;
        fastcgi_param CONTENT_LENGTH $content_length;
        
        # PHP优化参数
        fastcgi_buffer_size 128k;
        fastcgi_buffers 4 256k;
        fastcgi_busy_buffers_size 256k;
        fastcgi_temp_file_write_size 256k;
        
        include fastcgi_params;
    }
    
    # 隐藏PHP文件
    location ~ /\.php {
        deny all;
        access_log off;
        log_not_found off;
    }
    
    # HTTPS配置（可选）
    {% if enable_https %}
    {{ "# HTTPS Configuration" | comment }}
    
    listen 443 ssl{% if https_security.http2_enabled %} http2{% endif %};
    
    ssl_certificate "{{ ssl_cert_path }}";
    ssl_certificate_key "{{ ssl_key_path }}";
    
    ssl_protocols {{ https_security.ssl_protocols | join(' ') }};
    ssl_ciphers {{ https_security.ssl_ciphers }};
    ssl_prefer_server_ciphers {{ https_security.ssl_prefer_server_ciphers }};
    
    {% if https_security.hsts_enabled %}
    add_header Strict-Transport-Security "max-age={{ https_security.hsts_max_age }}{% if https_security.hsts_include_subdomains %} ; includeSubDomains{% endif %}{% if https_security.hsts_preload %} ; preload{% endif %}" always;
    {% endif %}
    {% endif %}
}
'''
    
    def _get_proxy_template(self) -> str:
        """反向代理默认模板."""
        return r'''# {{ site_name }} - Proxy Site Configuration
# Generated by {{ generator }} at {{ generated_time }}

server {
    listen {{ listen_port }}{% if enable_https and http2_enabled %} http2{% endif %};
    server_name {{ server_name }};
    
    # 性能优化基线（强制）
    {{ "# Performance Baseline" | comment }}
    keepalive_timeout {{ performance_baseline.keepalive_timeout }};
    keepalive_requests {{ performance_baseline.keepalive_requests }};
    
    {% if performance_baseline.gzip_enabled %}
    gzip on;
    gzip_comp_level {{ performance_baseline.gzip_comp_level }};
    gzip_min_length {{ performance_baseline.gzip_min_length }};
    gzip_vary {{ performance_baseline.gzip_vary | nginx_bool }};
    gzip_proxied {{ performance_baseline.gzip_proxied }};
    gzip_types {{ performance_baseline.gzip_types | join(' ') }};
    {% endif %}
    
    sendfile {{ performance_baseline.sendfile_enabled | nginx_bool }};
    tcp_nopush {{ performance_baseline.tcp_nopush | nginx_bool }};
    tcp_nodelay {{ performance_baseline.tcp_nodelay | nginx_bool }};
    
    client_max_body_size {{ performance_baseline.client_max_body_size }};
    
    {% if performance_baseline.access_log == "off" %}
    access_log off;
    {% endif %}
    
    # 通用安全设置
    {{ "# Security Settings" | comment }}
    server_tokens {{ common_security.server_tokens }};
    
    {% if common_security.hide_dot_files %}
    location ~ /\. {
        deny all;
        access_log off;
        log_not_found off;
    }
    {% endif %}
    
    # 请求限制
    limit_req zone=one burst=20 nodelay;
    limit_conn addr 20;
    
    # 反向代理配置
    location {{ location_path }} {
        proxy_pass {{ proxy_pass_url }};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 超时设置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # 缓冲区
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
        proxy_busy_buffers_size 8k;
        
        # WebSocket支持
        {% if enable_websocket %}
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        {% endif %}
    }
    
    # HTTPS配置（可选）
    {% if enable_https %}
    {{ "# HTTPS Configuration" | comment }}
    
    listen 443 ssl{% if https_security.http2_enabled %} http2{% endif %};
    
    ssl_certificate "{{ ssl_cert_path }}";
    ssl_certificate_key "{{ ssl_key_path }}";
    
    ssl_protocols {{ https_security.ssl_protocols | join(' ') }};
    ssl_ciphers {{ https_security.ssl_ciphers }};
    ssl_prefer_server_ciphers {{ https_security.ssl_prefer_server_ciphers }};
    
    {% if https_security.hsts_enabled %}
    add_header Strict-Transport-Security "max-age={{ https_security.hsts_max_age }}{% if https_security.hsts_include_subdomains %} ; includeSubDomains{% endif %}{% if https_security.hsts_preload %} ; preload{% endif %}" always;
    {% endif %}
    {% endif %}
}
'''
    
    def backup_existing_config(self, config_path: Path) -> Path:
        """
        备份现有配置文件
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            备份文件路径
        """
        if not config_path.exists():
            return None
        
        from datetime import datetime
        
        backup_dir = config_path.parent / "backups"
        backup_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{config_path.stem}_{timestamp}.conf.bak"
        backup_path = backup_dir / backup_name
        
        # 复制文件
        content = config_path.read_text(encoding="utf-8")
        backup_path.write_text(content, encoding="utf-8")
        
        logger.info(f"Backup created: {backup_path}")
        
        return backup_path