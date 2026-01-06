"""Proxy site configuration ViewModel."""

from pathlib import Path
from PySide6.QtCore import Property, Signal
from loguru import logger
from models.site_config import ProxySiteConfig
from viewmodels.base_site_viewmodel import BaseSiteViewModel


class ProxySiteViewModel(BaseSiteViewModel):
    """
    反向代理站点配置ViewModel
    
    管理反向代理站点的表单和业务逻辑
    """
    
    def __init__(self):
        """初始化反向代理站点ViewModel."""
        super().__init__()
        logger.info("ProxySiteViewModel initialized")
    
    # Property定义
    @Property(str, notify=BaseSiteViewModel.config_changed)
    def proxy_pass_url(self) -> str:
        """后端代理地址."""
        if isinstance(self._site_config, ProxySiteConfig):
            return self._site_config.proxy_pass_url
        return "http://localhost:8080"
    
    @proxy_pass_url.setter
    def proxy_pass_url(self, value: str):
        """设置后端代理地址."""
        if isinstance(self._site_config, ProxySiteConfig):
            self._site_config.proxy_pass_url = value
            self.config_changed.emit()
    
    @Property(str, notify=BaseSiteViewModel.config_changed)
    def location_path(self) -> str:
        """代理路径前缀."""
        if isinstance(self._site_config, ProxySiteConfig):
            return self._site_config.location_path
        return "/"
    
    @location_path.setter
    def location_path(self, value: str):
        """设置代理路径前缀."""
        if isinstance(self._site_config, ProxySiteConfig):
            self._site_config.location_path = value
            self.config_changed.emit()
    
    @Property(bool, notify=BaseSiteViewModel.config_changed)
    def enable_websocket(self) -> bool:
        """启用WebSocket支持."""
        if isinstance(self._site_config, ProxySiteConfig):
            return self._site_config.enable_websocket
        return False
    
    @enable_websocket.setter
    def enable_websocket(self, value: bool):
        """设置WebSocket支持."""
        if isinstance(self._site_config, ProxySiteConfig):
            self._site_config.enable_websocket = value
            self.config_changed.emit()
    
    # 实现抽象方法
    def create_new_config(self):
        """创建新配置."""
        try:
            self._site_config = ProxySiteConfig(
                site_name="New Proxy Site",
                proxy_pass_url="http://localhost:8080",
                location_path="/",
                enable_websocket=False,
                listen_port=80,
                server_name="localhost"
            )
            self._is_editing = False
            self.config_changed.emit()
            logger.info("Created new proxy site configuration")
        except Exception as e:
            logger.error(f"Failed to create new config: {e}")
    
    def load_config(self, site_config: ProxySiteConfig):
        """加载现有配置."""
        try:
            if isinstance(site_config, ProxySiteConfig):
                self._site_config = site_config
                self._is_editing = True
                self.config_changed.emit()
                logger.info(f"Loaded proxy site config: {site_config.site_name}")
            else:
                logger.error("Invalid site configuration type")
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
    
    def get_config(self) -> ProxySiteConfig:
        """获取当前配置."""
        return self._site_config
    
    def validate(self) -> bool:
        """验证配置."""
        try:
            self._clear_validation_errors()
            
            if not self._site_config:
                self.error_occurred.emit("No configuration to validate")
                return False
            
            # 验证必填字段
            is_valid = True
            is_valid &= self._validate_required(self._site_config.site_name, "site_name")
            is_valid &= self._validate_required(self._site_config.server_name, "server_name")
            is_valid &= self._validate_port(self._site_config.listen_port, "listen_port")
            
            # 验证代理地址
            if not self._site_config.proxy_pass_url:
                self._add_validation_error("proxy_pass_url", "Proxy pass URL is required")
                is_valid = False
            elif not (self._site_config.proxy_pass_url.startswith("http://") or 
                     self._site_config.proxy_pass_url.startswith("https://")):
                self._add_validation_error("proxy_pass_url", "Proxy URL must start with http:// or https://")
                is_valid = False
            
            # 验证HTTPS配置
            if self._site_config.enable_https:
                is_valid &= self._validate_https_paths()
            
            return is_valid
            
        except Exception as e:
            logger.error(f"Validation error: {e}")
            self.error_occurred.emit(f"Validation error: {e}")
            return False
    
    def reset(self):
        """重置配置."""
        self._site_config = None
        self._is_editing = False
        self._clear_validation_errors()
        self.config_changed.emit()
    
    # 特定方法
    @Property(bool, constant=True)
    def supports_php(self) -> bool:
        """是否支持PHP."""
        return False
    
    @Property(bool, constant=True)
    def supports_proxy(self) -> bool:
        """是否支持代理."""
        return True