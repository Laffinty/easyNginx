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
        self.site_items: list[SiteListItem] = []
        
        self._setup_ui()
        self._connect_signals()
        
        logger.info("SiteListWidget initialized")
    
    def _setup_ui(self):
        """设置UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # 顶部标题和搜索
        top_layout = QHBoxLayout()
        
        title = QLabel("站点列表")
        title.setStyleSheet("font-size: 14pt; font-weight: 600;")
        top_layout.addWidget(title)
        
        top_layout.addStretch()
        
        # 搜索框
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索站点...")
        self.search_edit.setFixedWidth(200)
        top_layout.addWidget(self.search_edit)
        
        layout.addLayout(top_layout)
        
        # 添加站点按钮组
        button_layout = QHBoxLayout()
        
        add_static_btn = QPushButton("+ 静态站点")
        add_static_btn.setToolTip("添加静态HTML站点")
        add_static_btn.clicked.connect(self.add_static_site.emit)
        button_layout.addWidget(add_static_btn)
        
        add_php_btn = QPushButton("+ PHP站点")
        add_php_btn.setToolTip("添加PHP动态站点")
        add_php_btn.clicked.connect(self.add_php_site.emit)
        button_layout.addWidget(add_php_btn)
        
        add_proxy_btn = QPushButton("+ 反向代理")
        add_proxy_btn.setToolTip("添加反向代理站点")
        add_proxy_btn.clicked.connect(self.add_proxy_site.emit)
        button_layout.addWidget(add_proxy_btn)
        
        layout.addLayout(button_layout)
        
        # 站点表格
        self.site_table = QTableView()
        self.site_table.setAlternatingRowColors(True)
        self.site_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.site_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.site_table.horizontalHeader().setStretchLastSection(True)
        self.site_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.site_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.site_table.customContextMenuRequested.connect(self._show_context_menu)
        
        # 设置模型
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(["站点", "类型", "端口", "域名", "HTTPS"])
        self.site_table.setModel(self.model)
        
        layout.addWidget(self.site_table)
        
        # 底部统计信息
        self.status_label = QLabel("共 0 个站点")
        layout.addWidget(self.status_label)
    
    def _connect_signals(self):
        """连接信号."""
        # ViewModel信号
        self.main_viewmodel.site_list_changed.connect(self.update_sites)
        
        # UI信号
        self.search_edit.textChanged.connect(self._on_search_changed)
        self.site_table.selectionModel().selectionChanged.connect(self._on_selection_changed)
        self.site_table.doubleClicked.connect(self._on_double_clicked)
    
    def _show_context_menu(self, position):
        """显示右键菜单."""
        index = self.site_table.indexAt(position)
        if index.isValid():
            site_name = self.model.item(index.row(), 0).data(Qt.UserRole)
            
            menu = QMenu()
            
            edit_action = QAction("编辑", self)
            edit_action.triggered.connect(lambda: self._edit_site(site_name))
            menu.addAction(edit_action)
            
            delete_action = QAction("删除", self)
            delete_action.triggered.connect(lambda: self._confirm_delete(site_name))
            menu.addAction(delete_action)
            
            menu.exec(self.site_table.mapToGlobal(position))
    
    @Slot(list)
    def update_sites(self, site_items: list[SiteListItem]):
        """更新站点列表."""
        self.site_items = site_items
        self._refresh_table()
        
        # 更新统计
        total = len(site_items)
        static_count = sum(1 for item in site_items if item.site_type == "static")
        php_count = sum(1 for item in site_items if item.site_type == "php")
        proxy_count = sum(1 for item in site_items if item.site_type == "proxy")
        
        self.status_label.setText(
            f"共 {total} 个站点（静态: {static_count}, PHP: {php_count}, 代理: {proxy_count}）"
        )
    
    def _refresh_table(self):
        """刷新表格."""
        self.model.setRowCount(0)
        
        for item in self.site_items:
            row = []
            
            # 站点名称（带HTTPS图标）
            name_item = QStandardItem()
            display_name = item.get_display_name()
            name_item.setText(display_name)
            name_item.setData(item.site_name, Qt.UserRole)  # 存储原始名称
            row.append(name_item)
            
            # 类型
            type_item = QStandardItem()
            type_map = {"static": "静态", "php": "PHP", "proxy": "代理"}
            type_name = type_map.get(item.site_type, item.site_type)
            type_item.setText(type_name)
            row.append(type_item)
            
            # 端口
            port_item = QStandardItem()
            port_item.setText(str(item.listen_port))
            port_item.setTextAlignment(Qt.AlignCenter)
            row.append(port_item)
            
            # 域名
            domain_item = QStandardItem()
            domain_item.setText(item.server_name)
            row.append(domain_item)
            
            # HTTPS
            https_item = QStandardItem()
            https_item.setText("是" if item.enable_https else "否")
            https_item.setTextAlignment(Qt.AlignCenter)
            row.append(https_item)
            
            self.model.appendRow(row)
        
        # 设置行高
        self.site_table.verticalHeader().setDefaultSectionSize(28)
    
    def _on_search_changed(self, text):
        """搜索文本改变."""
        filter_text = text.strip()
        
        if filter_text:
            filtered_items = [
                item for item in self.site_items
                if (filter_text.lower() in item.site_name.lower() or
                    filter_text.lower() in item.server_name.lower() or
                    filter_text.lower() in item.site_type.lower())
            ]
            self._update_display_items(filtered_items)
        else:
            self._update_display_items(self.site_items)
    
    def _update_display_items(self, items: list[SiteListItem]):
        """更新显示项."""
        # 保存当前选择
        selected = self.site_table.selectionModel().currentIndex()
        selected_name = None
        if selected.isValid():
            selected_name = self.model.item(selected.row(), 0).data(Qt.UserRole)
        
        # 刷新表格
        self._refresh_table()
        
        # 恢复选择
        if selected_name:
            for row in range(self.model.rowCount()):
                name_item = self.model.item(row, 0)
                if name_item.data(Qt.UserRole) == selected_name:
                    self.site_table.selectRow(row)
                    break
    
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
        """确认删除."""
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除站点 '{site_name}' 吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.delete_site.emit(site_name)