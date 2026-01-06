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
    site_selected = Signal(str)
    site_double_clicked = Signal(str)
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
    
    def _show_context_menu(self, position):
        """Show context menu."""
        index = self.site_table.indexAt(position)
        if index.isValid():
            site_name = self.model.item(index.row(), 0).data(Qt.UserRole)
            
            menu = QMenu()
            
            edit_action = QAction(self.main_viewmodel.language_manager.get("edit"), self)
            edit_action.triggered.connect(lambda: self._edit_site(site_name))
            menu.addAction(edit_action)
            
            delete_action = QAction(self.main_viewmodel.language_manager.get("delete"), self)
            delete_action.triggered.connect(lambda: self._confirm_delete(site_name))
            menu.addAction(delete_action)
            
            menu.exec(self.site_table.mapToGlobal(position))
    
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
        """Refresh table."""
        # Get translations
        static_text = self.main_viewmodel.language_manager.get("static_site")
        php_text = self.main_viewmodel.language_manager.get("php_site")
        proxy_text = self.main_viewmodel.language_manager.get("proxy_site")
        yes_text = self.main_viewmodel.language_manager.get("yes")
        no_text = self.main_viewmodel.language_manager.get("no")
        
        self.model.setRowCount(0)
        
        for item in self.site_items:
            row = []
            
            # Site name (with HTTPS icon)
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
            self.site_selected.emit(site_name)
    
    def _edit_site(self, site_name: str):
        """编辑站点."""
        self.site_selected.emit(site_name)
    
    def _confirm_delete(self, site_name: str):
        """Confirm delete."""
        reply = QMessageBox.question(
            self,
            self.main_viewmodel.language_manager.get("confirm_delete"),
            self.main_viewmodel.language_manager.get("delete_confirm_message", name=site_name),
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.delete_site.emit(site_name)