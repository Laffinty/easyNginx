"""Theme management for UI theming."""

from PySide6.QtCore import QObject, Signal, Property
from PySide6.QtGui import QPalette, QColor, QGuiApplication
import darkdetect


class ThemeManager(QObject):
    """
    主题管理器
    
    管理应用程序主题：亮色、暗色、高对比度
    """
    
    theme_changed = Signal(str)  # 主题改变信号
    
    THEMES = {
        "light": "亮色主题",
        "dark": "暗色主题", 
        "high_contrast": "高对比度"
    }
    
    def __init__(self):
        """初始化主题管理器."""
        super().__init__()
        self._current_theme = "light"
        self._auto_detect = True
        self._apply_theme("light")
    
    @Property(str, notify=theme_changed)
    def current_theme(self) -> str:
        """当前主题."""
        return self._current_theme
    
    @current_theme.setter
    def current_theme(self, theme: str):
        """设置主题."""
        if theme in self.THEMES and theme != self._current_theme:
            self._current_theme = theme
            self._auto_detect = False
            self._apply_theme(theme)
            self.theme_changed.emit(theme)
    
    @Property(bool, constant=True)
    def auto_detect(self) -> bool:
        """是否自动检测系统主题."""
        return True
    
    @Property(list, constant=True)
    def available_themes(self) -> list:
        """可用主题列表."""
        return list(self.THEMES.keys())
    
    def detect_system_theme(self):
        """检测系统主题."""
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