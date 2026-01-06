"""PHP site configuration ViewModel."""

from pathlib import Path
from PySide6.QtCore import Property, Signal
from loguru import logger
from models.site_config import PHPSiteConfig
from viewmodels.base_site_viewmodel import BaseSiteViewModel


class PHPSiteViewModel(BaseSiteViewModel):
    """
    PHP站点配置ViewModel
    
    管理PHP动态站点的表单和业务逻辑
    """
    
    def __init__(self):
        """初始化PHP站点ViewModel."""
        super().__init__()
        self._available_sockets = [
            "/run/php/php-fpm.sock",
            "/var/run/php/php-fpm.sock", 
            "/var/run/php-fpm/php-fpm.sock"
        ]
        logger.info("PHPSiteViewModel initialized")
    
    # Property定义
    @Property(list, constant=True)
    def available_sockets(self) -> list:
        """可用的PHP-FPM Socket路径."""
        return self._available_sockets
    
    @Property(str, notify=BaseSiteViewModel.config_changed)
    def php_fpm_mode(self) -> str:
        """PHP-FPM连接方式."""
        if isinstance(self._site_config, PHPSiteConfig):
            return self._site_config.php_fpm_mode
        return "unix"
    
    @php_fpm_mode.setter
    def php_fpm_mode(self, value: str):
        """设置PHP-FPM连接方式."""
        if isinstance(self._site_config, PHPSiteConfig):
            self._site_config.php_fpm_mode = value
            self.config_changed.emit()
    
    @Property(str, notify=BaseSiteViewModel.config_changed)
    def php_fpm_socket(self) -> str:
        """PHP-FPM Unix Socket路径."""
        if isinstance(self._site_config, PHPSiteConfig):
            return self._site_config.php_fpm_socket
        return ""
    
    @php_fpm_socket.setter
    def php_fpm_socket(self, value: str):
        """设置PHP-FPM Unix Socket路径."""
        if isinstance(self._site_config, PHPSiteConfig):
            self._site_config.php_fpm_socket = value
            self.config_changed.emit()
    
    @Property(str, notify=BaseSiteViewModel.config_changed)
    def php_fpm_host(self) -> str:
        """PHP-FPM TCP主机."""
        if isinstance(self._site_config, PHPSiteConfig):
            return self._site_config.php_fpm_host
        return "127.0.0.1"
    
    @php_fpm_host.setter
    def php_fpm_host(self, value: str):
        """设置PHP-FPM TCP主机."""
        if isinstance(self._site_config, PHPSiteConfig):
            self._site_config.php_fpm_host = value
            self.config_changed.emit()
    
    @Property(int, notify=BaseSiteViewModel.config_changed)
    def php_fpm_port(self) -> int:
        """PHP-FPM TCP端口."""
        if isinstance(self._site_config, PHPSiteConfig):
            return self._site_config.php_fpm_port
        return 9000
    
    @php_fpm_port.setter
    def php_fpm_port(self, value: int):
        """设置PHP-FPM TCP端口."""
        if isinstance(self._site_config, PHPSiteConfig):
            self._site_config.php_fpm_port = value
            self.config_changed.emit()
    
    @Property(str, notify=BaseSiteViewModel.config_changed)
    def root_path(self) -> str:
        """网站根目录."""
        if isinstance(self._site_config, PHPSiteConfig):
            return self._site_config.root_path
        return ""
    
    @root_path.setter
    def root_path(self, value: str):
        """设置网站根目录."""
        if isinstance(self._site_config, PHPSiteConfig) and value:
            self._site_config.root_path = value
            self.config_changed.emit()
    
    # 实现抽象方法
    def create_new_config(self):
        """创建新配置."""
        try:
            self._site_config = PHPSiteConfig(
                site_name="New PHP Site",
                root_path=str(Path.cwd()),
                php_fpm_mode="unix",
                php_fpm_socket="/run/php/php-fpm.sock",
                php_fpm_host="127.0.0.1",
                php_fpm_port=9000,
                listen_port=80,
                server_name="localhost"
            )
            self._is_editing = False
            self.config_changed.emit()
            logger.info("Created new PHP site configuration")
        except Exception as e:
            logger.error(f"Failed to create new config: {e}")
    
    def load_config(self, site_config: PHPSiteConfig):
        """加载现有配置."""
        try:
            if isinstance(site_config, PHPSiteConfig):
                self._site_config = site_config
                self._is_editing = True
                self.config_changed.emit()
                logger.info(f"Loaded PHP site config: {site_config.site_name}")
            else:
                logger.error("Invalid site configuration type")
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
    
    def get_config(self) -> PHPSiteConfig:
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
                try:
                    Path(root_path).resolve()
                except Exception:
                    self._add_validation_error("root_path", "Invalid directory path")
                    is_valid = False
            
            # 验证PHP-FPM配置
            if self._site_config.php_fpm_mode == "unix":
                if not self._site_config.php_fpm_socket:
                    self._add_validation_error("php_fpm_socket", "PHP-FPM socket path is required for unix mode")
                    is_valid = False
                # 检查Socket是否存在（可选，因为服务可能未启动）
            else:  # TCP模式
                if not self._site_config.php_fpm_host:
                    self._add_validation_error("php_fpm_host", "PHP-FPM host is required for tcp mode")
                    is_valid = False
                if not self._validate_port(self._site_config.php_fpm_port, "php_fpm_port"):
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
        return True
    
    @Property(bool, constant=True)
    def supports_proxy(self) -> bool:
        """是否支持代理."""
        return False