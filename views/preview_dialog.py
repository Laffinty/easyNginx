"""Configuration preview dialog."""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, 
    QPushButton, QLabel, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class ConfigPreviewDialog(QDialog):
    """
    配置预览对话框
    
    显示生成的Nginx配置，带有语法高亮
    """
    
    def __init__(self, parent, config_content: str):
        """初始化预览对话框."""
        super().__init__(parent)
        self.config_content = config_content
        
        self._setup_ui()
        
    def _setup_ui(self):
        """设置UI."""
        self.setWindowTitle("Nginx配置预览")
        self.resize(800, 600)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        
        # 标题
        title = QLabel("Nginx配置预览")
        title.setStyleSheet("font-size: 14pt; font-weight: 600;")
        layout.addWidget(title)
        
        # 说明
        desc = QLabel("以下是为当前站点生成的Nginx配置代码（已自动注入性能基线和安全加固）")
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        # 分割线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)
        
        # 配置文本区域
        self.config_edit = QTextEdit()
        self.config_edit.setReadOnly(True)
        self.config_edit.setFont(QFont("Courier New", 10))
        self.config_edit.setPlainText(self.config_content)
        layout.addWidget(self.config_edit)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        self.copy_btn = QPushButton("复制配置")
        self.copy_btn.clicked.connect(self._copy_config)
        button_layout.addWidget(self.copy_btn)
        
        button_layout.addStretch()
        
        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
        
        # 语法高亮
        self._apply_syntax_highlight()
    
    def _apply_syntax_highlight(self):
        """应用语法高亮."""
        # 在这里可以实现简单的语法高亮
        # 由于复杂性，这里仅作为占位符
        pass
    
    def _copy_config(self):
        """复制配置到剪贴板."""
        self.config_edit.selectAll()
        self.config_edit.copy()
        self.copy_btn.setText("已复制！")
        
    def showEvent(self, event):
        """显示事件."""
        super().showEvent(event)