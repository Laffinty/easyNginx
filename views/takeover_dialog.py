"""Nginx接管对话框。"""

import random
import string
import platform
from pathlib import Path
from datetime import datetime
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFileDialog, QMessageBox, QTextEdit, QGroupBox, QCheckBox
)
from PySide6.QtCore import Qt
from loguru import logger
from utils.language_manager import LanguageManager
from utils.encoding_utils import read_file_robust


class NginxTakeoverDialog(QDialog):
    """Nginx接管对话框。"""
    
    def __init__(self, parent=None, nginx_dir: str = "", language_manager=None):
        """
        初始化接管对话框。
        
        Args:
            parent: 父窗口
            nginx_dir: 初始Nginx目录
            language_manager: 语言管理器实例（可选）
        """
        super().__init__(parent)
        self.nginx_dir = Path(nginx_dir) if nginx_dir else None
        self.backup_path = None
        # 使用传入的language_manager或创建新实例
        self.language_manager = language_manager if language_manager else LanguageManager()
        self.setup_ui()
    
    def setup_ui(self):
        """设置UI。"""
        self.setWindowTitle(self.language_manager.get("takeover_dialog_title"))
        self.setMinimumSize(600, 400)
        
        layout = QVBoxLayout(self)
        
        # 说明
        desc_label = QLabel(
            self.language_manager.get("takeover_dialog_description") + "\n" +
            self.language_manager.get("takeover_dialog_step1") + "\n" +
            self.language_manager.get("takeover_dialog_step2") + "\n" +
            self.language_manager.get("takeover_dialog_step3")
        )
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        # Nginx目录选择
        dir_group = QGroupBox(self.language_manager.get("takeover_step1_title"))
        dir_layout = QVBoxLayout()
        
        dir_select_layout = QHBoxLayout()
        self.dir_label = QLabel(str(self.nginx_dir) if self.nginx_dir else self.language_manager.get("not_selected"))
        self.dir_label.setStyleSheet("padding: 5px; background-color: #f0f0f0;")
        dir_select_layout.addWidget(self.dir_label)
        
        self.select_button = QPushButton(self.language_manager.get("browse"))
        self.select_button.clicked.connect(self._on_select_dir)
        dir_select_layout.addWidget(self.select_button)
        
        dir_layout.addLayout(dir_select_layout)
        
        # 检查结果
        self.check_result_label = QLabel("")
        self.check_result_label.setWordWrap(True)
        self.check_result_label.setStyleSheet("padding: 10px;")
        dir_layout.addWidget(self.check_result_label)
        
        self.check_button = QPushButton(self.language_manager.get("check_nginx_integrity"))
        self.check_button.clicked.connect(self._on_check_nginx)
        self.check_button.setEnabled(False)
        dir_layout.addWidget(self.check_button)
        
        dir_group.setLayout(dir_layout)
        layout.addWidget(dir_group)
        
        # 备份选项
        backup_group = QGroupBox(self.language_manager.get("takeover_step2_title"))
        backup_layout = QVBoxLayout()
        
        self.backup_check = QCheckBox(self.language_manager.get("backup_existing_config"))
        self.backup_check.setChecked(True)
        backup_layout.addWidget(self.backup_check)
        
        self.backup_info_label = QLabel(self.language_manager.get("backup_filename_format"))
        self.backup_info_label.setStyleSheet("color: #666; font-size: 12px;")
        backup_layout.addWidget(self.backup_info_label)
        
        backup_group.setLayout(backup_layout)
        layout.addWidget(backup_group)
        
        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.cancel_button = QPushButton(self.language_manager.get("cancel"))
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        self.takeover_button = QPushButton(self.language_manager.get("execute_takeover"))
        self.takeover_button.clicked.connect(self._on_takeover)
        self.takeover_button.setEnabled(False)
        button_layout.addWidget(self.takeover_button)
        
        layout.addLayout(button_layout)
        
        # 初始化
        if self.nginx_dir:
            self.dir_label.setText(str(self.nginx_dir))
            self._on_check_nginx()
    
    def _on_select_dir(self):
        """选择Nginx目录。"""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            self.language_manager.get("select_nginx_directory"),
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
            errors.append(self.language_manager.get("nginx_exe_not_found") + f": {nginx_exe}")
        else:
            warnings.append(self.language_manager.get("nginx_exe_found"))
        
        if not conf_dir.exists():
            errors.append(self.language_manager.get("conf_dir_not_found") + f": {conf_dir}")
        else:
            warnings.append(self.language_manager.get("conf_dir_found"))
        
        if not nginx_conf.exists():
            errors.append(self.language_manager.get("nginx_conf_not_found") + f": {nginx_conf}" + self.language_manager.get("will_create_new_config"))
        else:
            warnings.append(self.language_manager.get("nginx_conf_found"))
        
        if not mime_types.exists():
            errors.append(self.language_manager.get("mime_types_not_found") + f": {mime_types}" + self.language_manager.get("may_cause_config_issues"))
        else:
            warnings.append(self.language_manager.get("mime_types_found"))
        
        # 显示结果
        if errors:
            result_text = "\n".join(errors + warnings)
            self.check_result_label.setText(result_text)
            self.check_result_label.setStyleSheet("padding: 10px; color: #d32f2f;")
            self.takeover_button.setEnabled(False)
        else:
            result_text = self.language_manager.get("nginx_installation_complete") + "\n\n" + "\n".join(warnings)
            self.check_result_label.setText(result_text)
            self.check_result_label.setStyleSheet("padding: 10px; color: #388e3c;")
            self.takeover_button.setEnabled(True)
    
    def _generate_optimized_config_preview(self) -> str:
        """生成优化的配置预览。"""
        # 根据操作系统选择事件模型
        event_model = "select" if platform.system() == "Windows" else "epoll"
        return f"""# 全局性能优化配置
worker_processes auto;
worker_rlimit_nofile 8192;
error_log logs/error.log warn;

# Events优化
events {{
    worker_connections 1024;
    multi_accept on;
    use {event_model};
}}

# HTTP性能和安全性优化
http {{
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
}}"""""
    
    def _on_takeover(self):
        """执行接管。"""
        if not self.nginx_dir:
            QMessageBox.warning(self, self.language_manager.get("error"), self.language_manager.get("please_select_nginx_directory"))
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
                    
                    # 创建备份（使用健壮的编码检测）
                    content = read_file_robust(nginx_conf)
                    if content is None:
                        logger.error(f"无法读取配置文件: {nginx_conf}")
                        raise Exception(f"无法读取配置文件: {nginx_conf}")
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
            msg = self.language_manager.get("takeover_success_message") + f"\n\n" + self.language_manager.get("nginx_directory") + f": {self.nginx_dir}\n"
            if self.backup_path:
                msg += self.language_manager.get("backup_file") + f": {self.backup_path.name}"
            
            QMessageBox.information(self, self.language_manager.get("takeover_success"), msg)
            self.accept()
            
        except Exception as e:
            logger.error(f"Takeover failed: {e}")
            QMessageBox.critical(self, self.language_manager.get("takeover_failed"), self.language_manager.get("takeover_error_occurred") + f":\n{str(e)}")
    
    def _generate_full_optimized_config(self) -> str:
        """生成完整的优化配置。"""
        # 读取模板文件（使用健壮的编码检测）
        template_path = Path(__file__).parent.parent / "templates" / "nginx_base.conf"
        if template_path.exists():
            content = read_file_robust(template_path)
            if content:
                return content
            else:
                logger.warning("无法读取模板文件，使用内联配置")
        
        # 如果模板不存在，使用内联配置
        logger.warning("nginx_base.conf template not found, using inline config")
        event_model = "select" if platform.system() == "Windows" else "epoll"
        return f"""# Nginx Configuration - Generated by easyNginx
# Performance optimized and security hardened
# Based on F5/CIS best practices

# ============================================
# Global Configuration
# ============================================
worker_processes auto;
worker_rlimit_nofile 8192;
error_log logs/error.log warn;
pid logs/nginx.pid;

# ============================================
# Events Module
# ============================================
events {{
    worker_connections 1024;
    multi_accept on;
    use {event_model};  # Windows平台使用select模型
}}

# ============================================
# HTTP Module
# ============================================
http {{
    # MIME Types
    include mime.types;
    default_type application/octet-stream;
    
    # Logging Configuration
    log_format main '$remote_addr - $remote_user [$time_local] \"$request\" '
                    '$status $body_bytes_sent \"$http_referer\" '
                    '\"$http_user_agent\" \"$http_x_forwarded_for\"';
    
    access_log logs/access.log main;
    
    # ============================================
    # Performance Optimization
    # ============================================
    
    # File Transfer Optimization
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    
    # Keepalive Settings
    keepalive_timeout 65;
    keepalive_requests 100;
    reset_timedout_connection on;
    client_body_timeout 10;
    client_header_timeout 10;
    send_timeout 10;
    
    # Buffer Settings
    client_body_buffer_size 128k;
    client_max_body_size 50m;
    client_header_buffer_size 1k;
    large_client_header_buffers 4 4k;
    output_buffers 1 32k;
    postpone_output 1460;
    
    # ============================================
    # Security Hardening
    # ============================================
    
    # Hide Nginx Version
    server_tokens off;
    
    # Prevent Clickjacking
    add_header X-Frame-Options "SAMEORIGIN" always;
    
    # Prevent MIME Sniffing
    add_header X-Content-Type-Options "nosniff" always;
    
    # XSS Protection
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Disable Deprecated SSL/TLS
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES128-SHA256:ECDHE-RSA-AES256-SHA384;
    ssl_prefer_server_ciphers on;
    
    # SSL Session Settings
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # Rate Limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=login:10m rate=1r/s;
    
    # Connection Limiting
    limit_conn_zone $binary_remote_addr zone=addr:10m;
    
    # ============================================
    # Gzip Compression
    # ============================================
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_comp_level 6;
    gzip_proxied any;
    gzip_types
        text/plain
        text/css
        text/xml
        text/javascript
        application/json
        application/javascript
        application/xml+rss
        application/xml
        image/svg+xml
        font/woff
        font/woff2;
    
    # ============================================
    # Include Site Configurations
    # ============================================
    include conf.d/*.conf;
    
    # Default Server (Placeholder - will be replaced by actual sites)
    server {{
        listen 80 default_server;
        server_name _;
        
        location / {{
            root html;
            index index.html index.htm;
        }}
        
        error_page 500 502 503 504 /50x.html;
        location = /50x.html {{
            root html;
        }}
    }}
}}"""
    
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
