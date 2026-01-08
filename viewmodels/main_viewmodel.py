"""Main ViewModel - Business logic coordinator."""

from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path
import platform
from PySide6.QtCore import QObject, Signal, QThread, QTimer
from loguru import logger
from models.site_config import SiteConfigBase, create_site_config
from models.nginx_status import NginxStatus, SiteListItem
from services.nginx_service import NginxService
from services.config_generator import ConfigGenerator
from services.config_parser import ConfigParser
from services.config_manager import ConfigManager
from utils.language_manager import LanguageManager


class StatusUpdateThread(QThread):
    """
    后台线程用于更新Nginx状态
    避免阻塞GUI主线程
    """
    
    status_updated = Signal(NginxStatus)
    error_occurred = Signal(str)
    
    def __init__(self, nginx_service: NginxService):
        """初始化状态更新线程."""
        super().__init__()
        self.nginx_service = nginx_service
        self._running = True
        self.interval = 2000  # 2秒间隔
        
    def run(self):
        """线程主循环."""
        while self._running:
            try:
                if self._running:  # 再次检查避免竞争条件
                    status = self.nginx_service.get_status()
                    self.status_updated.emit(status)
            except Exception as e:
                logger.error(f"Status update thread error: {e}")
                self.error_occurred.emit(str(e))
            
            # 等待指定间隔
            self.msleep(self.interval)
    
    def stop(self):
        """停止线程."""
        self._running = False
        self.quit()
        self.wait()


