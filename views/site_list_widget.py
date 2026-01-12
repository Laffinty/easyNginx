"""Site list widget for displaying and managing sites."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableView, QLineEdit,
    QPushButton, QLabel, QHeaderView, QAbstractItemView, QMessageBox,
    QMenu
)
from PySide6.QtCore import Qt, Signal, QSize, Slot
from PySide6.QtGui import QAction, QStandardItemModel, QStandardItem
from loguru import logger
from models.nginx_status import SiteListItem
from utils.language_manager import LanguageManager


class SiteListWidget(QWidget):
    """
    站点列表部件
    
    显示和管理所有站点，支持搜索、添加、删除
    """
    
    # 信号定义
    site_selected = Signal(str)  # 仅传递站点名称
    site_double_clicked = Signal(str)  # 仅传递站点名称
    site_selected_with_item = Signal(SiteListItem)  # 传递完整的站点项目
    add_static_site = Signal()
    add_php_site = Signal()
    add_proxy_site = Signal()
    delete_site = Signal(str)
    
    def __init__(self, main_viewmodel):
        """初始化站点列表部件."""
        super().__init__()
        self.main_viewmodel = main_viewmodel
        self.language_manager = LanguageManager()
        self.site_items: list[SiteListItem] = []
        
        self._setup_ui()
        self._connect_signals()
        
        logger.info("SiteListWidget initialized")
    
    def _setup_ui(self):
        """设置UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # 站点表格
        self.site_table = QTableView()
        self.site_table.setAlternatingRowColors(True)
        self.site_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.site_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.site_table.setEditTriggers(QAbstractItemView.NoEditTriggers)  # 禁用编辑
        self.site_table.setFocusPolicy(Qt.NoFocus)  # 去掉焦点框
        self.site_table.horizontalHeader().setStretchLastSection(True)
        self.site_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.site_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.site_table.customContextMenuRequested.connect(self._show_context_menu)
        
        # Set up model with translated headers
        self.model = QStandardItemModel()
        headers = [
            self.main_viewmodel.language_manager.get("site"),
            self.main_viewmodel.language_manager.get("type"),
            self.main_viewmodel.language_manager.get("port"),
            self.main_viewmodel.language_manager.get("domain"),
            "HTTPS"
        ]
        self.model.setHorizontalHeaderLabels(headers)
        self.site_table.setModel(self.model)
        
        layout.addWidget(self.site_table)
        
        # 底部统计信息
        self.status_label = QLabel(self.language_manager.get("total_sites", total=0, static=0, php=0, proxy=0))
        layout.addWidget(self.status_label)
    
    def _connect_signals(self):
        """连接信号."""
        # ViewModel信号
        self.main_viewmodel.site_list_changed.connect(self.update_sites)
        
        # UI信号
        self.site_table.selectionModel().selectionChanged.connect(self._on_selection_changed)
        self.site_table.doubleClicked.connect(self._on_double_clicked)
    
    def update_headers(self):
        """Update table headers with current language."""
        headers = [
            self.main_viewmodel.language_manager.get("site"),
            self.main_viewmodel.language_manager.get("type"),
            self.main_viewmodel.language_manager.get("port"),
            self.main_viewmodel.language_manager.get("domain"),
            "HTTPS"
        ]
        self.model.setHorizontalHeaderLabels(headers)
        
        # 刷新表格内容以更新语言相关的文本（如yes/no）
        self._refresh_table()
    
    def _show_context_menu(self, position):
        """Show context menu."""
        index = self.site_table.indexAt(position)
        if index.isValid():
            site_name = self.model.item(index.row(), 0).data(Qt.UserRole)
            
            # 查找对应的 SiteListItem 对象
            site_item = next((item for item in self.site_items if item.site_name == site_name), None)
            
            # 创建菜单
            menu = QMenu(self.site_table)  # 指定父部件为 site_table
            
            # 添加编辑菜单项
            edit_action = QAction(self.main_viewmodel.language_manager.get("edit"), self)
            edit_action.triggered.connect(lambda: self._edit_site(site_name))
            menu.addAction(edit_action)
            
            # 添加分隔符
            menu.addSeparator()
            
            # 添加删除菜单项
            delete_action = QAction(self.main_viewmodel.language_manager.get("delete"), self)
            if site_item:
                delete_action.triggered.connect(lambda: self._confirm_delete(site_item))
            else:
                delete_action.triggered.connect(lambda: self._confirm_delete_site_name(site_name))
            menu.addAction(delete_action)
            
            # 显示菜单
            menu.exec(self.site_table.viewport().mapToGlobal(position))
    
    @Slot(list)
    def update_sites(self, site_items: list[SiteListItem]):
        """Update site list."""
        self.site_items = site_items
        self._refresh_table()
        
        # Update statistics
        total = len(site_items)
        static_count = sum(1 for item in site_items if item.site_type == "static")
        php_count = sum(1 for item in site_items if item.site_type == "php")
        proxy_count = sum(1 for item in site_items if item.site_type == "proxy")
        
        self.status_label.setText(
            self.main_viewmodel.language_manager.get("total_sites", 
                total=total, static=static_count, php=php_count, proxy=proxy_count
            )
        )
    
    def _refresh_table(self):
        """Refresh table - 所有站点统一显示，不再区分管理/非管理."""
        # Get translations
        static_text = self.main_viewmodel.language_manager.get("static_site")
        php_text = self.main_viewmodel.language_manager.get("php_site")
        proxy_text = self.main_viewmodel.language_manager.get("proxy_site")
        yes_text = self.main_viewmodel.language_manager.get("yes")
        no_text = self.main_viewmodel.language_manager.get("no")
        
        self.model.setRowCount(0)
        
        for item in self.site_items:
            row = []
            
            # Site name (移除管理状态图标，统一显示)
            name_item = QStandardItem()
            display_name = item.get_display_name()
            name_item.setText(display_name)
            name_item.setData(item.site_name, Qt.UserRole)  # Store original name
            row.append(name_item)
            
            # Type
            type_item = QStandardItem()
            type_map = {"static": static_text, "php": php_text, "proxy": proxy_text}
            type_name = type_map.get(item.site_type, item.site_type)
            type_item.setText(type_name)
            row.append(type_item)
            
            # Port
            port_item = QStandardItem()
            if item.enable_https and item.enable_http_redirect:
                # 显示HTTPS端口和80重定向（格式：443/80(重定向)）
                redirect_text = self.main_viewmodel.language_manager.get("redirect")
                port_display = f"{item.listen_port}/80({redirect_text})"
                port_item.setText(port_display)
            else:
                port_item.setText(str(item.listen_port))
            port_item.setTextAlignment(Qt.AlignCenter)
            row.append(port_item)
            
            # Domain
            domain_item = QStandardItem()
            domain_item.setText(item.server_name)
            row.append(domain_item)
            
            # HTTPS
            https_item = QStandardItem()
            https_item.setText(yes_text if item.enable_https else no_text)
            https_item.setTextAlignment(Qt.AlignCenter)
            row.append(https_item)
            
            self.model.appendRow(row)
        
        # Set row height
        self.site_table.verticalHeader().setDefaultSectionSize(28)
    
    def _on_selection_changed(self):
        """选择改变."""
        selected = self.site_table.selectionModel().currentIndex()
        if selected.isValid():
            site_name = self.model.item(selected.row(), 0).data(Qt.UserRole)
            logger.debug(f"Site selected: {site_name}")
    
    def _on_double_clicked(self, index):
        """双击."""
        if index.isValid():
            site_name = self.model.item(index.row(), 0).data(Qt.UserRole)
            # 查找完整的SiteListItem
            site_item = next((item for item in self.site_items if item.site_name == site_name), None)
            if site_item:
                self.site_selected_with_item.emit(site_item)
            else:
                self.site_selected.emit(site_name)
    
    def _edit_site(self, site_name: str):
        """编辑站点."""
        self.site_selected.emit(site_name)
    
    def _confirm_delete(self, site_item: SiteListItem):
        """Confirm delete - 所有站点都可以删除."""
        reply = QMessageBox.question(
            self,
            self.main_viewmodel.language_manager.get("confirm_delete"),
            self.main_viewmodel.language_manager.get("delete_confirm_message", name=site_item.site_name),
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # 发送站点名称（字符串），而不是 SiteListItem 对象
            self.delete_site.emit(site_item.site_name)
    
    def _confirm_delete_site_name(self, site_name: str):
        """Confirm delete by site name only (fallback)."""
        reply = QMessageBox.question(
            self,
            self.main_viewmodel.language_manager.get("confirm_delete"),
            self.main_viewmodel.language_manager.get("delete_confirm_message", name=site_name),
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # 直接发送站点名称字符串
            self.delete_site.emit(site_name)