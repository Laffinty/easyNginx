"""Data models for easyNginx."""

from .site_config import SiteConfigBase, StaticSiteConfig, PHPSiteConfig, ProxySiteConfig
from .nginx_status import NginxStatus

__all__ = [
    "SiteConfigBase",
    "StaticSiteConfig", 
    "PHPSiteConfig",
    "ProxySiteConfig",
    "NginxStatus"
]