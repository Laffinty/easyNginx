"""Main application window."""

from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
    QMessageBox, QFileDialog, QDialog
)
from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtGui import QIcon, QAction
from loguru import logger
from models.nginx_status import NginxStatus
from viewmodels.main_viewmodel import MainViewModel
from views.site_list_widget import SiteListWidget
from views.site_config_dialog import (
    StaticSiteConfigDialog, PHPSiteConfigDialog, ProxySiteConfigDialog
)
from views.status_bar import StatusBar
from utils.theme_manager import ThemeManager
from utils.language_manager import LanguageManager
from services.config_generator import ConfigGenerator


class MainWindow(QMainWindow):
    """
    主窗口
    
    职责：
    1. 整体布局和导航
    2. 菜单栏和工具栏
    3. 模式切换
    4. 全局错误处理
    """
    
    def __init__(self, main_viewmodel: MainViewModel):
        """Initialize main window."""
        super().__init__()
        self.main_viewmodel = main_viewmodel
        self.theme_manager = ThemeManager()
        self.language_manager = LanguageManager()
        self.config_generator = ConfigGenerator()
        
        # Store language menu actions for radio behavior
        self.language_actions = {}
        
        # Initialize UI
        self._setup_ui()
        self._connect_signals()
        
        logger.info("MainWindow initialized")
    
    def _setup_ui(self):
        """设置UI."""
        self.setWindowTitle("easyNginx - Professional Nginx Management")
        self.setMinimumSize(800, 600)
        
        # 中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局 - 只包含站点列表
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 站点列表（占据全部空间）
        self.site_list_widget = SiteListWidget(self.main_viewmodel)
        main_layout.addWidget(self.site_list_widget)
        
        # 底部状态栏
        self.status_bar = StatusBar(self.main_viewmodel)
        self.setStatusBar(self.status_bar)
        
        # 创建菜单栏
        self._create_menu_bar()
        
        # 应用初始主题
        self._apply_theme(self.theme_manager.current_theme)
    
    def _create_menu_bar(self):
        """Create menu bar."""
        menu_bar = self.menuBar()
        
        # File menu
        file_menu = menu_bar.addMenu(self.language_manager.get("file_menu"))
        
        # Takeover Nginx directory
        nginx_action = file_menu.addAction(self.language_manager.get("takeover_nginx"))
        nginx_action.triggered.connect(self._on_set_nginx_path)
        
        file_menu.addSeparator()
        
        # New site actions
        new_proxy_action = file_menu.addAction(self.language_manager.get("new_proxy"))
        new_proxy_action.triggered.connect(self._on_add_proxy_site)
        
        new_php_action = file_menu.addAction(self.language_manager.get("new_php"))
        new_php_action.triggered.connect(self._on_add_php_site)
        
        new_static_action = file_menu.addAction(self.language_manager.get("new_static"))
        new_static_action.triggered.connect(self._on_add_static_site)
        
        file_menu.addSeparator()
        
        # Exit
        exit_action = file_menu.addAction(self.language_manager.get("exit"))
        exit_action.triggered.connect(self.close)
        
        # Operation menu
        action_menu = menu_bar.addMenu(self.language_manager.get("operation_menu"))
        
        # Start/Stop/Reload
        self.start_action = action_menu.addAction(self.language_manager.get("start_nginx"))
        self.start_action.triggered.connect(lambda: self.main_viewmodel.control_nginx("start"))
        
        self.stop_action = action_menu.addAction(self.language_manager.get("stop_nginx"))
        self.stop_action.triggered.connect(lambda: self.main_viewmodel.control_nginx("stop"))
        
        self.reload_action = action_menu.addAction(self.language_manager.get("reload_config"))
        self.reload_action.triggered.connect(lambda: self.main_viewmodel.control_nginx("reload"))
        
        action_menu.addSeparator()
        
        # Test config
        test_action = action_menu.addAction(self.language_manager.get("test_config"))
        test_action.triggered.connect(self.main_viewmodel.test_config)
        
        # Backup
        backup_action = action_menu.addAction(self.language_manager.get("backup_config"))
        backup_action.triggered.connect(self.main_viewmodel.backup_config)
        
        # Language menu
        lang_menu = menu_bar.addMenu(self.language_manager.get("language_menu"))
        
        for lang_code, (display_name, native_name) in self.language_manager.SUPPORTED_LANGUAGES.items():
            action = lang_menu.addAction(native_name)
            action.setCheckable(True)
            action.setChecked(lang_code == self.language_manager.current_language)
            action.triggered.connect(lambda checked, l=lang_code: self._on_language_changed(l))
            self.language_actions[lang_code] = action  # Store for radio behavior
        
        # Help menu
        help_menu = menu_bar.addMenu(self.language_manager.get("help_menu"))
        
        about_action = help_menu.addAction(self.language_manager.get("about"))
        about_action.triggered.connect(self._on_about)
    
    def _connect_signals(self):
        """连接信号."""
        # MainViewModel信号
        self.main_viewmodel.nginx_status_changed.connect(self._on_nginx_status_changed)
        self.main_viewmodel.site_list_changed.connect(self._on_site_list_changed)
        self.main_viewmodel.operation_completed.connect(self._on_operation_completed)
        self.main_viewmodel.error_occurred.connect(self._on_error_occurred)
        self.main_viewmodel.config_generated.connect(self._on_config_generated)
        
        # UI信号
        self.site_list_widget.site_selected.connect(self._on_site_selected)
        self.site_list_widget.site_double_clicked.connect(self._on_site_selected)
        self.site_list_widget.delete_site.connect(self._on_delete_site)
    
    @Slot(NginxStatus)
    def _on_nginx_status_changed(self, status):
        """Nginx状态改变."""
        self.status_bar.update_status(status)
    
    @Slot(list)
    def _on_site_list_changed(self, site_items):
        """站点列表改变."""
        self.site_list_widget.update_sites(site_items)
    
    @Slot(bool, str)
    def _on_operation_completed(self, success, message):
        """操作完成."""
        if success:
            QMessageBox.information(self, "操作成功", message)
        else:
            QMessageBox.warning(self, "操作失败", message)
    
    @Slot(str)
    def _on_error_occurred(self, error):
        """错误发生."""
        QMessageBox.critical(self, "错误", error)
        logger.error(f"UI error: {error}")
    
    @Slot(str)
    def _on_config_generated(self, config_content):
        """配置已生成."""
        # 显示预览对话框
        from views.preview_dialog import ConfigPreviewDialog
        dialog = ConfigPreviewDialog(self, config_content)
        dialog.exec()
    
    @Slot(str)
    def _on_site_selected(self, site_name):
        """站点被选中（双击编辑）."""
        site = self.main_viewmodel.get_site_by_name(site_name)
        if site:
            self._edit_site(site)
    
    def _on_add_static_site(self):
        """添加静态站点."""
        dialog = StaticSiteConfigDialog(self.main_viewmodel, self, self.language_manager)
        if dialog.exec() == QDialog.Accepted:
            config = dialog.get_config()
            if config:
                self.main_viewmodel.add_site(config)
    
    def _on_add_php_site(self):
        """添加PHP站点."""
        dialog = PHPSiteConfigDialog(self.main_viewmodel, self, self.language_manager)
        if dialog.exec() == QDialog.Accepted:
            config = dialog.get_config()
            if config:
                self.main_viewmodel.add_site(config)
    
    def _on_add_proxy_site(self):
        """添加代理站点."""
        dialog = ProxySiteConfigDialog(self.main_viewmodel, self, self.language_manager)
        if dialog.exec() == QDialog.Accepted:
            config = dialog.get_config()
            if config:
                self.main_viewmodel.add_site(config)
    
    @Slot(str)
    def _on_delete_site(self, site_name):
        """删除站点."""
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除站点 '{site_name}' 吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.main_viewmodel.delete_site(site_name)
    

    
    def _edit_site(self, site):
        """编辑站点."""
        # 根据站点类型创建对应的对话框
        if site.site_type == "static":
            dialog = StaticSiteConfigDialog(self.main_viewmodel, self, self.language_manager)
            dialog.load_site(site)
            if dialog.exec() == QDialog.Accepted:
                config = dialog.get_config()
                if config:
                    self.main_viewmodel.update_site(site.site_name, config)
        elif site.site_type == "php":
            dialog = PHPSiteConfigDialog(self.main_viewmodel, self, self.language_manager)
            dialog.load_site(site)
            if dialog.exec() == QDialog.Accepted:
                config = dialog.get_config()
                if config:
                    self.main_viewmodel.update_site(site.site_name, config)
        elif site.site_type == "proxy":
            dialog = ProxySiteConfigDialog(self.main_viewmodel, self, self.language_manager)
            dialog.load_site(site)
            if dialog.exec() == QDialog.Accepted:
                config = dialog.get_config()
                if config:
                    self.main_viewmodel.update_site(site.site_name, config)
    
    def _on_language_changed(self, lang_code):
        """Language changed - update UI without restart."""
        if lang_code == self.language_manager.current_language:
            return
            
        # Update language manager
        self.language_manager.set_language(lang_code)
        
        # Implement radio button behavior: uncheck other actions
        for code, action in self.language_actions.items():
            action.setChecked(code == lang_code)
        
        # Update all UI text dynamically
        self._retranslate_ui()
        
        logger.info(f"Language switched to {lang_code}")
    
    def _apply_theme(self, theme: str):
        """应用主题."""
        self.setStyleSheet(self.theme_manager.get_theme_qss(theme))
        logger.info(f"Applied theme: {theme}")
    
    def _on_set_nginx_path(self):
        """接管Nginx目录."""
        from utils.config_registry import ConfigRegistry
        from views.takeover_dialog import NginxTakeoverDialog
        
        dialog = NginxTakeoverDialog(self, "", self.language_manager)
        
        if dialog.exec() == QDialog.Accepted:
            nginx_path, config_path = dialog.get_nginx_paths()
            
            if nginx_path and config_path:
                # 更新注册表
                config_registry = ConfigRegistry()
                config_registry.set_nginx_paths(nginx_path, config_path)
                config_registry.set_takeover_status(
                    True,
                    str(Path(nginx_path).parent),
                    str(Path(config_path).parent / "backups")
                )
                
                # 更新ViewModel
                self.main_viewmodel.update_nginx_path(nginx_path, config_path)
                QMessageBox.information(self, "接管完成", "Nginx目录已接管，配置已更新，请重新启动应用")
    
    def _retranslate_ui(self):
        """Dynamically update all UI text when language changes."""
        # Update window title
        self.setWindowTitle(self.language_manager.get("app_title"))
        
        # Recreate menu bar with new language
        self.menuBar().clear()
        self.language_actions.clear()
        self._create_menu_bar()
        
        # Update site list headers
        self.site_list_widget.update_headers()
        
        logger.info("UI text updated for new language")
    
    def _on_about(self):
        """About dialog."""
        about_text = self.language_manager.get("about_content")
        QMessageBox.about(self, self.language_manager.get("about_title"), about_text)
    
    def closeEvent(self, event):
        """Close event."""
        reply = QMessageBox.question(
            self,
            self.language_manager.get("confirm_exit"),
            self.language_manager.get("exit_confirm_message"),
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # 清理资源
            self.main_viewmodel.cleanup()
            logger.info("Application closing...")
            event.accept()
        else:
            event.ignore()