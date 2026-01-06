"""Configuration pages for different site types."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, 
    QLineEdit, QPushButton, QCheckBox, QLabel, QFileDialog,
    QTextEdit, QGroupBox, QComboBox, QSpinBox, QSplitter
)
from PySide6.QtCore import Qt, Signal, Slot
from loguru import logger
from models.site_config import SiteConfigBase, StaticSiteConfig, PHPSiteConfig, ProxySiteConfig


class BaseConfigPage(QWidget):
    """
    配置页面基类
    
    提供通用表单和配置管理功能
    """
    
    config_saved = Signal()
    preview_requested = Signal()
    
    def __init__(self, main_viewmodel, page_title: str):
        """初始化配置页面."""
        super().__init__()
        self.main_viewmodel = main_viewmodel
        self.page_title = page_title
        self.original_site_name: str = ""
        
        self._setup_ui()
        self._connect_signals()
        
    def _setup_ui(self):
        """设置UI."""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)
        
        # 左侧：表单区域
        form_container = QWidget()
        form_layout = QVBoxLayout(form_container)
        form_layout.setContentsMargins(0, 0, 0, 0)
        
        # 标题
        title = QLabel(self.page_title)
        title.setStyleSheet("font-size: 16pt; font-weight: 600;")
        form_layout.addWidget(title)
        
        # 通用配置区域
        self._setup_common_form(form_layout)
        
        # 特定配置区域（由子类实现）
        self._setup_specific_form(form_layout)
        
        # HTTPS配置区域
        self._setup_https_form(form_layout)
        
        # 按钮区域
        self._setup_button_area(form_layout)
        
        # 添加弹簧
        form_layout.addStretch()
        
        main_layout.addWidget(form_container, 2)  # 2/3宽度
        
        # 右侧：预览区域
        preview_container = QWidget()
        preview_layout = QVBoxLayout(preview_container)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        
        preview_title = QLabel("配置预览")
        preview_title.setStyleSheet("font-size: 12pt; font-weight: 600;")
        preview_layout.addWidget(preview_title)
        
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setFontFamily("Courier New")
        self.preview_text.setFontPointSize(9)
        preview_layout.addWidget(self.preview_text)
        
        preview_controls = QHBoxLayout()
        
        self.update_preview_btn = QPushButton("更新预览")
        self.update_preview_btn.clicked.connect(self._update_preview)
        preview_controls.addWidget(self.update_preview_btn)
        
        self.copy_btn = QPushButton("复制配置")
        self.copy_btn.clicked.connect(self._copy_config)
        preview_controls.addWidget(self.copy_btn)
        
        preview_layout.addLayout(preview_controls)
        
        main_layout.addWidget(preview_container, 1)  # 1/3宽度
    
    def _setup_common_form(self, layout):
        """设置通用表单."""
        common_group = QGroupBox("基础配置")
        common_layout = QFormLayout()
        common_layout.setSpacing(8)
        
        # 站点名称
        self.site_name_edit = QLineEdit()
        self.site_name_edit.setPlaceholderText("输入站点名称")
        common_layout.addRow("站点名称:", self.site_name_edit)
        
        # 监听端口
        port_layout = QHBoxLayout()
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(80)
        port_layout.addWidget(self.port_spin)
        port_layout.addStretch()
        common_layout.addRow("监听端口:", port_layout)
        
        # 服务器名称
        self.server_name_edit = QLineEdit()
        self.server_name_edit.setPlaceholderText("localhost 或域名")
        common_layout.addRow("服务器名称:", self.server_name_edit)
        
        common_group.setLayout(common_layout)
        layout.addWidget(common_group)
    
    def _setup_https_form(self, layout):
        """设置HTTPS表单."""
        https_group = QGroupBox("HTTPS配置")
        https_layout = QVBoxLayout()
        https_layout.setSpacing(8)
        
        # HTTPS开关
        https_switch_layout = QHBoxLayout()
        self.https_check = QCheckBox("启用HTTPS")
        self.https_check.setToolTip("启用HTTPS需要SSL证书")
        self.https_check.stateChanged.connect(self._on_https_toggled)
        https_switch_layout.addWidget(self.https_check)
        https_switch_layout.addStretch()
        https_layout.addLayout(https_switch_layout)
        
        # SSL证书路径
        cert_layout = QHBoxLayout()
        self.ssl_cert_edit = QLineEdit()
        self.ssl_cert_edit.setPlaceholderText("选择SSL证书文件 (.crt/.pem)")
        self.ssl_cert_edit.setEnabled(False)
        cert_layout.addWidget(self.ssl_cert_edit)
        
        self.cert_browse_btn = QPushButton("浏览")
        self.cert_browse_btn.setEnabled(False)
        self.cert_browse_btn.clicked.connect(self._browse_cert)
        cert_layout.addWidget(self.cert_browse_btn)
        https_layout.addLayout(cert_layout)
        
        # SSL私钥路径
        key_layout = QHBoxLayout()
        self.ssl_key_edit = QLineEdit()
        self.ssl_key_edit.setPlaceholderText("选择SSL私钥文件 (.key)")
        self.ssl_key_edit.setEnabled(False)
        key_layout.addWidget(self.ssl_key_edit)
        
        self.key_browse_btn = QPushButton("浏览")
        self.key_browse_btn.setEnabled(False)
        self.key_browse_btn.clicked.connect(self._browse_key)
        key_layout.addWidget(self.key_browse_btn)
        https_layout.addLayout(key_layout)
        
        https_group.setLayout(https_layout)
        layout.addWidget(https_group)
    
    def _setup_button_area(self, layout):
        """设置按钮区域."""
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)
        
        # 左对齐：预览按钮
        self.preview_btn = QPushButton("预览配置")
        self.preview_btn.setToolTip("预览即将生成的Nginx配置")
        self.preview_btn.clicked.connect(self.preview_requested.emit)
        button_layout.addWidget(self.preview_btn)
        
        button_layout.addStretch()
        
        # 右对齐：保存/取消
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self._on_cancel)
        button_layout.addWidget(self.cancel_btn)
        
        self.save_btn = QPushButton("保存并应用")
        self.save_btn.setStyleSheet("font-weight: 600;")
        self.save_btn.clicked.connect(self._on_save)
        button_layout.addWidget(self.save_btn)
        
        layout.addLayout(button_layout)
    
    def _connect_signals(self):
        """连接信号."""
        # 表单值改变时更新预览
        self.site_name_edit.textChanged.connect(self._update_preview)
        self.port_spin.valueChanged.connect(self._update_preview)
        self.server_name_edit.textChanged.connect(self._update_preview)
        self.https_check.stateChanged.connect(self._update_preview)
        self.ssl_cert_edit.textChanged.connect(self._update_preview)
        self.ssl_key_edit.textChanged.connect(self._update_preview)
    
    # 抽象方法（由子类实现）
    def _setup_specific_form(self, layout):
        """设置特定表单（子类实现）."""
        pass
    
    def get_config(self) -> SiteConfigBase:
        """获取配置（子类实现）."""
        pass
    
    def load_site(self, site_config: SiteConfigBase):
        """加载站点（子类实现）."""
        pass
    
    def new_site(self):
        """新建站点."""
        self.original_site_name = ""
        self._clear_fields()
    
    def is_editing(self) -> bool:
        """是否在编辑模式."""
        return bool(self.original_site_name)
    
    def get_original_site_name(self) -> str:
        """获取原始站点名称."""
        return self.original_site_name
    
    # 槽函数
    def _on_https_toggled(self, state):
        """HTTPS开关切换."""
        enabled = state == Qt.Checked
        self.ssl_cert_edit.setEnabled(enabled)
        self.ssl_key_edit.setEnabled(enabled)
        self.cert_browse_btn.setEnabled(enabled)
        self.key_browse_btn.setEnabled(enabled)
        self._update_preview()
    
    def _browse_cert(self):
        """浏览证书."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择SSL证书",
            "",
            "证书文件 (*.crt *.pem *.cer);;所有文件 (*.*)"
        )
        if file_path:
            self.ssl_cert_edit.setText(file_path)
    
    def _browse_key(self):
        """浏览私钥."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择SSL私钥",
            "",
            "密钥文件 (*.key *.pem);;所有文件 (*.*)"
        )
        if file_path:
            self.ssl_key_edit.setText(file_path)
    
    def _on_save(self):
        """保存配置."""
        config = self.get_config()
        if config:
            self.config_saved.emit()
    
    def _on_cancel(self):
        """取消编辑."""
        self.new_site()
        self._update_preview()
    
    def _update_preview(self):
        """更新预览."""
        try:
            config = self.get_config()
            if config:
                config_content = self.main_viewmodel.config_generator.generate_config(config)
                self.preview_text.setPlainText(config_content)
            else:
                self.preview_text.setPlainText("配置无效，请检查输入")
        except Exception as e:
            self.preview_text.setPlainText(f"配置生成错误: {str(e)}")
    
    def _copy_config(self):
        """复制配置到剪贴板."""
        self.preview_text.selectAll()
        self.preview_text.copy()
    
    def _clear_fields(self):
        """清空表单."""
        self.site_name_edit.clear()
        self.port_spin.setValue(80)
        self.server_name_edit.setText("localhost")
        self.https_check.setChecked(False)
        self.ssl_cert_edit.clear()
        self.ssl_key_edit.clear()
        self.preview_text.clear()


class StaticSitePage(BaseConfigPage):
    """静态站点配置页面."""
    
    def __init__(self, main_viewmodel):
        """初始化静态站点页面."""
        super().__init__(main_viewmodel, "静态站点配置")
    
    def _setup_specific_form(self, layout):
        """设置静态站点特定表单."""
        specific_group = QGroupBox("静态站点设置")
        specific_layout = QFormLayout()
        specific_layout.setSpacing(8)
        
        # 网站根目录
        root_layout = QHBoxLayout()
        self.root_edit = QLineEdit()
        self.root_edit.setPlaceholderText("选择网站根目录")
        root_layout.addWidget(self.root_edit)
        
        self.root_browse_btn = QPushButton("浏览")
        self.root_browse_btn.clicked.connect(self._browse_root)
        root_layout.addWidget(self.root_browse_btn)
        specific_layout.addRow("网站根目录:", root_layout)
        
        # 索引文件
        self.index_edit = QLineEdit("index.html")
        self.index_edit.setPlaceholderText("index.html")
        specific_layout.addRow("索引文件:", self.index_edit)
        
        specific_group.setLayout(specific_layout)
        layout.addWidget(specific_group)
        
        # 连接信号
        self.root_edit.textChanged.connect(self._update_preview)
        self.index_edit.textChanged.connect(self._update_preview)
    
    def get_config(self) -> StaticSiteConfig:
        """获取静态站点配置."""
        try:
            return StaticSiteConfig(
                site_name=self.site_name_edit.text(),
                listen_port=self.port_spin.value(),
                server_name=self.server_name_edit.text(),
                enable_https=self.https_check.isChecked(),
                ssl_cert_path=self.ssl_cert_edit.text() if self.https_check.isChecked() else None,
                ssl_key_path=self.ssl_key_edit.text() if self.https_check.isChecked() else None,
                root_path=self.root_edit.text(),
                index_file=self.index_edit.text() or "index.html"
            )
        except Exception as e:
            logger.error(f"Failed to create static config: {e}")
            return None
    
    def load_site(self, site_config: StaticSiteConfig):
        """加载站点."""
        self.original_site_name = site_config.site_name
        
        self.site_name_edit.setText(site_config.site_name)
        self.port_spin.setValue(site_config.listen_port)
        self.server_name_edit.setText(site_config.server_name)
        self.https_check.setChecked(site_config.enable_https)
        
        if site_config.enable_https:
            self.ssl_cert_edit.setText(site_config.ssl_cert_path or "")
            self.ssl_key_edit.setText(site_config.ssl_key_path or "")
        
        self.root_edit.setText(site_config.root_path)
        self.index_edit.setText(site_config.index_file)
        
        self._update_preview()
    
    def _browse_root(self):
        """浏览根目录."""
        directory = QFileDialog.getExistingDirectory(
            self,
            "选择网站根目录",
            self.root_edit.text() or ""
        )
        if directory:
            self.root_edit.setText(directory)


class PHPSitePage(BaseConfigPage):
    """PHP站点配置页面."""
    
    def __init__(self, main_viewmodel):
        """初始化PHP站点页面."""
        super().__init__(main_viewmodel, "PHP站点配置")
    
    def _setup_specific_form(self, layout):
        """设置PHP站点特定表单."""
        php_group = QGroupBox("PHP设置")
        php_layout = QVBoxLayout()
        php_layout.setSpacing(8)
        
        # PHP-FPM连接方式
        mode_layout = QHBoxLayout()
        self.php_mode_combo = QComboBox()
        self.php_mode_combo.addItems(["Unix Socket", "TCP"])
        self.php_mode_combo.currentIndexChanged.connect(self._on_php_mode_changed)
        mode_layout.addWidget(self.php_mode_combo)
        mode_layout.addStretch()
        php_layout.addLayout(mode_layout)
        
        # Socket配置
        socket_layout = QHBoxLayout()
        self.php_socket_edit = QLineEdit("/run/php/php-fpm.sock")
        socket_layout.addWidget(self.php_socket_edit)
        php_layout.addLayout(socket_layout)
        
        # TCP配置（初始隐藏）
        tcp_widget = QWidget()
        tcp_layout = QHBoxLayout(tcp_widget)
        tcp_layout.setContentsMargins(0, 0, 0, 0)
        
        self.php_host_edit = QLineEdit("127.0.0.1")
        tcp_layout.addWidget(QLabel("主机:"))
        tcp_layout.addWidget(self.php_host_edit)
        
        self.php_port_spin = QSpinBox()
        self.php_port_spin.setRange(1, 65535)
        self.php_port_spin.setValue(9000)
        tcp_layout.addWidget(QLabel("端口:"))
        tcp_layout.addWidget(self.php_port_spin)
        
        php_layout.addWidget(tcp_widget)
        
        php_group.setLayout(php_layout)
        layout.addWidget(php_group)
        
        # 网站根目录
        root_group = QGroupBox("网站设置")
        root_layout = QFormLayout()
        
        root_path_layout = QHBoxLayout()
        self.root_edit = QLineEdit()
        self.root_browse_btn = QPushButton("浏览")
        self.root_browse_btn.clicked.connect(self._browse_root)
        root_path_layout.addWidget(self.root_edit)
        root_path_layout.addWidget(self.root_browse_btn)
        root_layout.addRow("网站根目录:", root_path_layout)
        
        root_group.setLayout(root_layout)
        layout.addWidget(root_group)
        
        # 连接信号
        self.php_socket_edit.textChanged.connect(self._update_preview)
        self.php_host_edit.textChanged.connect(self._update_preview)
        self.php_port_spin.valueChanged.connect(self._update_preview)
        self.root_edit.textChanged.connect(self._update_preview)
    
    def _on_php_mode_changed(self, index):
        """PHP模式改变."""
        is_unix = index == 0
        self.php_socket_edit.setEnabled(is_unix)
        self.php_host_edit.setEnabled(not is_unix)
        self.php_port_spin.setEnabled(not is_unix)
    
    def get_config(self) -> PHPSiteConfig:
        """获取PHP站点配置."""
        try:
            is_unix = self.php_mode_combo.currentIndex() == 0
            
            return PHPSiteConfig(
                site_name=self.site_name_edit.text(),
                listen_port=self.port_spin.value(),
                server_name=self.server_name_edit.text(),
                enable_https=self.https_check.isChecked(),
                ssl_cert_path=self.ssl_cert_edit.text() if self.https_check.isChecked() else None,
                ssl_key_path=self.ssl_key_edit.text() if self.https_check.isChecked() else None,
                root_path=self.root_edit.text(),
                php_fpm_mode="unix" if is_unix else "tcp",
                php_fpm_socket=self.php_socket_edit.text() if is_unix else None,
                php_fpm_host=self.php_host_edit.text() if not is_unix else None,
                php_fpm_port=self.php_port_spin.value() if not is_unix else None
            )
        except Exception as e:
            logger.error(f"Failed to create PHP config: {e}")
            return None
    
    def load_site(self, site_config: PHPSiteConfig):
        """加载站点."""
        self.original_site_name = site_config.site_name
        
        self.site_name_edit.setText(site_config.site_name)
        self.port_spin.setValue(site_config.listen_port)
        self.server_name_edit.setText(site_config.server_name)
        self.https_check.setChecked(site_config.enable_https)
        
        if site_config.enable_https:
            self.ssl_cert_edit.setText(site_config.ssl_cert_path or "")
            self.ssl_key_edit.setText(site_config.ssl_key_path or "")
        
        self.root_edit.setText(site_config.root_path)
        
        # PHP配置
        if site_config.php_fpm_mode == "unix":
            self.php_mode_combo.setCurrentIndex(0)
            self.php_socket_edit.setText(site_config.php_fpm_socket or "/run/php/php-fpm.sock")
        else:
            self.php_mode_combo.setCurrentIndex(1)
            self.php_host_edit.setText(site_config.php_fpm_host or "127.0.0.1")
            self.php_port_spin.setValue(site_config.php_fpm_port or 9000)
        
        self._update_preview()
    
    def _browse_root(self):
        """浏览根目录."""
        directory = QFileDialog.getExistingDirectory(
            self,
            "选择网站根目录",
            self.root_edit.text() or ""
        )
        if directory:
            self.root_edit.setText(directory)


class ProxySitePage(BaseConfigPage):
    """反向代理配置页面."""
    
    def __init__(self, main_viewmodel):
        """初始化反向代理页面."""
        super().__init__(main_viewmodel, "反向代理配置")
    
    def _setup_specific_form(self, layout):
        """设置反向代理特定表单."""
        proxy_group = QGroupBox("反向代理设置")
        proxy_layout = QFormLayout()
        proxy_layout.setSpacing(8)
        
        # 后端地址
        self.proxy_url_edit = QLineEdit()
        self.proxy_url_edit.setPlaceholderText("http://localhost:8080")
        proxy_layout.addRow("后端地址:", self.proxy_url_edit)
        
        # 路径前缀
        self.location_edit = QLineEdit("/")
        self.location_edit.setPlaceholderText("/")
        proxy_layout.addRow("路径前缀:", self.location_edit)
        
        # WebSocket支持
        self.websocket_check = QCheckBox("启用WebSocket支持")
        self.websocket_check.setToolTip("为WebSocket应用启用升级支持")
        proxy_layout.addRow("", self.websocket_check)
        
        proxy_group.setLayout(proxy_layout)
        layout.addWidget(proxy_group)
        
        # 连接信号
        self.proxy_url_edit.textChanged.connect(self._update_preview)
        self.location_edit.textChanged.connect(self._update_preview)
        self.websocket_check.stateChanged.connect(self._update_preview)
    
    def get_config(self) -> ProxySiteConfig:
        """获取反向代理配置."""
        try:
            return ProxySiteConfig(
                site_name=self.site_name_edit.text(),
                listen_port=self.port_spin.value(),
                server_name=self.server_name_edit.text(),
                enable_https=self.https_check.isChecked(),
                ssl_cert_path=self.ssl_cert_edit.text() if self.https_check.isChecked() else None,
                ssl_key_path=self.ssl_key_edit.text() if self.https_check.isChecked() else None,
                proxy_pass_url=self.proxy_url_edit.text(),
                location_path=self.location_edit.text() or "/",
                enable_websocket=self.websocket_check.isChecked()
            )
        except Exception as e:
            logger.error(f"Failed to create proxy config: {e}")
            return None
    
    def load_site(self, site_config: ProxySiteConfig):
        """加载站点."""
        self.original_site_name = site_config.site_name
        
        self.site_name_edit.setText(site_config.site_name)
        self.port_spin.setValue(site_config.listen_port)
        self.server_name_edit.setText(site_config.server_name)
        self.https_check.setChecked(site_config.enable_https)
        
        if site_config.enable_https:
            self.ssl_cert_edit.setText(site_config.ssl_cert_path or "")
            self.ssl_key_edit.setText(site_config.ssl_key_path or "")
        
        self.proxy_url_edit.setText(site_config.proxy_pass_url)
        self.location_edit.setText(site_config.location_path)
        self.websocket_check.setChecked(site_config.enable_websocket)
        
        self._update_preview()