class MainViewModel(QObject):
    """
    Main ViewModel - Main business logic coordinator
    
    Responsibilities:
    1. Coordinate ViewModels
    2. Manage Nginx service status
    3. Handle site CRUD operations
    4. Config generation and deployment
    5. Error handling and logging
    """
    
    # Signal definitions
    nginx_status_changed = Signal(NginxStatus)
    site_list_changed = Signal(list)
    config_generated = Signal(str)
    operation_completed = Signal(bool, str)
    error_occurred = Signal(str)
    
    def __init__(self, nginx_path: Optional[str] = None, config_path: Optional[str] = None):
        """Initialize MainViewModel."""
        super().__init__()
        
        # Initialize services
        self.nginx_service = NginxService(nginx_path, config_path)
        self.config_generator = ConfigGenerator()
        self.config_parser = ConfigParser()
        self.config_manager = ConfigManager(Path(config_path) if config_path else None)
        self.language_manager = LanguageManager()
        
        # State management
        self.sites: List[SiteConfigBase] = []
        self.current_site: Optional[SiteConfigBase] = None
        self.nginx_status: Optional[NginxStatus] = None
        
        # 使用后台线程进行状态监控（替代QTimer）
        self.status_thread: Optional[StatusUpdateThread] = None
        
        logger.info("MainViewModel initialized")
    
    def initialize(self):
        """初始化应用 - 包括Nginx检查、配置同步和状态监控."""
        logger.info("=" * 60)
        logger.info("Initializing MainViewModel...")
        logger.info(f"Nginx path: {self.nginx_service.nginx_path}")
        logger.info(f"Config path: {self.nginx_service.config_path}")
        
        # 检查Nginx可用性
        if not self.nginx_service.is_nginx_available():
            error_msg = "Nginx is not available. Please check the installation."
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return False
        
        logger.info("Nginx is available ✓")
        
        # 检查配置文件是否存在
        if not self.nginx_service.config_path or not Path(self.nginx_service.config_path).exists():
            warning_msg = f"Nginx config file not found at: {self.nginx_service.config_path}. Starting with empty site list."
            logger.warning(warning_msg)
            # 不返回False,允许继续运行,只是站点列表为空
            self.sites = []
            self.site_list_changed.emit([])
        else:
            # 加载现有配置 - 这是同步nginx.conf中站点配置的关键步骤
            logger.info("Starting configuration sync from nginx.conf...")
            
            # 设置配置管理器路径
            self.config_manager.config_path = Path(self.nginx_service.config_path)
            
            # 加载管理的站点
            self.load_sites()
            
            if self.sites:
                logger.info(f"Configuration sync completed: {len(self.sites)} managed sites loaded")
            else:
                logger.info("Configuration sync completed: No managed sites found in nginx.conf")
        
        # 启动后台状态监控线程
        logger.info("Starting status monitoring thread...")
        self._start_status_monitoring()
        
        logger.info("MainViewModel initialized successfully ✓")
        logger.info("=" * 60)
        return True
    
    def cleanup(self):
        """清理资源."""
        logger.info("Cleaning up MainViewModel...")
        self._stop_status_monitoring()
    
    def _start_status_monitoring(self):
        """启动后台状态监控线程."""
        if self.status_thread is None:
            self.status_thread = StatusUpdateThread(self.nginx_service)
            self.status_thread.status_updated.connect(self._on_status_updated)
            self.status_thread.error_occurred.connect(self.error_occurred)
            self.status_thread.start()
            logger.info("Status monitoring thread started")
    
    def _stop_status_monitoring(self):
        """停止后台状态监控线程."""
        if self.status_thread is not None:
            self.status_thread.stop()
            self.status_thread = None
            logger.info("Status monitoring thread stopped")
    
    def _update_status(self):
        """手动更新Nginx状态（仅用于初始化）."""
        try:
            self.nginx_status = self.nginx_service.get_status()
            self.nginx_status_changed.emit(self.nginx_status)
        except Exception as e:
            logger.error(f"Failed to update status: {e}")
            self.error_occurred.emit(f"Status update failed: {e}")
    
    def _on_status_updated(self, status: NginxStatus):
        """后台线程状态更新回调."""
        self.nginx_status = status
        self.nginx_status_changed.emit(status)
    
    def load_sites(self):
        """加载站点列表 - 只加载标记为管理的server块，保留其他配置."""
        logger.info("Starting to load managed sites from nginx configuration...")
        
        try:
            if not self.nginx_service.config_path:
                error_msg = "Nginx config path is not set, cannot load sites"
                logger.error(error_msg)
                self.error_occurred.emit(error_msg)
                return
            
            config_path = Path(self.nginx_service.config_path)
            
            if not config_path.exists():
                error_msg = f"Nginx config file not found: {config_path}"
                logger.warning(error_msg)
                # 配置文件不存在时，初始化空站点列表
                self.sites = []
                self.site_list_changed.emit([])
                # 不显示错误，因为这是首次运行的情况
                return
            
            logger.info(f"Reading nginx configuration from: {config_path}")
            
            # 加载配置文件内容
            content = config_path.read_text(encoding="utf-8", errors="ignore")
            
            # 使用配置管理器解析标记为管理的站点
            self.sites = self.config_manager.parse_managed_sites(content, self.config_parser)
            
            logger.info(f"Loaded {len(self.sites)} managed sites from config")
            
            # 转换为SiteListItem用于UI显示
            site_items = self.config_parser.build_site_list(self.sites)
            self.site_list_changed.emit(site_items)
            
            # 发送操作完成信号
            self.operation_completed.emit(True, f"从nginx.conf加载 {len(self.sites)} 个受管站点")
            
        except Exception as e:
            logger.exception(f"Failed to load sites: {e}")
            self.error_occurred.emit(f"加载站点配置失败: {e}")
            # 确保即使失败也有空列表
            self.sites = []
            self.site_list_changed.emit([])
    
    def add_site(self, site_config: SiteConfigBase) -> bool:
        """
        添加新站点
        
        Args:
            site_config: 站点配置对象
            
        Returns:
            是否成功
        """
        try:
            # 验证配置
            if not site_config or not site_config.site_name or not site_config.site_name.strip():
                self.error_occurred.emit("站点名称不能为空")
                return False
            
            # 清理站点名称（移除首尾空格等）
            site_config.site_name = site_config.site_name.strip()
            
            # 检查站点名称唯一性
            for site in self.sites:
                if site.site_name == site_config.site_name:
                    self.error_occurred.emit(f"站点名称 '{site_config.site_name}' 已存在")
                    return False
            
            # 检查端口冲突
            for site in self.sites:
                if (site.listen_port == site_config.listen_port and 
                    site.server_name == site_config.server_name):
                    self.error_occurred.emit(
                        f"端口 {site_config.listen_port} 已被 {site.site_name} 使用"
                    )
                    return False
            
            # 添加站点
            self.sites.append(site_config)
            
            # 生成配置
            if self._deploy_config():
                self.load_sites()  # 重新加载列表
                self.operation_completed.emit(True, f"站点 '{site_config.site_name}' 添加成功")
                return True
            else:
                self.sites.remove(site_config)  # 回滚
                return False
                
        except Exception as e:
            logger.error(f"添加站点失败: {e}")
            self.error_occurred.emit(f"添加站点失败: {e}")
            return False
    
    def update_site(self, old_site_name: str, site_config: SiteConfigBase) -> bool:
        """
        更新现有站点
        
        Args:
            old_site_name: 原站点名称
            site_config: 新站点配置
            
        Returns:
            是否成功
        """
        try:
            # 查找原站点
            old_site = next((s for s in self.sites if s.site_name == old_site_name), None)
            if not old_site:
                self.error_occurred.emit(f"Site '{old_site_name}' not found")
                return False
            
            # 更新站点
            self.sites.remove(old_site)
            self.sites.append(site_config)
            
            # 重新部署
            if self._deploy_config():
                self.load_sites()
                self.operation_completed.emit(True, f"Site '{site_config.site_name}' updated successfully")
                return True
            else:
                # 回滚
                self.sites.remove(site_config)
                self.sites.append(old_site)
                return False
                
        except Exception as e:
            logger.error(f"Failed to update site: {e}")
            self.error_occurred.emit(f"Failed to update site: {e}")
            return False
    
    def delete_site(self, site_name: str) -> bool:
        """
        删除站点
        
        Args:
            site_name: 站点名称
            
        Returns:
            是否成功
        """
        try:
            # 查找站点
            site = next((s for s in self.sites if s.site_name == site_name), None)
            if not site:
                self.error_occurred.emit(f"Site '{site_name}' not found")
                return False
            
            # 确认删除（由UI层处理）
            self.sites.remove(site)
            
            # 重新部署
            if self._deploy_config():
                self.load_sites()
                self.operation_completed.emit(True, f"Site '{site_name}' deleted successfully")
                return True
            else:
                # 回滚
                self.sites.append(site)
                return False
                
        except Exception as e:
            logger.error(f"Failed to delete site: {e}")
            self.error_occurred.emit(f"Failed to delete site: {e}")
            return False
    
    def generate_config_preview(self, site_config: SiteConfigBase) -> str:
        """
        生成配置预览
        
        Args:
            site_config: 站点配置
            
        Returns:
            配置内容
        """
        try:
            config_content = self.config_generator.generate_config(site_config)
            self.config_generated.emit(config_content)
            return config_content
        except Exception as e:
            logger.error(f"Failed to generate config preview: {e}")
            self.error_occurred.emit(f"Config generation failed: {e}")
            return ""
    
    def _deploy_config(self) -> bool:
        """
        部署配置到Nginx - 使用配置管理器进行增量更新
        
        Returns:
            是否成功
        """
        try:
            # 使用配置管理器更新配置（只更新server块，保留其他用户配置）
            success = self.config_manager.update_config(
                sites=self.sites,
                config_generator=self.config_generator
            )
            
            if not success:
                self.error_occurred.emit("Failed to update configuration")
                return False
            
            # 测试配置
            is_valid, message = self.nginx_service.test_config()
            if not is_valid:
                self.error_occurred.emit(f"Config test failed: {message}")
                return False
            
            # 重载Nginx
            if self.nginx_service.is_nginx_running():
                success, msg = self.nginx_service.reload_nginx()
                if not success:
                    self.error_occurred.emit(f"Nginx reload failed: {msg}")
                    return False
            
            logger.info(f"Successfully deployed {len(self.sites)} sites")
            return True
            
        except Exception as e:
            logger.exception(f"Failed to deploy config: {e}")
            self.error_occurred.emit(f"Config deployment failed: {e}")
            return False
    
    def _get_config_summary(self) -> str:
        """获取配置摘要信息."""
        return f"""# Nginx Configuration
# Managed by easyNginx
# Total sites: {len(self.sites)}
# Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    def control_nginx(self, action: str) -> bool:
        """
        控制Nginx（启动/停止/重载）
        
        Args:
            action: 操作（start/stop/reload）
            
        Returns:
            是否成功
        """
        try:
            if action == "start":
                success, msg = self.nginx_service.start_nginx()
            elif action == "stop":
                success, msg = self.nginx_service.stop_nginx()
            elif action == "reload":
                success, msg = self.nginx_service.reload_nginx()
            else:
                self.error_occurred.emit(f"Unknown action: {action}")
                return False
            
            if success:
                self.operation_completed.emit(True, msg)
                self._update_status()
                return True
            else:
                self.error_occurred.emit(msg)
                return False
                
        except Exception as e:
            logger.error(f"Failed to {action} nginx: {e}")
            self.error_occurred.emit(f"Nginx {action} failed: {e}")
            return False
    
    def test_config(self) -> Tuple[bool, str]:
        """
        测试Nginx配置
        
        Returns:
            (is_valid, message)
        """
        try:
            is_valid, message = self.nginx_service.test_config()
            if is_valid:
                self.operation_completed.emit(True, f"Config test passed: {message}")
            else:
                self.error_occurred.emit(f"Config test failed: {message}")
            return is_valid, message
        except Exception as e:
            logger.error(f"Failed to test config: {e}")
            self.error_occurred.emit(f"Config test error: {e}")
            return False, str(e)
    
    def backup_config(self) -> bool:
        """备份配置文件."""
        try:
            backup_path = self.nginx_service.backup_config()
            if backup_path:
                self.operation_completed.emit(True, f"Backup created: {backup_path}")
                return True
            else:
                self.error_occurred.emit("Failed to create backup")
                return False
        except Exception as e:
            logger.error(f"Failed to backup config: {e}")
            self.error_occurred.emit(f"Backup failed: {e}")
            return False
    
    def get_site_by_name(self, site_name: str) -> Optional[SiteConfigBase]:
        """根据名称获取站点."""
        try:
            return next((s for s in self.sites if s.site_name == site_name), None)
        except Exception:
            return None
    
    def update_nginx_path(self, nginx_path: str, config_path: str):
        """更新Nginx和配置路径."""
        self.nginx_service.set_paths(nginx_path, config_path)
        self.initialize()