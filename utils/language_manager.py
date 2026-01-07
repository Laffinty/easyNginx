"""Multilingual support manager."""

import sys
import locale
from pathlib import Path
from typing import Dict, Any
from PySide6.QtCore import QObject
from loguru import logger


class LanguageManager(QObject):
    """
    Language manager for internationalization support.
    
    Supports: English (default), Simplified Chinese, Traditional Chinese, Japanese, Korean
    """
    
    # Supported languages mapping: {language_code: (display_name, native_name)}
    SUPPORTED_LANGUAGES = {
        "en": ("English", "English"),
        "zh_CN": ("简体中文", "简体中文"),
        "zh_TW": ("繁体中文", "繁體中文"),
        "ja": ("日本語", "日本語"),
        "ko": ("한국어", "한국어")
    }
    
    def __init__(self):
        """Initialize language manager."""
        super().__init__()
        self.current_language = "en"
        self.translations: Dict[str, Dict[str, Any]] = {}
        self._load_translations()
        
        # Auto-detect system language on initialization
        detected_lang = self.detect_system_language()
        if detected_lang in self.SUPPORTED_LANGUAGES:
            self.current_language = detected_lang
            logger.info(f"Auto-detected system language: {detected_lang}")
        else:
            self.current_language = "en"
            logger.info(f"System language '{detected_lang}' not supported, using default: en")
    
    def _load_translations(self):
        """Load all translation files."""
        translation_dir = Path(__file__).parent.parent / "translations"
        translation_dir.mkdir(exist_ok=True)
        
        # Create default translations if files don't exist
        self._create_default_translations(translation_dir)
        
        # Load translation files
        for lang_code in self.SUPPORTED_LANGUAGES.keys():
            trans_file = translation_dir / f"{lang_code}.json"
            if trans_file.exists():
                try:
                    import json
                    with open(trans_file, 'r', encoding='utf-8') as f:
                        self.translations[lang_code] = json.load(f)
                    logger.debug(f"Loaded translations for {lang_code}")
                except Exception as e:
                    logger.error(f"Failed to load translations for {lang_code}: {e}")
                    self.translations[lang_code] = {}
            else:
                self.translations[lang_code] = {}
    
    def _create_default_translations(self, translation_dir: Path):
        """Create default translation files if they don't exist."""
        import json
        
        # Default English translations
        en_trans = {
            "app_title": "easyNginx {version}",
            "app_name": "easyNginx",
            "file_menu": "File(&F)",
            "takeover_nginx": "Takeover Nginx Directory",
            "new_proxy": "New Reverse Proxy",
            "new_php": "New PHP Site",
            "new_static": "New Static Site",
            "exit": "Exit",
            "operation_menu": "Operation(&O)",
            "start_nginx": "Start Nginx",
            "stop_nginx": "Stop Nginx",
            "reload_config": "Reload Config",
            "test_config": "Test Config Syntax",
            "backup_config": "Backup Config",
            "language_menu": "Language",
            "help_menu": "Help(&H)",
            "about": "About",
            
            "site_list": "Site List",
            "site": "Site",
            "type": "Type",
            "port": "Port",
            "domain": "Domain",
            "https": "HTTPS",
            "total_sites": "Total {total} sites (Static: {static}, PHP: {php}, Proxy: {proxy})",
            
            "static_site": "Static",
            "php_site": "PHP",
            "proxy_site": "Proxy",
            
            "edit": "Edit",
            "delete": "Delete",
            "confirm_delete": "Confirm Delete",
            "delete_confirm_message": "Are you sure you want to delete site '{name}'?",
            
            "operation_success": "Operation Success",
            "operation_failed": "Operation Failed",
            
            "static_site_config": "Static Site Configuration",
            "php_site_config": "PHP Site Configuration",
            "proxy_site_config": "Reverse Proxy Configuration",
            
            "basic_config": "Basic Configuration",
            "site_name": "Site Name",
            "site_name_placeholder": "Enter site name",
            "listen_port": "Listen Port",
            "server_name": "Server Name",
            "server_name_placeholder": "localhost or domain",
            
            "https_config": "HTTPS Configuration",
            "enable_https": "Enable HTTPS",
            "https_tooltip": "Enable HTTPS requires SSL certificate",
            "ssl_cert": "SSL Certificate:",
            "ssl_cert_placeholder": "Select SSL certificate file (.crt/.pem)",
            "ssl_key": "SSL Private Key:",
            "ssl_key_placeholder": "Select SSL private key file (.key)",
            "browse": "Browse",
            
            "static_settings": "Static Site Settings",
            "root_dir": "Root Directory:",
            "root_placeholder": "Select website root directory",
            "index_file": "Index File:",
            "index_placeholder": "index.html",
            
            "php_settings": "PHP Settings",
            "php_connection": "PHP-FPM Connection",
            "php_mode" : "Mode:",
            "unix_socket": "Unix Socket",
            "tcp": "TCP",
            "php_socket": "Socket:",
            "php_host": "Host:",
            "php_port": "Port:",
            
            "proxy_settings": "Reverse Proxy Settings",
            "backend_url": "Backend URL:",
            "backend_placeholder": "http://localhost:8080",
            "location_path": "Location Path:",
            "location_placeholder": "/",
            "websocket_support": "Enable WebSocket Support",
            
            "save_apply": "Save & Apply",
            "cancel": "Cancel",
            "force_optimization_tip": "* All configurations will automatically apply F5/CIS Nginx best practices",
            
            "confirm_exit": "Confirm Exit",
            "exit_confirm_message": "Are you sure you want to exit easyNginx?",
            
            "about_title": "About easyNginx",
            "about_content": """
        <h2>easyNginx v1.0</h2>
        <p>Copyright &copy; 2026 Laffinty</p>
        <hr>
        <p><b>License:</b> MIT License</p>
        <p>This software is released under the MIT License.</p>
            """,
            "app_name": "easyNginx",
            
            # Error messages
            "error": "Error",
            "config_test_failed": "Config test failed: {message}",
            "nginx_reload_failed": "Nginx reload failed: {message}",
            "port_conflict": "Port {port} already in use by {site}",
            "site_not_found": "Site '{name}' not found",
            "nginx_not_available": "Nginx is not available. Please check the installation.",
            "load_sites_failed": "Failed to load sites: {error}",
            "add_site_failed": "Failed to add site: {error}",
            "update_site_failed": "Failed to update site: {error}",
            "delete_site_failed": "Failed to delete site: {error}",
            "deploy_config_failed": "Config deployment failed: {error}",
            "backup_created": "Config backup created: {path}",
            "nginx_started": "Nginx started",
            "nginx_stopped": "Nginx stopped",
            "config_reloaded": "Configuration reloaded"
        }
        
        # Simplified Chinese translations
        zh_CN_trans = {
            k: v for k, v in {
                "app_title": "easyNginx {version}",
                "file_menu": "文件(&F)",
                "takeover_nginx": "接管Nginx目录",
                "new_proxy": "新建反向代理",
                "new_php": "新建PHP站点",
                "new_static": "新建纯静态站点",
                "exit": "退出",
                "operation_menu": "操作(&O)",
                "start_nginx": "启动Nginx",
                "stop_nginx": "停止Nginx",
                "reload_config": "重载配置",
                "test_config": "测试配置语法",
                "backup_config": "备份配置文件",
                "language_menu": "语言",
                "help_menu": "帮助(&H)",
                "about": "关于",
                
                "site_list": "站点列表",
                "site": "站点",
                "type": "类型",
                "port": "端口",
                "domain": "域名",
                "https": "HTTPS",
                "total_sites": "共 {total} 个站点（静态: {static}, PHP: {php}, 代理: {proxy}）",
                
                "static_site": "静态",
                "php_site": "PHP",
                "proxy_site": "代理",
                
                "edit": "编辑",
                "delete": "删除",
                "confirm_delete": "确认删除",
                "delete_confirm_message": "确定要删除站点 '{name}' 吗？",
                
                "operation_success": "操作成功",
                "operation_failed": "操作失败",
                
                "save_apply": "保存并应用",
                "cancel": "取消",
                "force_optimization_tip": "* 所有配置将自动应用F5/CIS Nginx最佳实践优化",
                
                "confirm_exit": "确认退出",
                "exit_confirm_message": "确定要退出 easyNginx 吗？",
                
                "config_test_failed": "配置测试失败: {message}",
                "nginx_reload_failed": "Nginx重载失败: {message}",
                "port_conflict": "端口 {port} 已被 {site} 使用",
                "site_not_found": "站点 '{name}' 未找到",
                "nginx_not_available": "Nginx不可用，请检查安装",
                "load_sites_failed": "加载站点失败: {error}",
                "add_site_failed": "添加站点失败: {error}",
                "update_site_failed": "更新站点失败: {error}",
                "delete_site_failed": "删除站点失败: {error}",
                "deploy_config_failed": "配置部署失败: {error}",
            }.items()
        }
        
        # Create translation files
        translations = {
            "en": en_trans,
            "zh_CN": zh_CN_trans,
            "zh_TW": {},  # Can be extended
            "ja": {},     # Can be extended
            "ko": {}      # Can be extended
        }
        
        for lang_code, trans_dict in translations.items():
            trans_file = translation_dir / f"{lang_code}.json"
            if not trans_file.exists():
                try:
                    with open(trans_file, 'w', encoding='utf-8') as f:
                        json.dump(trans_dict, f, ensure_ascii=False, indent=2)
                    logger.info(f"Created translation file: {trans_file}")
                except Exception as e:
                    logger.error(f"Failed to create translation file {trans_file}: {e}")
    
    def detect_system_language(self) -> str:
        """
        Detect system language.
        
        Returns:
            Language code (e.g., 'en', 'zh_CN')
        """
        try:
            # Try to get system locale
            if sys.platform == "win32":
                import ctypes
                windll = ctypes.windll.kernel32
                lcid = windll.GetUserDefaultUILanguage()
                lang = locale.windows_locale.get(lcid, "en")
            else:
                lang = locale.getdefaultlocale()[0]
            
            if not lang:
                return "en"
            
            # Normalize language code
            lang = lang.replace('-', '_').lower()
            
            # Map to supported languages
            if lang.startswith('zh_cn'):
                return 'zh_CN'
            elif lang.startswith('zh_tw') or lang.startswith('zh_hk'):
                return 'zh_TW'
            elif lang.startswith('zh'):
                return 'zh_CN'  # Default Chinese to Simplified
            elif lang.startswith('ja'):
                return 'ja'
            elif lang.startswith('ko'):
                return 'ko'
            elif lang.startswith('en'):
                return 'en'
            else:
                return "en"  # Default to English
                
        except Exception as e:
            logger.error(f"Failed to detect system language: {e}")
            return "en"
    
    def set_language(self, language_code: str):
        """
        Set current language.
        
        Args:
            language_code: Language code (e.g., 'en', 'zh_CN')
        """
        if language_code in self.SUPPORTED_LANGUAGES:
            self.current_language = language_code
            logger.info(f"Language changed to: {language_code}")
        else:
            logger.warning(f"Unsupported language: {language_code}")
    
    def get(self, key: str, **kwargs) -> str:
        """
        Get translated string.
        
        Args:
            key: Translation key
            **kwargs: Format parameters
            
        Returns:
            Translated string (falls back to key if not found)
        """
        try:
            # Get translation for current language
            lang_dict = self.translations.get(self.current_language, {})
            text = lang_dict.get(key, "")
            
            # Fallback to English if not found
            if not text and self.current_language != "en":
                en_dict = self.translations.get("en", {})
                text = en_dict.get(key, key)
            
            # If still not found, use key itself
            if not text:
                text = key
            
            # Format with parameters if provided
            if kwargs:
                try:
                    text = text.format(**kwargs)
                except KeyError:
                    # If formatting fails, return original text
                    pass
            
            return text
            
        except Exception as e:
            logger.error(f"Translation error for key '{key}': {e}")
            return key
    
    def get_language_name(self, language_code: str = None) -> str:
        """
        Get display name for a language.
        
        Args:
            language_code: Language code (or current language if None)
            
        Returns:
            Language display name
        """
        code = language_code or self.current_language
        info = self.SUPPORTED_LANGUAGES.get(code, (code, code))
        return info[0]
    
    def get_current_language_name(self) -> str:
        """Get current language display name."""
        return self.get_language_name(self.current_language)
