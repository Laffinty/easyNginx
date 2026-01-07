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
        status_text = f"Nginx {status.status}"
        if status.process_info and status.process_info.pid:
            status_text += f" (PID: {status.process_info.pid})"
        
        self.status_text.setText(status_text)
        
        # 更新状态图标
        self._update_status_icon()
        
        # 更新信息文本 - 站点统计
        if status.total_sites > 0:
            # 从sites_by_type字典获取各类型站点数量，默认为0
            static_count = status.sites_by_type.get("static", 0)
            php_count = status.sites_by_type.get("php", 0)
            proxy_count = status.sites_by_type.get("proxy", 0)
            
            site_stats = self.language_manager.get(
                "total_sites", 
                total=status.total_sites,
                static=static_count,
                php=php_count,
                proxy=proxy_count
            )
            self.info_text.setText(site_stats)
        else:
            self.info_text.setText("")
        
        # 如果Nginx正在运行，显示资源使用信息
        if status.process_info and status.is_running():
            resource_info = f"{self.language_manager.get('cpu_usage')}: {status.process_info.cpu_percent}% | {self.language_manager.get('memory_usage')}: {status.get_memory_usage_mb():.1f}MB | {self.language_manager.get('uptime')}: {status.get_uptime_display()}"
            if self.info_text.text():
                self.info_text.setText(f"{self.info_text.text()} | {resource_info}")
            else:
                self.info_text.setText(resource_info)
        
        # 更新按钮状态
        is_running = status.is_running()
        self.start_btn.setEnabled(not is_running)
        self.stop_btn.setEnabled(is_running)
        self.reload_btn.setEnabled(is_running)
        
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
        
        # 更新当前状态显示
        self.update_status(self._status)