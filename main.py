#!/usr/bin/env python3
"""
easyNginx - Professional Nginx Management Tool
Main entry point
"""

import sys
import os
from pathlib import Path

# Application version
APP_VERSION = "v1.0"
from typing import Optional
from PySide6.QtWidgets import QApplication, QDialog
from PySide6.QtCore import Qt, QDir

# 添加项目根目录到Python路径
if getattr(sys, 'frozen', False):
    # PyInstaller打包环境
    application_path = Path(sys._MEIPASS)
else:
    # 开发环境
    application_path = Path(__file__).parent

sys.path.insert(0, str(application_path))

from utils.logger import init_logger
from utils.theme_manager import ThemeManager
from utils.config_registry import ConfigRegistry
from utils.language_manager import LanguageManager
from viewmodels.main_viewmodel import MainViewModel
from views.main_window import MainWindow
from views.takeover_dialog import NginxTakeoverDialog
from loguru import logger


def init_application():
    """初始化应用程序."""
    try:
        # 创建必要目录
        logs_dir = application_path / "logs"
        logs_dir.mkdir(exist_ok=True)
        
        templates_dir = application_path / "templates"
        templates_dir.mkdir(exist_ok=True)
        
        # 为Nginx创建temp目录（nginx需要在其工作目录下创建临时文件）
        temp_dir = application_path / "temp"
        temp_dir.mkdir(exist_ok=True)
        
        # 初始化日志
        init_logger(str(logs_dir))
        logger.info("="*60)
        logger.info("easyNginx Application Starting...")
        logger.info(f"Application path: {application_path}")
        logger.info(f"Python version: {sys.version}")
        logger.info(f"Platform: {sys.platform}")
        
        return True
        
    except Exception as e:
        print(f"Failed to initialize application: {e}", file=sys.stderr)
        return False


def detect_nginx_paths():
    """自动检测Nginx路径."""
    # 1. 首先检查项目根目录下的 nginx-* 文件夹（最高优先级）
    application_dir = Path(__file__).parent
    for item in application_dir.iterdir():
        if item.is_dir() and item.name.startswith("nginx-"):
            nginx_exe = item / "nginx.exe"
            nginx_conf = item / "conf" / "nginx.conf"
            if nginx_exe.exists() and nginx_conf.exists():
                logger.info(f"Detected local Nginx: {nginx_exe}")
                logger.info(f"Detected local config: {nginx_conf}")
                return str(nginx_exe), str(nginx_conf)
    
    # 2. 检查常见系统安装路径
    common_nginx_paths = [
        r"C:\nginx\nginx.exe",
        r"C:\Program Files\nginx\nginx.exe",
        r"C:\Program Files (x86)\nginx\nginx.exe",
    ]
    
    common_config_paths = [
        r"C:\nginx\conf\nginx.conf",
        r"C:\nginx\nginx.conf",
        r"C:\Program Files\nginx\conf\nginx.conf",
    ]
    
    nginx_path = None
    config_path = None
    
    # 检查可执行文件
    for path in common_nginx_paths:
        if Path(path).exists():
            nginx_path = path
            break
    
    # 检查配置文件
    for path in common_config_paths:
        if Path(path).exists():
            config_path = path
            break
    
    # 如果找到了nginx.exe但找不到配置文件，尝试默认位置
    if nginx_path and not config_path:
        nginx_dir = Path(nginx_path).parent
        default_config = nginx_dir / "conf" / "nginx.conf"
        if default_config.exists():
            config_path = str(default_config)
        else:
            default_config = nginx_dir / "nginx.conf"
            if default_config.exists():
                config_path = str(default_config)
    
    if nginx_path and config_path:
        logger.info(f"Detected system Nginx: {nginx_path}")
        logger.info(f"Detected system config: {config_path}")
    else:
        logger.warning("Nginx installation not detected")
        logger.warning(f"Nginx path: {nginx_path or 'Not found'}")
        logger.warning(f"Config path: {config_path or 'Not found'}")
    
    return nginx_path, config_path


def setup_exception_handler():
    """设置全局异常处理."""
    def handle_exception(exc_type, exc_value, exc_traceback):
        """处理未捕获的异常."""
        if issubclass(exc_type, KeyboardInterrupt):
            # 允许Ctrl+C退出
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        logger.error("Uncaught exception occurred:", exc_info=(exc_type, exc_value, exc_traceback))
        
        # 尝试显示错误对话框
        try:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(
                None,
                "致命错误",
                f"应用程序遇到致命错误:\n\n{exc_value}\n\n请查看日志文件获取详细信息。"
            )
        except Exception:
            pass
        
        sys.exit(1)
    
    sys.excepthook = handle_exception


