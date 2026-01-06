"""Base site ViewModel for all site types."""

from typing import Optional, Dict, Any
from pathlib import Path
from PySide6.QtCore import QObject, Signal, Property
from loguru import logger
from models.site_config import SiteConfigBase


class BaseSiteViewModel(QObject):
    """
    站点配置ViewModel基类
    
    职责：
    1. 管理站点配置状态
    2. 表单验证
    3. 配置预览
    """
    
    # 信号定义
    config_changed = Signal()  # 配置变更
    validation_changed = Signal()  # 验证状态变更
    preview_requested = Signal()  # 预览请求
    
    def __init__(self):
        """初始化基类."""
        super().__init__()
        self._site_config: Optional[SiteConfigBase] = None
        self._is_editing: bool = False
        self._validation_errors: Dict[str, str] = {}
        
        logger.info(f"{self.__class__.__name__} initialized")
    
    # Property定义
    @Property(bool, notify=config_changed)
    def is_editing(self) -> bool:
        """是否处于编辑模式."""
        return self._is_editing
    
    @Property(str, notify=config_changed)
    def site_name(self) -> str:
        """站点名称."""
        return self._site_config.site_name if self._site_config else ""
    
    @site_name.setter
    def site_name(self, value: str):
        """设置站点名称."""
        if self._site_config and value:
            self._site_config.site_name = value
            self.config_changed.emit()
    
    @Property(int, notify=config_changed)
    def listen_port(self) -> int:
        """监听端口."""
        return self._site_config.listen_port if self._site_config else 80
    
    @listen_port.setter
    def listen_port(self, value: int):
        """设置监听端口."""
        if self._site_config and value > 0:
            self._site_config.listen_port = value
            self.config_changed.emit()
    
    @Property(str, notify=config_changed)
    def server_name(self) -> str:
        """服务器名称."""
        return self._site_config.server_name if self._site_config else "localhost"
    
    @server_name.setter
    def server_name(self, value: str):
        """设置服务器名称."""
        if self._site_config and value:
            self._site_config.server_name = value
            self.config_changed.emit()
    
    @Property(bool, notify=config_changed)
    def enable_https(self) -> bool:
        """是否启用HTTPS."""
        return self._site_config.enable_https if self._site_config else False
    
    @enable_https.setter
    def enable_https(self, value: bool):
        """设置HTTPS开关."""
        if self._site_config:
            self._site_config.enable_https = value
            self.config_changed.emit()
    
    @Property(str, notify=config_changed)
    def ssl_cert_path(self) -> str:
        """SSL证书路径."""
        return self._site_config.ssl_cert_path if self._site_config else ""
    
    @ssl_cert_path.setter
    def ssl_cert_path(self, value: str):
        """设置SSL证书路径."""
        if self._site_config:
            self._site_config.ssl_cert_path = value
            self.config_changed.emit()
    
    @Property(str, notify=config_changed)
    def ssl_key_path(self) -> str:
        """SSL私钥路径."""
        return self._site_config.ssl_key_path if self._site_config else ""
    
    @ssl_key_path.setter
    def ssl_key_path(self, value: str):
        """设置SSL私钥路径."""
        if self._site_config:
            self._site_config.ssl_key_path = value
            self.config_changed.emit()
    
    @Property(bool, notify=validation_changed)
    def is_valid(self) -> bool:
        """配置是否有效."""
        return len(self._validation_errors) == 0
    
    @Property(dict, notify=validation_changed)
    def validation_errors(self) -> dict:
        """验证错误."""
        return self._validation_errors
    
    # 抽象方法（子类必须实现）
    def create_new_config(self):
        """创建新配置."""
        raise NotImplementedError("Subclasses must implement create_new_config")
    
    def load_config(self, site_config: SiteConfigBase):
        """加载现有配置."""
        raise NotImplementedError("Subclasses must implement load_config")
    
    def get_config(self) -> Optional[SiteConfigBase]:
        """获取当前配置."""
        raise NotImplementedError("Subclasses must implement get_config")
    
    def validate(self) -> bool:
        """验证配置."""
        raise NotImplementedError("Subclasses must implement validate")
    
    def reset(self):
        """重置配置."""
        raise NotImplementedError("Subclasses must implement reset")
    
    # 公共方法
    def start_edit(self, site_config: Optional[SiteConfigBase] = None):
        """开始编辑."""
        if site_config:
            self.load_config(site_config)
            self._is_editing = True
        else:
            self.create_new_config()
            self._is_editing = False
        
        self.config_changed.emit()
    
    def cancel_edit(self):
        """取消编辑."""
        self.reset()
        self._is_editing = False
        self.config_changed.emit()
    
    def request_preview(self):
        """请求预览."""
        if self.validate():
            self.preview_requested.emit()
        else:
            self.error_occurred.emit("Configuration validation failed")
    
    def _add_validation_error(self, field: str, error: str):
        """添加验证错误."""
        self._validation_errors[field] = error
        self.validation_changed.emit()
    
    def _clear_validation_errors(self):
        """清除验证错误."""
        self._validation_errors.clear()
        self.validation_changed.emit()
    
    def _validate_required(self, value: str, field_name: str) -> bool:
        """验证必填字段."""
        if not value or not value.strip():
            self._add_validation_error(field_name, f"{field_name} is required")
            return False
        return True
    
    def _validate_port(self, port: int, field_name: str = "listen_port") -> bool:
        """验证端口."""
        if not 1 <= port <= 65535:
            self._add_validation_error(field_name, "Port must be between 1 and 65535")
            return False
        return True
    
    def _validate_https_paths(self) -> bool:
        """验证HTTPS路径."""
        if not self._site_config or not self._site_config.enable_https:
            return True
        
        is_valid = True
        
        if not self._site_config.ssl_cert_path:
            self._add_validation_error("ssl_cert_path", "SSL certificate path is required when HTTPS is enabled")
            is_valid = False
        
        if not self._site_config.ssl_key_path:
            self._add_validation_error("ssl_key_path", "SSL key path is required when HTTPS is enabled")
            is_valid = False
        
        # 检查文件是否存在
        if self._site_config.ssl_cert_path and not Path(self._site_config.ssl_cert_path).exists():
            self._add_validation_error("ssl_cert_path", "SSL certificate file not found")
            is_valid = False
        
        if self._site_config.ssl_key_path and not Path(self._site_config.ssl_key_path).exists():
            self._add_validation_error("ssl_key_path", "SSL key file not found")
            is_valid = False
        
        return is_valid