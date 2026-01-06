"""Main application window."""

from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
    QSplitter, QMessageBox, QFileDialog, QDialog
)
from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtGui import QIcon
from loguru import logger
from models.nginx_status import NginxStatus
from viewmodels.main_viewmodel import MainViewModel
from views.site_list_widget import SiteListWidget
from views.config_pages import StaticSitePage, PHPSitePage, ProxySitePage
from views.status_bar import StatusBar
from utils.theme_manager import ThemeManager
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
        """初始化主窗口."""
        super().__init__()
        self.main_viewmodel = main_viewmodel
        self.theme_manager = ThemeManager()
        self.config_generator = ConfigGenerator()
        
        # 初始化UI
        self._setup_ui()
        self._connect_signals()
        
        logger.info("MainWindow initialized")
    
    def _setup_ui(self):
        """设置UI."""
        self.setWindowTitle("easyNginx - Professional Nginx Management")
        self.setMinimumSize(1200, 800)
        
        # 中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 分割器（左右布局）
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # 左侧：站点列表
        self.site_list_widget = SiteListWidget(self.main_viewmodel)
        splitter.addWidget(self.site_list_widget)
        
        # 右侧：堆叠页面（配置区域）
        self.config_page_widget = QWidget()
        config_layout = QVBoxLayout(self.config_page_widget)
        config_layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建三种配置页面
        self.static_page = StaticSitePage(self.main_viewmodel)
        self.php_page = PHPSitePage(self.main_viewmodel)
        self.proxy_page = ProxySitePage(self.main_viewmodel)
        
        # 将页面添加到堆叠布局
        config_layout.addWidget(self.static_page)
        config_layout.addWidget(self.php_page)
        config_layout.addWidget(self.proxy_page)
        
        # 初始只显示静态页面
        self.php_page.hide()
        self.proxy_page.hide()
        self.current_page = self.static_page
        
        splitter.addWidget(self.config_page_widget)
        
        # 设置分割器比例
        splitter.setStretchFactor(0, 1)  # 左侧站点列表
        splitter.setStretchFactor(1, 2)  # 右侧配置区域
        
        # 底部状态栏
        self.status_bar = StatusBar(self.main_viewmodel)
        self.setStatusBar(self.status_bar)
        
        # 创建菜单栏
        self._create_menu_bar()
        
        # 应用初始主题
        self._apply_theme(self.theme_manager.current_theme)
    
    def _create_menu_bar(self):
        """创建菜单栏."""
        menu_bar = self.menuBar()
        
        # 文件菜单
        file_menu = menu_bar.addMenu("文件(&F)")
        
        # 接管Nginx目录
        nginx_action = file_menu.addAction("接管Nginx目录")
        nginx_action.triggered.connect(self._on_set_nginx_path)
        
        file_menu.addSeparator()
        
        # 退出
        exit_action = file_menu.addAction("退出")
        exit_action.triggered.connect(self.close)
        
        # 操作菜单
        action_menu = menu_bar.addMenu("操作(&O)")
        
        # 启动/停止/重载
        self.start_action = action_menu.addAction("启动Nginx")
        self.start_action.triggered.connect(lambda: self.main_viewmodel.control_nginx("start"))
        
        self.stop_action = action_menu.addAction("停止Nginx")
        self.stop_action.triggered.connect(lambda: self.main_viewmodel.control_nginx("stop"))
        
        self.reload_action = action_menu.addAction("重载配置")
        self.reload_action.triggered.connect(lambda: self.main_viewmodel.control_nginx("reload"))
        
        action_menu.addSeparator()
        
        # 测试配置
        test_action = action_menu.addAction("测试配置语法")
        test_action.triggered.connect(self.main_viewmodel.test_config)
        
        # 备份
        backup_action = action_menu.addAction("备份配置文件")
        backup_action.triggered.connect(self.main_viewmodel.backup_config)
        
        # 主题菜单
        theme_menu = menu_bar.addMenu("主题(&T)")
        
        for theme_id, theme_name in ThemeManager.THEMES.items():
            action = theme_menu.addAction(theme_name)
            action.setCheckable(True)
            action.setChecked(theme_id == self.theme_manager.current_theme)
            action.triggered.connect(lambda checked, t=theme_id: self._on_theme_changed(t))
        
        # 帮助菜单
        help_menu = menu_bar.addMenu("帮助(&H)")
        
        about_action = help_menu.addAction("关于")
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
        self.site_list_widget.add_static_site.connect(self._on_add_static_site)
        self.site_list_widget.add_php_site.connect(self._on_add_php_site)
        self.site_list_widget.add_proxy_site.connect(self._on_add_proxy_site)
        self.site_list_widget.delete_site.connect(self._on_delete_site)
        
        # 配置页面信号
        self.static_page.config_saved.connect(self._on_config_saved)
        self.static_page.preview_requested.connect(self._on_preview_requested)
        self.php_page.config_saved.connect(self._on_config_saved)
        self.php_page.preview_requested.connect(self._on_preview_requested)
        self.proxy_page.config_saved.connect(self._on_config_saved)
        self.proxy_page.preview_requested.connect(self._on_preview_requested)
    
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
        """站点被选中."""
        site = self.main_viewmodel.get_site_by_name(site_name)
        if site:
            # 根据站点类型切换页面
            if site.site_type == "static":
                self._switch_to_page(self.static_page)
                self.static_page.load_site(site)
            elif site.site_type == "php":
                self._switch_to_page(self.php_page)
                self.php_page.load_site(site)
            elif site.site_type == "proxy":
                self._switch_to_page(self.proxy_page)
                self.proxy_page.load_site(site)
    
    def _on_add_static_site(self):
        """添加静态站点."""
        self._switch_to_page(self.static_page)
        self.static_page.new_site()
    
    def _on_add_php_site(self):
        """添加PHP站点."""
        self._switch_to_page(self.php_page)
        self.php_page.new_site()
    
    def _on_add_proxy_site(self):
        """添加代理站点."""
        self._switch_to_page(self.proxy_page)
        self.proxy_page.new_site()
    
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
    
    @Slot()
    def _on_config_saved(self):
        """配置已保存."""
        # 通知ViewModel更新站点
        page = self.sender()
        site_config = page.get_config()
        
        if site_config:
            if page.is_editing():
                # 编辑模式
                old_name = page.get_original_site_name()
                self.main_viewmodel.update_site(old_name, site_config)
            else:
                # 新建模式
                self.main_viewmodel.add_site(site_config)
    
    @Slot()
    def _on_preview_requested(self):
        """预览请求."""
        page = self.sender()
        site_config = page.get_config()
        
        if site_config:
            # 生成并显示预览
            config_content = self.config_generator.generate_config(site_config)
            self.main_viewmodel.config_generated.emit(config_content)
    
    def _switch_to_page(self, page):
        """切换到指定页面."""
        # 隐藏所有页面
        self.static_page.hide()
        self.php_page.hide()
        self.proxy_page.hide()
        
        # 显示目标页面
        page.show()
        self.current_page = page
        
        logger.info(f"Switched to {page.__class__.__name__}")
    
    def _on_theme_changed(self, theme_id):
        """主题改变."""
        self.theme_manager.current_theme = theme_id
        self._apply_theme(theme_id)
        
        # 更新菜单项的选中状态
        for action in self.menuBar().findChildren(QAction):
            if action.text() in ThemeManager.THEMES.values():
                theme_key = list(ThemeManager.THEMES.keys())[list(ThemeManager.THEMES.values()).index(action.text())]
                action.setChecked(theme_key == theme_id)
    
    def _apply_theme(self, theme: str):
        """应用主题."""
        self.setStyleSheet(self.theme_manager.get_theme_qss(theme))
        logger.info(f"Applied theme: {theme}")
    
    def _on_set_nginx_path(self):
        """接管Nginx目录."""
        from utils.config_registry import ConfigRegistry
        from views.takeover_dialog import NginxTakeoverDialog
        
        dialog = NginxTakeoverDialog(self)
        
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
    
    def _on_about(self):
        """关于对话框."""
        about_text = """
        <h2>easyNginx v1.0</h2>
        <p><b>专业级Nginx图形化管理工具</b></p>
        <p>为系统管理员打造的高性能、安全可靠的Nginx配置管理解决方案</p>
        <hr>
        <p><b>核心特性：</b></p>
        <ul>
            <li>三种配置模式：静态站点、PHP动态站点、反向代理</li>
            <li>强制性能优化基线（F5/CIS最佳实践）</li>
            <li>可选HTTPS安全加固（TLS 1.2/1.3、HSTS、安全头等）</li>
            <li>智能配置解析和实时预览</li>
            <li>启动时间<3秒，内存占用<150MB</li>
            <li>支持暗色/亮色/高对比度主题</li>
        </ul>
        <hr>
        <p><b>技术栈：</b> Python 3.11+, PySide6, Pydantic, Jinja2, Loguru</p>
        <p><b>适用平台：</b> Windows 10/11 (x64)</p>
        <p><b>许可证：</b> 商业软件</p>
        <hr>
        <p>© 2026 easyNginx Team. All rights reserved.</p>
        """
        
        QMessageBox.about(self, "关于 easyNginx", about_text)
    
    def closeEvent(self, event):
        """关闭事件."""
        reply = QMessageBox.question(
            self,
            "退出确认",
            "确定要退出 easyNginx 吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # 清理资源
            self.main_viewmodel.cleanup()
            logger.info("Application closing...")
            event.accept()
        else:
            event.ignore()