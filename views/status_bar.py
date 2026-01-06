"""Status bar showing Nginx status and controls."""

from PySide6.QtWidgets import (
    QStatusBar, QLabel, QPushButton, QHBoxLayout, QWidget,
    QToolButton, QMenu
)
from PySide6.QtCore import Qt, Signal, Slot, QTimer
from PySide6.QtGui import QIcon, QColor, QPainter, QPixmap
from loguru import logger
from models.nginx_status import NginxStatus, NginxProcessStatus
from utils.language_manager import LanguageManager


class StatusBar(QStatusBar):
    """
    状态栏
    
    显示Nginx状态、提供控制按钮
    """
    
    status_clicked = Signal()  # 状态点击
    
    def __init__(self, main_viewmodel):
        """初始化状态栏."""
        super().__init__()
        self.main_viewmodel = main_viewmodel
        self.language_manager = LanguageManager()
        self._status = NginxStatus()
        self._blinking = False
        self._blink_timer = QTimer()
        self._blink_timer.timeout.connect(self._blink_status)
        
        self._setup_ui()
        self._connect_signals()
        
        logger.info("StatusBar initialized")
    
    def _setup_ui(self):
        """设置UI."""
        # 左侧：Nginx状态指示器
        status_widget = QWidget()
        status_layout = QHBoxLayout(status_widget)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(4)
        
        self.status_icon = QLabel()
        self.status_icon.setFixedSize(16, 16)
        self._update_status_icon()
        status_layout.addWidget(self.status_icon)
        
        self.status_text = QLabel(self.language_manager.get("nginx_not_running"))
        status_layout.addWidget(self.status_text)
        
        self.addWidget(status_widget)
        
        # 中间：状态信息
        self.info_text = QLabel()
        self.addPermanentWidget(self.info_text)
        
        # 右侧：控制按钮
        control_widget = QWidget()
        control_layout = QHBoxLayout(control_widget)
        control_layout.setContentsMargins(0, 0, 0, 0)
        control_layout.setSpacing(4)
        
        self.start_btn = QPushButton(self.language_manager.get("start"))
        self.start_btn.setFixedWidth(60)
        self.start_btn.clicked.connect(lambda: self.main_viewmodel.control_nginx("start"))
        control_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton(self.language_manager.get("stop"))
        self.stop_btn.setFixedWidth(60)
        self.stop_btn.clicked.connect(lambda: self.main_viewmodel.control_nginx("stop"))
        self.stop_btn.setEnabled(False)
        control_layout.addWidget(self.stop_btn)
        
        self.reload_btn = QPushButton(self.language_manager.get("reload"))
        self.reload_btn.setFixedWidth(60)
        self.reload_btn.clicked.connect(lambda: self.main_viewmodel.control_nginx("reload"))
        self.reload_btn.setEnabled(False)
        control_layout.addWidget(self.reload_btn)
        
        # 更多操作菜单
        self.more_btn = QToolButton()
        self.more_btn.setText(self.language_manager.get("more"))
        self.more_btn.setPopupMode(QToolButton.InstantPopup)
        
        menu = QMenu(self.more_btn)
        
        self.test_action = menu.addAction(self.language_manager.get("test_config"))
        self.test_action.triggered.connect(self.main_viewmodel.test_config)
        
        self.backup_action = menu.addAction(self.language_manager.get("backup_config"))
        self.backup_action.triggered.connect(self.main_viewmodel.backup_config)
        
        menu.addSeparator()
        
        self.open_dir_action = menu.addAction(self.language_manager.get("open_config_dir"))
        self.open_dir_action.triggered.connect(self.main_viewmodel.nginx_service.open_config_directory)
        
        self.open_editor_action = menu.addAction(self.language_manager.get("edit_config_file"))
        self.open_editor_action.triggered.connect(self.main_viewmodel.nginx_service.open_config_in_editor)
        
        self.more_btn.setMenu(menu)
        control_layout.addWidget(self.more_btn)
        
        self.addPermanentWidget(control_widget)
    
    def _connect_signals(self):
        """连接信号."""
        self.main_viewmodel.nginx_status_changed.connect(self.update_status)
        self.status_icon.mousePressEvent = lambda e: self.status_clicked.emit()
    
    @Slot(NginxStatus)
    def update_status(self, status: NginxStatus):
        """更新状态."""
        self._status = status
        
        # 更新状态文本
        status_text = f"Nginx {status.status.value}"
        if status.process_info and status.process_info.pid:
            status_text += f" (PID: {status.process_info.pid})"
        
        self.status_text.setText(status_text)
        
        # 更新状态图标
        self._update_status_icon()
        
        # 更新信息文本
        info_parts = []
        if status.total_sites > 0:
            info_parts.append(f"{self.language_manager.get('sites')}: {status.total_sites}")
        
        if status.process_info and status.is_running():
            info_parts.append(f"{self.language_manager.get('cpu_usage')}: {status.process_info.cpu_percent}%")
            info_parts.append(f"{self.language_manager.get('memory_usage')}: {status.get_memory_usage_mb():.1f}MB")
            info_parts.append(f"{self.language_manager.get('uptime')}: {status.get_uptime_display()}")
        
        self.info_text.setText(" | ".join(info_parts) if info_parts else "")
        
        # 更新按钮状态
        is_running = status.is_running()
        self.start_btn.setEnabled(not is_running)
        self.stop_btn.setEnabled(is_running)
        self.reload_btn.setEnabled(is_running)
        self.test_action.setEnabled(True)
        self.backup_action.setEnabled(True)
        self.open_dir_action.setEnabled(status.can_manage())
        self.open_editor_action.setEnabled(status.can_manage())
        
        # 停止闪烁
        if is_running and self._blinking:
            self._stop_blinking()
    
    def _update_status_icon(self):
        """更新状态图标."""
        # 创建彩色圆点图标
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 设置颜色
        color = self._status.get_status_color()
        painter.setBrush(QColor(color))
        painter.setPen(Qt.NoPen)
        
        # 绘制圆点
        painter.drawEllipse(2, 2, 12, 12)
        painter.end()
        
        self.status_icon.setPixmap(pixmap)
    
    def start_blinking(self):
        """开始闪烁（启动中）."""
        self._blinking = True
        self._blink_timer.start(500)  # 500ms间隔
    
    def _stop_blinking(self):
        """停止闪烁."""
        self._blinking = False
        self._blink_timer.stop()
        self._update_status_icon()
    
    def _blink_status(self):
        """闪烁状态."""
        if self.status_icon.isVisible():
            self.status_icon.setVisible(False)
        else:
            self.status_icon.setVisible(True)
    
    def paintEvent(self, event):
        """绘制事件."""
        super().paintEvent(event)
    
    def retranslate_ui(self):
        """重新翻译UI文本."""
        # 更新按钮文本
        self.start_btn.setText(self.language_manager.get("start"))
        self.stop_btn.setText(self.language_manager.get("stop"))
        self.reload_btn.setText(self.language_manager.get("reload"))
        self.more_btn.setText(self.language_manager.get("more"))
        
        # 更新菜单项文本
        self.test_action.setText(self.language_manager.get("test_config"))
        self.backup_action.setText(self.language_manager.get("backup_config"))
        self.open_dir_action.setText(self.language_manager.get("open_config_dir"))
        self.open_editor_action.setText(self.language_manager.get("edit_config_file"))
        
        # 更新当前状态显示
        self.update_status(self._status)