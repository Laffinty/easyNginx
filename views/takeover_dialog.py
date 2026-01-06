"""Nginx接管对话框。"""

import random
import string
from pathlib import Path
from datetime import datetime
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFileDialog, QMessageBox, QTextEdit, QGroupBox, QCheckBox
)
from PySide6.QtCore import Qt
from loguru import logger


class NginxTakeoverDialog(QDialog):
    """Nginx接管对话框。"""
    
    def __init__(self, parent=None, nginx_dir: str = ""):
        """
        初始化接管对话框。
        
        Args:
            parent: 父窗口
            nginx_dir: 初始Nginx目录
        """
        super().__init__(parent)
        self.nginx_dir = Path(nginx_dir) if nginx_dir else None
        self.backup_path = None
        self.setup_ui()
    
    def setup_ui(self):
        """设置UI。"""
        self.setWindowTitle("Nginx接管向导")
        self.setMinimumSize(600, 400)
        
        layout = QVBoxLayout(self)
        
        # 说明
        desc_label = QLabel(
            "本向导将帮助您接管Nginx配置管理。\n"
            "我们将：\n"
            "1. 检查Nginx安装完整性\n"
            "2. 备份现有配置文件\n"
            "3. 应用性能优化和安全加固配置"
        )
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        # Nginx目录选择
        dir_group = QGroupBox("1. 选择Nginx目录")
        dir_layout = QVBoxLayout()
        
        dir_select_layout = QHBoxLayout()
        self.dir_label = QLabel(str(self.nginx_dir) if self.nginx_dir else "未选择")
        self.dir_label.setStyleSheet("padding: 5px; background-color: #f0f0f0;")
        dir_select_layout.addWidget(self.dir_label)
        
        self.select_button = QPushButton("浏览...")
        self.select_button.clicked.connect(self._on_select_dir)
        dir_select_layout.addWidget(self.select_button)
        
        dir_layout.addLayout(dir_select_layout)
        
        # 检查结果
        self.check_result_label = QLabel("")
        self.check_result_label.setWordWrap(True)
        self.check_result_label.setStyleSheet("padding: 10px;")
        dir_layout.addWidget(self.check_result_label)
        
        self.check_button = QPushButton("检查Nginx完整性")
        self.check_button.clicked.connect(self._on_check_nginx)
        self.check_button.setEnabled(False)
        dir_layout.addWidget(self.check_button)
        
        dir_group.setLayout(dir_layout)
        layout.addWidget(dir_group)
        
        # 备份选项
        backup_group = QGroupBox("2. 备份选项")
        backup_layout = QVBoxLayout()
        
        self.backup_check = QCheckBox("备份现有nginx.conf配置文件")
        self.backup_check.setChecked(True)
        backup_layout.addWidget(self.backup_check)
        
        self.backup_info_label = QLabel("备份文件名格式: YYYYMMDD_HHMMSS_8位随机数.nginx.conf.bk")
        self.backup_info_label.setStyleSheet("color: #666; font-size: 12px;")
        backup_layout.addWidget(self.backup_info_label)
        
        backup_group.setLayout(backup_layout)
        layout.addWidget(backup_group)
        
        # 配置预览
        preview_group = QGroupBox("3. 新配置预览（性能优化和安全加固）")
        preview_layout = QVBoxLayout()
        
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setMaximumHeight(150)
        preview_layout.addWidget(self.preview_text)
        
        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)
        
        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        self.takeover_button = QPushButton("执行接管")
        self.takeover_button.clicked.connect(self._on_takeover)
        self.takeover_button.setEnabled(False)
        button_layout.addWidget(self.takeover_button)
        
        layout.addLayout(button_layout)
        
        # 初始化
        if self.nginx_dir:
            self.dir_label.setText(str(self.nginx_dir))
            self._on_check_nginx()
        
        # 显示配置预览
        self.preview_text.setText(self._generate_optimized_config_preview())
    
    def _on_select_dir(self):
        """选择Nginx目录。"""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "选择Nginx所在目录",
            str(self.nginx_dir) if self.nginx_dir else ""
        )
        
        if dir_path:
            self.nginx_dir = Path(dir_path)
            self.dir_label.setText(dir_path)
            self.check_button.setEnabled(True)
            self.check_result_label.setText("")
            self.check_result_label.setStyleSheet("padding: 10px;")
            # 自动执行完整性检查
            self._on_check_nginx()
    
    def _on_check_nginx(self):
        """检查Nginx完整性。"""
        if not self.nginx_dir:
            return
        
        # 检查必需文件
        nginx_exe = self.nginx_dir / "nginx.exe"
        conf_dir = self.nginx_dir / "conf"
        nginx_conf = conf_dir / "nginx.conf"
        
        # mime.types文件可能在conf目录或同级目录
        mime_types = conf_dir / "mime.types"
        if not mime_types.exists():
            mime_types = self.nginx_dir / "mime.types"
        
        errors = []
        warnings = []
        
        if not nginx_exe.exists():
            errors.append(f"❌ 找不到 nginx.exe: {nginx_exe}")
        else:
            warnings.append(f"✓ 找到 nginx.exe")
        
        if not conf_dir.exists():
            errors.append(f"❌ 找不到 conf 目录: {conf_dir}")
        else:
            warnings.append(f"✓ 找到 conf 目录")
        
        if not nginx_conf.exists():
            errors.append(f"⚠ 找不到 nginx.conf: {nginx_conf}（将创建新配置）")
        else:
            warnings.append(f"✓ 找到 nginx.conf")
        
        if not mime_types.exists():
            errors.append(f"⚠ 找不到 mime.types: {mime_types}（可能导致配置问题）")
        else:
            warnings.append(f"✓ 找到 mime.types")
        
        # 显示结果
        if errors:
            result_text = "\n".join(errors + warnings)
            self.check_result_label.setText(result_text)
            self.check_result_label.setStyleSheet("padding: 10px; color: #d32f2f;")
            self.takeover_button.setEnabled(False)
        else:
            result_text = "✅ Nginx安装完整\n\n" + "\n".join(warnings)
            self.check_result_label.setText(result_text)
            self.check_result_label.setStyleSheet("padding: 10px; color: #388e3c;")
            self.takeover_button.setEnabled(True)
    
    def _generate_optimized_config_preview(self) -> str:
        """生成优化的配置预览。"""
        return """# 全局性能优化配置
worker_processes auto;
worker_rlimit_nofile 8192;
error_log logs/error.log warn;

# Events优化
events {
    worker_connections 1024;
    multi_accept on;
    use epoll;
}

# HTTP性能和安全性优化
http {
    include mime.types;
    default_type application/octet-stream;
    
    # 性能优化
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    keepalive_requests 100;
    
    # 安全性
    server_tokens off;
    client_max_body_size 50m;
    
    # Gzip压缩
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/json application/javascript application/xml+rss application/xml image/svg+xml;
}"""
    
    def _on_takeover(self):
        """执行接管。"""
        if not self.nginx_dir:
            QMessageBox.warning(self, "错误", "请先选择Nginx目录")
            return
        
        try:
            # 1. 备份现有配置
            if self.backup_check.isChecked():
                conf_dir = self.nginx_dir / "conf"
                nginx_conf = conf_dir / "nginx.conf"
                
                if nginx_conf.exists():
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    random_str = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
                    backup_name = f"{timestamp}_{random_str}.nginx.conf.bk"
                    backup_path = conf_dir / backup_name
                    
                    # 创建备份
                    content = nginx_conf.read_text(encoding="utf-8")
                    backup_path.write_text(content, encoding="utf-8")
                    
                    self.backup_path = backup_path
                    logger.info(f"Config backed up to: {backup_path}")
            
            # 2. 创建新的优化配置
            conf_dir = self.nginx_dir / "conf"
            conf_dir.mkdir(exist_ok=True)
            
            nginx_conf = conf_dir / "nginx.conf"
            optimized_config = self._generate_full_optimized_config()
            nginx_conf.write_text(optimized_config, encoding="utf-8")
            
            # 3. 创建mime.types（如果不存在）
            mime_types = conf_dir / "mime.types"
            if not mime_types.exists():
                mime_content = self._generate_mime_types()
                mime_types.write_text(mime_content, encoding="utf-8")
            
            logger.info(f"Takeover completed successfully: {self.nginx_dir}")
            
            # 显示成功信息
            msg = f"接管成功！\n\nNginx目录: {self.nginx_dir}\n"
            if self.backup_path:
                msg += f"备份文件: {self.backup_path.name}"
            
            QMessageBox.information(self, "接管成功", msg)
            self.accept()
            
        except Exception as e:
            logger.error(f"Takeover failed: {e}")
            QMessageBox.critical(self, "接管失败", f"接管过程中出现错误:\n{str(e)}")
    
    def _generate_full_optimized_config(self) -> str:
        """生成完整的优化配置。"""
        return """# Nginx Configuration - Generated by easyNginx
# Performance optimized and security hardened

# 全局配置
worker_processes auto;
worker_rlimit_nofile 8192;
error_log logs/error.log warn;
pid logs/nginx.pid;

# Event配置
events {
    worker_connections 1024;
    multi_accept on;
    use epoll;
}

# HTTP配置
http {
    include mime.types;
    default_type application/octet-stream;
    
    # 日志格式
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';
    
    access_log logs/access.log main;
    
    # 性能优化
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    keepalive_requests 100;
    reset_timedout_connection on;
    client_body_timeout 10;
    client_header_timeout 10;
    send_timeout 10;
    
    # 安全性
    server_tokens off;
    client_max_body_size 50m;
    
    # Gzip压缩
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_comp_level 6;
    gzip_types
        text/plain
        text/css
        text/xml
        text/javascript
        application/json
        application/javascript
        application/xml+rss
        application/xml
        image/svg+xml;
    
    # 安全的SSL配置（需要时取消注释）
    # ssl_protocols TLSv1.2 TLSv1.3;
    # ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES128-SHA256:ECDHE-RSA-AES256-SHA384;
    # ssl_prefer_server_ciphers on;
    # ssl_session_cache shared:SSL:10m;
    # ssl_session_timeout 10m;
    
    # 包含站点配置
    include conf.d/*.conf;
    
    # 默认server（占位符）
    server {
        listen 80 default_server;
        server_name _;
        
        location / {
            root html;
            index index.html index.htm;
        }
        
        error_page 500 502 503 504 /50x.html;
        location = /50x.html {
            root html;
        }
    }
}
"""
    
    def _generate_mime_types(self) -> str:
        """生成mime.types文件内容。"""
        return """types {
    text/html                             html htm shtml;
    text/css                              css;
    text/xml                              xml;
    image/gif                             gif;
    image/jpeg                            jpeg jpg;
    application/javascript                js;
    application/atom+xml                  atom;
    application/rss+xml                   rss;
    text/mathml                           mml;
    text/plain                            txt;
    text/vnd.sun.j2me.app-descriptor      jad;
    text/vnd.wap.wml                      wml;
    text/x-component                      htc;
    image/avif                            avif;
    image/png                             png;
    image/svg+xml                         svg svgz;
    image/tiff                            tif tiff;
    image/vnd.wap.wbmp                    wbmp;
    image/webp                            webp;
    image/x-icon                          ico;
    image/x-jng                           jng;
    image/x-ms-bmp                        bmp;
    font/woff                             woff;
    font/woff2                            woff2;
    application/java-archive              jar war ear;
    application/json                      json;
    application/mac-binhex40              hqx;
    application/msword                    doc;
    application/pdf                       pdf;
    application/postscript                ps eps ai;
    application/rtf                       rtf;
    application/vnd.apple.mpegurl         m3u8;
    application/vnd.google-earth.kml+xml  kml;
    application/vnd.google-earth.kmz      kmz;
    application/vnd.ms-excel              xls;
    application/vnd.ms-fontobject         eot;
    application/vnd.ms-powerpoint         ppt;
    application/vnd.oasis.opendocument.graphics        odg;
    application/vnd.oasis.opendocument.presentation    odp;
    application/vnd.oasis.opendocument.spreadsheet     ods;
    application/vnd.oasis.opendocument.text            odt;
    application/vnd.openxmlformats-officedocument.presentationml.presentation    pptx;
    application/vnd.openxmlformats-officedocument.spreadsheetml.sheet          xlsx;
    application/vnd.openxmlformats-officedocument.wordprocessingml.document    docx;
    application/vnd.wap.wmlc              wmlc;
    application/wasm                      wasm;
    application/x-7z-compressed           7z;
    application/x-cocoa                   cco;
    application/x-java-archive-diff       jardiff;
    application/x-java-jnlp-file          jnlp;
    application/x-makeself                run;
    application/x-perl                    pl pm;
    application/x-pilot                   prc pdb;
    application/x-rar-compressed          rar;
    application/x-redhat-package-manager  rpm;
    application/x-sea                     sea;
    application/x-shockwave-flash         swf;
    application/x-stuffit                 sit;
    application/x-tcl                     tcl tk;
    application/x-x509-ca-cert            der pem crt;
    application/x-xpinstall               xpi;
    application/xhtml+xml                 xhtml;
    application/xspf+xml                  xspf;
    application/zip                       zip;
    application/octet-stream              bin exe dll;
    application/octet-stream              deb;
    application/octet-stream              dmg;
    application/octet-stream              iso img;
    application/octet-stream              msi msp msm;
    audio/midi                            mid midi kar;
    audio/mpeg                            mp3;
    audio/ogg                             ogg;
    audio/x-m4a                           m4a;
    audio/x-realaudio                     ra;
    video/3gpp                            3gpp 3gp;
    video/mp2t                            ts;
    video/mp4                             mp4;
    video/mpeg                            mpeg mpg;
    video/quicktime                       mov;
    video/webm                            webm;
    video/x-flv                           flv;
    video/x-m4v                           m4v;
    video/x-mng                           mng;
    video/x-ms-asf                        asx asf;
    video/x-ms-wmv                        wmv;
    video/x-msvideo                       avi;
}
"""
    
    def get_nginx_paths(self) -> tuple[str, str]:
        """
        获取接管后的Nginx路径。
        
        Returns:
            (nginx_exe_path, config_path)
        """
        if not self.nginx_dir:
            return "", ""
        
        nginx_exe = self.nginx_dir / "nginx.exe"
        nginx_conf = self.nginx_dir / "conf" / "nginx.conf"
        
        return str(nginx_exe), str(nginx_conf)
