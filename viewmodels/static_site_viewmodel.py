"""Static site configuration ViewModel."""

from pathlib import Path
from PySide6.QtCore import Property, Signal
from loguru import logger
from models.site_config import StaticSiteConfig
from viewmodels.base_site_viewmodel import BaseSiteViewModel


class StaticSiteViewModel(BaseSiteViewModel):
    """
    静态站点配置ViewModel
    
    管理静态站点的表单和业务逻辑
    """
    
    def __init__(self):
        """初始化静态站点ViewModel."""
        super().__init__()
        logger.info("StaticSiteViewModel initialized")
    
    # Property定义
    @Property(str, notify=BaseSiteViewModel.config_changed)
    def root_path(self) -> str:
        """网站根目录."""
        if isinstance(self._site_config, StaticSiteConfig):
            return self._site_config.root_path
        return ""
    
    @root_path.setter
    def root_path(self, value: str):
        """设置网站根目录."""
        if isinstance(self._site_config, StaticSiteConfig) and value:
            self._site_config.root_path = value
            self.config_changed.emit()
    
    @Property(str, notify=BaseSiteViewModel.config_changed)
    def index_file(self) -> str:
        """索引文件."""
        if isinstance(self._site_config, StaticSiteConfig):
            return self._site_config.index_file
        return "index.html"
    
    @index_file.setter
    def index_file(self, value: str):
        """设置索引文件."""
        if isinstance(self._site_config, StaticSiteConfig):
            self._site_config.index_file = value or "index.html"
            self.config_changed.emit()
    
    # 实现抽象方法
    def create_new_config(self):
        """创建新配置."""
        try:
            self._site_config = StaticSiteConfig(
                site_name="New Static Site",
                root_path=str(Path.cwd()),
                index_file="index.html",
                listen_port=80,
                server_name="localhost"
            )
            self._is_editing = False
            self.config_changed.emit()
            logger.info("Created new static site configuration")
        except Exception as e:
            logger.error(f"Failed to create new config: {e}")
    
    def load_config(self, site_config: StaticSiteConfig):
        """加载现有配置."""
        try:
            if isinstance(site_config, StaticSiteConfig):
                self._site_config = site_config
                self._is_editing = True
                self.config_changed.emit()
                logger.info(f"Loaded static site config: {site_config.site_name}")
            else:
                logger.error("Invalid site configuration type")
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
    
    def get_config(self) -> StaticSiteConfig:
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
            
            # 验证根目录
            root_path = self._site_config.root_path
            if not root_path or not Path(root_path).exists():
                # 允许不存在的目录，但必须是有效路径
                try:
                    Path(root_path).resolve()
                except Exception:
                    self._add_validation_error("root_path", "Invalid directory path")
                    is_valid = False
            
            # 验证索引文件
            if ".." in self._site_config.index_file or "/" in self._site_config.index_file:
                self._add_validation_error("index_file", "Invalid index file name")
                is_valid = False
            
            # 验证HTTPS配置
            if self._site_config.enable_https:
                is_valid &= self._validate_https_paths()
            
            if is_valid:
                logger.info(f"Validation passed for site: {self._site_config.site_name}")
            else:
                logger.warning(f"Validation failed for site: {self._site_config.site_name}")
            
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
        """是否支持PHP（静态站点不支持）."""
        return False
    
    @Property(bool, constant=True)
    def supports_proxy(self) -> bool:
        """是否支持代理（静态站点不支持）."""
        return False