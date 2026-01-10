"""Theme management for UI theming."""

from PySide6.QtCore import QObject, Signal, Property, QTimer
from PySide6.QtGui import QPalette, QColor, QGuiApplication
from loguru import logger
import darkdetect


class ThemeManager(QObject):
    """
    Theme manager - automatically follows system theme.
    
    Automatically detects and applies system light/dark theme.
    """
    
    theme_changed = Signal(str)  # Theme changed signal
    
    AVAILABLE_THEMES = ["light", "dark"]
    
    def __init__(self):
        """Initialize theme manager."""
        super().__init__()
        self._current_theme = "light"
        self._theme_check_timer = QTimer()
        self._theme_check_timer.setInterval(1000)  # Check every second
        self._theme_check_timer.timeout.connect(self._check_system_theme_change)
        self._theme_check_timer.start()
        
        # Apply initial theme
        self._apply_initial_theme()
    
    @Property(str, notify=theme_changed)
    def current_theme(self) -> str:
        """Current theme."""
        return self._current_theme
    
    def _apply_initial_theme(self):
        """Apply initial theme based on system."""
        system_theme = self.detect_system_theme()
        if system_theme != self._current_theme:
            self._current_theme = system_theme
            self._apply_theme(system_theme)
            self.theme_changed.emit(system_theme)
    
    def _check_system_theme_change(self):
        """Check if system theme has changed."""
        try:
            system_theme = self.detect_system_theme()
            if system_theme != self._current_theme:
                self._current_theme = system_theme
                self._apply_theme(system_theme)
                self.theme_changed.emit(system_theme)
                logger.debug(f"System theme changed to: {system_theme}")
        except Exception as e:
            # Silently ignore errors in theme detection
            pass
    
    def detect_system_theme(self):
        """Detect system theme."""
        try:
            if darkdetect.isDark():
                return "dark"
            else:
                return "light"
        except Exception:
            return "light"
    
    def _apply_theme(self, theme: str):
        """应用主题."""
        app = QGuiApplication.instance()
        if not app:
            return
        
        palette = QPalette()
        
        if theme == "dark":
            # 暗色主题
            palette.setColor(QPalette.Window, QColor(32, 32, 32))
            palette.setColor(QPalette.WindowText, QColor(255, 255, 255))
            palette.setColor(QPalette.Base, QColor(42, 42, 42))
            palette.setColor(QPalette.AlternateBase, QColor(52, 52, 52))
            palette.setColor(QPalette.ToolTipBase, QColor(255, 255, 255))
            palette.setColor(QPalette.ToolTipText, QColor(255, 255, 255))
            palette.setColor(QPalette.Text, QColor(255, 255, 255))
            palette.setColor(QPalette.Button, QColor(42, 42, 42))
            palette.setColor(QPalette.ButtonText, QColor(255, 255, 255))
            palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
            palette.setColor(QPalette.Link, QColor(42, 130, 218))
            palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
            palette.setColor(QPalette.HighlightedText, QColor(0, 0, 0))
            
        elif theme == "high_contrast":
            # 高对比度主题
            palette.setColor(QPalette.Window, QColor(0, 0, 0))
            palette.setColor(QPalette.WindowText, QColor(255, 255, 0))
            palette.setColor(QPalette.Base, QColor(0, 0, 0))
            palette.setColor(QPalette.AlternateBase, QColor(20, 20, 20))
            palette.setColor(QPalette.ToolTipBase, QColor(255, 255, 255))
            palette.setColor(QPalette.ToolTipText, QColor(0, 0, 0))
            palette.setColor(QPalette.Text, QColor(255, 255, 255))
            palette.setColor(QPalette.Button, QColor(0, 0, 0))
            palette.setColor(QPalette.ButtonText, QColor(255, 255, 0))
            palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
            palette.setColor(QPalette.Link, QColor(255, 255, 0))
            palette.setColor(QPalette.Highlight, QColor(255, 255, 0))
            palette.setColor(QPalette.HighlightedText, QColor(0, 0, 0))
            
        else:
            # 亮色主题（默认）
            palette = QPalette()  # 使用默认亮色
        
        app.setPalette(palette)
    
    def get_theme_qss(self, theme: str) -> str:
        """获取主题的QSS样式."""
        if theme == "dark":
            return """
            QWidget {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QPushButton {
                background-color: #3c3c3c;
                color: #ffffff;
                border: 1px solid #555555;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #4c4c4c;
            }
            QLineEdit {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #555555;
                padding: 3px;
            }
            QTextEdit {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #555555;
            }
            QTableView {
                background-color: #2b2b2b;
                color: #ffffff;
                alternate-background-color: #323232;
            }
            QHeaderView::section {
                background-color: #3c3c3c;
                color: #ffffff;
            }
            QMenu {
                background-color: #3c3c3c;
                border: 1px solid #555555;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 24px 6px 24px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #0078d4;
                color: #ffffff;
            }
            QMenu::item:disabled {
                color: #808080;
            }
            QMenu::separator {
                height: 1px;
                background-color: #555555;
                margin: 4px 0px 4px 0px;
            }
            QMenu::indicator {
                width: 16px;
                height: 16px;
            }
            """
        
        elif theme == "high_contrast":
            return """
            QWidget {
                background-color: #000000;
                color: #ffff00;
            }
            QPushButton {
                background-color: #000000;
                color: #ffff00;
                border: 2px solid #ffff00;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #ffff00;
                color: #000000;
            }
            QLineEdit {
                background-color: #000000;
                color: #ffffff;
                border: 2px solid #ffff00;
                padding: 3px;
            }
            QTextEdit {
                background-color: #000000;
                color: #ffffff;
                border: 2px solid #ffff00;
            }
            QMenu {
                background-color: #000000;
                border: 2px solid #ffff00;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 24px 6px 24px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #ffff00;
                color: #000000;
            }
            QMenu::item:disabled {
                color: #808080;
            }
            QMenu::separator {
                height: 2px;
                background-color: #ffff00;
                margin: 4px 0px 4px 0px;
            }
            QMenu::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #ffff00;
            }
            """
        
        else:
            # Fluent Design风格的亮色主题
            return """
            QWidget {
                font-family: "Segoe UI", "Microsoft YaHei", system-ui;
                font-size: 9pt;
            }
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 16px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
            QPushButton:disabled {
                background-color: #f3f2f1;
                color: #a19f9d;
            }
            QLineEdit {
                background-color: #ffffff;
                border: 1px solid #d1d1d1;
                border-radius: 4px;
                padding: 4px 8px;
            }
            QLineEdit:focus {
                border-color: #0078d4;
            }
            QTextEdit {
                background-color: #ffffff;
                border: 1px solid #d1d1d1;
                border-radius: 4px;
                padding: 4px;
            }
            QTableView {
                background-color: #ffffff;
                border: 1px solid #e1dfdd;
                border-radius: 4px;
                gridline-color: #e1dfdd;
            }
            QTableView::item:hover {
                background-color: #f3f2f1;
            }
            QTableView::item:selected {
                background-color: #d1e7ff;
                color: #000000;
            }
            QHeaderView::section {
                background-color: #f3f2f1;
                color: #323130;
                font-weight: 600;
                border: none;
                border-bottom: 2px solid #d1d1d1;
                padding: 8px 4px;
            }
            QCheckBox {
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #d1d1d1;
                border-radius: 3px;
                background-color: #ffffff;
            }
            QCheckBox::indicator:checked {
                background-color: #0078d4;
                border-color: #0078d4;
            }
            QGroupBox {
                border: 1px solid #d1d1d1;
                border-radius: 4px;
                margin-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px;
                color: #323130;
                font-weight: 600;
            }
            QMenu {
                background-color: #ffffff;
                border: 1px solid #e1dfdd;
                border-radius: 4px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 24px 6px 24px;
                border-radius: 4px;
                background-color: transparent;
            }
            QMenu::item:selected {
                background-color: #e1f0ff;
                color: #323130;
            }
            QMenu::item:disabled {
                color: #a19f9d;
            }
            QMenu::separator {
                height: 1px;
                background-color: #e1dfdd;
                margin: 4px 0px 4px 0px;
            }
            QMenu::indicator {
                width: 16px;
                height: 16px;
                padding-left: 4px;
            }
            """


class PathHelper:
    """路径处理辅助类."""
    
    @staticmethod
    def normalize_path(path: str) -> str:
        """规范化路径."""
        if not path:
            return ""
        return str(Path(path).resolve())
    
    @staticmethod
    def is_valid_directory(path: str) -> bool:
        """检查是否为有效目录."""
        try:
            p = Path(path)
            return p.exists() and p.is_dir()
        except Exception:
            return False
    
    @staticmethod
    def ensure_directory(path: str):
        """确保目录存在."""
        try:
            Path(path).mkdir(parents=True, exist_ok=True)
            return True
        except Exception:
            return False