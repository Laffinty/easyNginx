"""Windows注册表配置管理器。"""

import winreg
import json
from pathlib import Path
from typing import Optional, Dict, Any
from loguru import logger


class ConfigRegistry:
    """Windows注册表配置管理器。"""
    
    # 注册表路径
    REGISTRY_PATH = r"SOFTWARE\easyNginx"
    REGISTRY_KEY = r"SOFTWARE\easyNginx\Settings"
    
    # 配置键名
    KEY_NGINX_PATH = "nginx_path"
    KEY_CONFIG_PATH = "config_path"
    KEY_TAKEOVER_STATUS = "takeover_status"
    KEY_TAKEOVER_TIME = "takeover_time"
    KEY_SITE_CONF_RANDOM = "site_conf_random"
    
    def __init__(self):
        """初始化注册表管理器。"""
        self._ensure_registry_key_exists()
    
    def _ensure_registry_key_exists(self):
        """确保注册表键存在。"""
        try:
            # 先创建父键
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, self.REGISTRY_PATH):
                pass
            # 再创建子键
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, self.REGISTRY_KEY):
                pass
        except Exception as e:
            logger.error(f"Failed to create registry key: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值。
        
        Args:
            key: 配置键名
            default: 默认值
            
        Returns:
            配置值
        """
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.REGISTRY_KEY, 0, winreg.KEY_READ) as reg_key:
                value, _ = winreg.QueryValueEx(reg_key, key)
                # 尝试JSON反序列化
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    return value
        except FileNotFoundError:
            return default
        except Exception as e:
            logger.error(f"Failed to read registry key {key}: {e}")
            return default
    
    def set(self, key: str, value: Any) -> bool:
        """
        设置配置值。
        
        Args:
            key: 配置键名
            value: 配置值
            
        Returns:
            是否成功
        """
        try:
            # 序列化为JSON字符串
            if not isinstance(value, str):
                value = json.dumps(value)
            
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.REGISTRY_KEY, 0, winreg.KEY_SET_VALUE) as reg_key:
                winreg.SetValueEx(reg_key, key, 0, winreg.REG_SZ, str(value))
            return True
        except Exception as e:
            logger.error(f"Failed to write registry key {key}: {e}")
            return False
    
    def get_nginx_paths(self) -> tuple[Optional[str], Optional[str]]:
        """
        获取Nginx路径配置。
        
        Returns:
            (nginx_path, config_path)
        """
        nginx_path = self.get(self.KEY_NGINX_PATH)
        config_path = self.get(self.KEY_CONFIG_PATH)
        return nginx_path, config_path
    
    def set_nginx_paths(self, nginx_path: str, config_path: str) -> bool:
        """
        设置Nginx路径配置。
        
        Args:
            nginx_path: Nginx可执行文件路径
            config_path: 配置文件路径
            
        Returns:
            是否成功
        """
        success1 = self.set(self.KEY_NGINX_PATH, nginx_path)
        success2 = self.set(self.KEY_CONFIG_PATH, config_path)
        return success1 and success2
    
    def get_takeover_status(self) -> Dict[str, Any]:
        """
        获取Nginx接管状态。
        
        Returns:
            接管状态字典
        """
        status = self.get(self.KEY_TAKEOVER_STATUS, {})
        if not isinstance(status, dict):
            status = {}
        
        return {
            "is_taken": status.get("is_taken", False),
            "nginx_dir": status.get("nginx_dir", ""),
            "backup_dir": status.get("backup_dir", ""),
            "takeover_time": status.get("takeover_time", "")
        }
    
    def set_takeover_status(self, is_taken: bool, nginx_dir: str, backup_dir: str = "") -> bool:
        """
        设置Nginx接管状态。
        
        Args:
            is_taken: 是否已接管
            nginx_dir: Nginx目录
            backup_dir: 备份目录
            
        Returns:
            是否成功
        """
        import datetime
        status = {
            "is_taken": is_taken,
            "nginx_dir": nginx_dir,
            "backup_dir": backup_dir,
            "takeover_time": datetime.datetime.now().isoformat()
        }
        return self.set(self.KEY_TAKEOVER_STATUS, status)
    
    def clear_takeover_status(self) -> bool:
        """清除接管状态。"""
        return self.set(self.KEY_TAKEOVER_STATUS, {
            "is_taken": False,
            "nginx_dir": "",
            "backup_dir": "",
            "takeover_time": ""
        })
    
    def is_takeover_valid(self) -> bool:
        """
        检查接管状态是否有效（Nginx目录是否存在）。
        
        Returns:
            是否有效
        """
        status = self.get_takeover_status()
        if not status["is_taken"] or not status["nginx_dir"]:
            return False
        
        nginx_dir = Path(status["nginx_dir"])
        nginx_exe = nginx_dir / "nginx.exe"
        
        return nginx_dir.exists() and nginx_exe.exists()
    
    def generate_site_conf_random(self) -> str:
        """
        生成站点配置目录的随机数标识符。
        
        生成一个5位随机字符串（字母+数字），用于命名站点配置目录。
        
        Returns:
            随机字符串（如: J43R8）
        """
        import random
        import string
        
        # 生成5位随机字符串（字母+数字）
        random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        
        # 保存到注册表
        if self.set(self.KEY_SITE_CONF_RANDOM, random_str):
            logger.info(f"Generated site conf random identifier: {random_str}")
            return random_str
        else:
            logger.error("Failed to save site conf random identifier")
            # 返回一个默认值
            return "EN000"
    
    def get_site_conf_random(self) -> str:
        """
        获取站点配置目录的随机数标识符。
        
        Returns:
            随机字符串（如: J43R8），如果未设置则返回默认值
        """
        random_id = self.get(self.KEY_SITE_CONF_RANDOM, "EN000")
        logger.info(f"Site conf random identifier: {random_id}")
        return random_id
    
    def get_site_conf_dir(self, nginx_conf_dir: Path) -> Path:
        """
        获取站点配置目录路径。
        
        Args:
            nginx_conf_dir: Nginx配置目录（conf目录）
            
        Returns:
            站点配置目录路径（如: conf/J43R8_conf.d/）
        """
        random_id = self.get_site_conf_random()
        conf_dir_name = f"{random_id}_conf.d"
        return nginx_conf_dir / conf_dir_name