def check_and_handle_nginx_takeover(config_registry: ConfigRegistry, language_manager: LanguageManager = None) -> tuple[Optional[str], Optional[str]]:
    """
    检查并处理Nginx接管。
    
    Args:
        config_registry: 注册表配置管理器
        language_manager: 语言管理器实例（可选）
        
    Returns:
        (nginx_path, config_path)，如果用户取消返回(None, None)
    """
    logger.info("Checking Nginx takeover status...")
    
    # 1. 检查注册表中的接管状态
    takeover_status = config_registry.get_takeover_status()
    is_taken = takeover_status.get("is_taken", False)
    nginx_dir = takeover_status.get("nginx_dir", "")
    
    # 2. 检查是否需要弹出接管对话框
    need_takeover = False
    
    if not is_taken or not nginx_dir:
        # 首次使用或未接管
        logger.info("No valid takeover record found, showing takeover dialog")
        need_takeover = True
    else:
        # 检查Nginx目录是否还存在
        nginx_path = Path(nginx_dir) / "nginx.exe"
        if not nginx_path.exists():
            logger.warning(f"Nginx directory no longer exists: {nginx_dir}")
            need_takeover = True
    
    if need_takeover:
        # 显示接管对话框
        logger.info("Showing Nginx takeover dialog")
        # 如果 language_manager 为 None，则创建实例
        if language_manager is None:
            language_manager = LanguageManager()
        dialog = NginxTakeoverDialog(None, nginx_dir, language_manager)
        
        if dialog.exec() == QDialog.Accepted:
            # 获取接管后的路径
            nginx_path, config_path = dialog.get_nginx_paths()
            
            if nginx_path and config_path:
                # 更新注册表
                config_registry.set_nginx_paths(nginx_path, config_path)
                config_registry.set_takeover_status(
                    True, 
                    str(Path(nginx_path).parent),
                    str(Path(config_path).parent / "backups")
                )
                
                logger.info(f"Nginx takeover completed: {nginx_path}")
                return nginx_path, config_path
        
        # 用户取消
        logger.warning("Nginx takeover cancelled by user")
        return None, None
    
    # 3. 使用注册表中的配置
    nginx_path, config_path = config_registry.get_nginx_paths()
    
    if nginx_path and config_path:
        logger.info(f"Using existing Nginx configuration: {nginx_path}")
        
        # 验证路径是否有效
        if Path(nginx_path).exists() and Path(config_path).exists():
            return nginx_path, config_path
        else:
            logger.warning("Stored Nginx paths are invalid, showing takeover dialog")
            
            # 清除无效配置
            config_registry.clear_takeover_status()
            
            # 重新显示接管对话框
            dialog = NginxTakeoverDialog(None, "", language_manager)
            if dialog.exec() == QDialog.Accepted:
                nginx_path, config_path = dialog.get_nginx_paths()
                
                if nginx_path and config_path:
                    config_registry.set_nginx_paths(nginx_path, config_path)
                    status = config_registry.get_takeover_status()
                    config_registry.set_takeover_status(
                        True,
                        str(Path(nginx_path).parent),
                        status.get("backup_dir", "")
                    )
                    
                    return nginx_path, config_path
            
            return None, None
    
    # 4. 如果都没有找到，显示接管对话框
    logger.info("No Nginx configuration found, showing takeover dialog")
    dialog = NginxTakeoverDialog(None, "", language_manager)
    
    if dialog.exec() == QDialog.Accepted:
        nginx_path, config_path = dialog.get_nginx_paths()
        
        if nginx_path and config_path:
            config_registry.set_nginx_paths(nginx_path, config_path)
            config_registry.set_takeover_status(
                True,
                str(Path(nginx_path).parent),
                str(Path(config_path).parent / "backups")
            )
            
            return nginx_path, config_path
    
    return None, None


def main():
    """主函数."""
    # 设置异常处理
    setup_exception_handler()
    
    # 初始化应用
    if not init_application():
        sys.exit(1)
    
    try:
        # 创建Qt应用
        app = QApplication(sys.argv)
        # app.setApplicationName("easyNginx")  # 注释掉避免标题重复
        # app.setApplicationDisplayName("easyNginx")  # 注释掉避免标题重复
        app.setOrganizationName("easyNginx")
        app.setOrganizationDomain("easynginx.com")
        
        # 设置应用属性
        QDir.setCurrent(str(application_path))
        
        # 初始化注册表配置管理器
        config_registry = ConfigRegistry()
        
        # 初始化语言管理器
        language_manager = LanguageManager()
        
        # 检查是否需要Nginx接管
        nginx_path, config_path = check_and_handle_nginx_takeover(config_registry, language_manager)
        
        if not nginx_path:
            logger.warning("Nginx takeover cancelled by user, exiting application")
            # Qt事件循环未启动，直接返回
            return
        
        # 创建ViewModel
        logger.info("Creating MainViewModel...")
        main_viewmodel = MainViewModel(nginx_path, config_path)
        
        # 初始化ViewModel（包含配置同步）
        logger.info("Initializing MainViewModel and syncing configuration...")
        if not main_viewmodel.initialize():
            logger.error("Failed to initialize MainViewModel")
            sys.exit(1)
        
        logger.info("Configuration sync completed successfully")
        
        # 创建主窗口
        main_window = MainWindow(main_viewmodel)
        main_window.show()
        
        logger.info("Application started successfully")
        
        # 启动事件循环
        exit_code = app.exec()
        
        logger.info(f"Application exited with code {exit_code}")
        sys.exit(exit_code)
        
    except Exception as e:
        logger.exception(f"Application crashed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()