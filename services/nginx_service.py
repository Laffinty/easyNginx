"""Nginx process management service."""

import subprocess
import psutil
import time
from pathlib import Path
from typing import Optional, Tuple, List
from datetime import datetime
from loguru import logger
from models.nginx_status import NginxStatus, NginxProcessStatus, ConfigTestStatus, NginxProcessInfo


class NginxService:
    """
    Nginx服务管理类
    
    职责：
    1. Nginx进程管理（启动/停止/重载）
    2. 配置语法测试
    3. 配置文件备份
    4. 进程状态监控
    """
    
    def __init__(self, nginx_path: Optional[str] = None, config_path: Optional[str] = None):
        """初始化Nginx服务."""
        self._nginx_path = nginx_path
        self._config_path = config_path
        self._process: Optional[psutil.Process] = None
        
        # 自动检测Nginx路径
        if not self._nginx_path:
            self._nginx_path = self._detect_nginx_path()
        
        # 自动检测配置文件路径
        if not self._config_path and self._nginx_path:
            self._config_path = self._detect_config_path()
        
        logger.info(f"NginxService initialized: nginx={self._nginx_path}, config={self._config_path}")
    
    @property
    def nginx_path(self) -> Optional[str]:
        """获取Nginx可执行文件路径."""
        return self._nginx_path
    
    @property
    def config_path(self) -> Optional[str]:
        """获取Nginx配置文件路径."""
        return self._config_path
    
    def _detect_nginx_path(self) -> Optional[str]:
        """自动检测Nginx可执行文件路径."""
        # 常见路径
        common_paths = [
            r"C:\nginx\nginx.exe",
            r"C:\Program Files\nginx\nginx.exe",
            r"C:\Program Files (x86)\nginx\nginx.exe",
            r"C:\Tools\nginx\nginx.exe"
        ]
        
        # 检查PATH环境变量
        try:
            result = subprocess.run(
                ["where", "nginx.exe"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                path = result.stdout.strip().split('\n')[0]
                if Path(path).exists():
                    logger.info(f"Detected nginx.exe from PATH: {path}")
                    return path
        except Exception as e:
            logger.debug(f"Failed to find nginx in PATH: {e}")
        
        # 检查常见路径
        for path in common_paths:
            if Path(path).exists():
                logger.info(f"Detected nginx.exe from common path: {path}")
                return path
        
        logger.warning("Nginx executable not found")
        return None
    
    def _detect_config_path(self) -> Optional[str]:
        """自动检测Nginx配置文件路径."""
        if not self._nginx_path:
            return None
        
        # 默认配置文件位置（与nginx.exe同目录的conf/nginx.conf）
        nginx_dir = Path(self._nginx_path).parent
        config_path = nginx_dir / "conf" / "nginx.conf"
        
        if config_path.exists():
            logger.info(f"Detected nginx.conf: {config_path}")
            return str(config_path)
        
        # 检查nginx.exe所在目录
        config_path = nginx_dir / "nginx.conf"
        if config_path.exists():
            logger.info(f"Detected nginx.conf: {config_path}")
            return str(config_path)
        
        logger.warning("Nginx config file not found")
        return None
    
    def set_paths(self, nginx_path: str, config_path: str):
        """设置Nginx路径."""
        self._nginx_path = nginx_path
        self._config_path = config_path
        logger.info(f"Paths updated: nginx={nginx_path}, config={config_path}")
    
    def is_nginx_available(self) -> bool:
        """检查Nginx是否可用."""
        if not self._nginx_path or not Path(self._nginx_path).exists():
            logger.error(f"Nginx executable not found: {self._nginx_path}")
            return False
        
        try:
            result = subprocess.run(
                [self._nginx_path, "-v"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                version = result.stderr.strip()  # nginx -v输出到stderr
                logger.info(f"Nginx version: {version}")
                return True
        except Exception as e:
            logger.error(f"Failed to check nginx version: {e}")
        
        return False
    
    def test_config(self) -> Tuple[bool, str]:
        """
        测试Nginx配置文件语法
        
        Returns:
            (is_valid, message)
        """
        if not self._nginx_path or not self._config_path:
            return False, "Nginx path or config path not set"
        
        try:
            result = subprocess.run(
                [self._nginx_path, "-t", "-c", self._config_path],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                # 提取成功消息中的配置文件路径
                output = result.stderr.strip()  # nginx -t输出到stderr
                logger.info(f"Config test passed: {output}")
                return True, output
            else:
                # 提取错误信息
                error_output = result.stderr.strip()
                logger.error(f"Config test failed: {error_output}")
                return False, error_output
                
        except subprocess.TimeoutExpired:
            logger.error("Config test timeout")
            return False, "Config test timeout (10s)"
        except Exception as e:
            logger.error(f"Config test error: {e}")
            return False, str(e)
    
    def start_nginx(self) -> Tuple[bool, str]:
        """
        启动Nginx服务
        
        Returns:
            (success, message)
        """
        if not self._nginx_path or not self._config_path:
            return False, "Nginx path or config path not set"
        
        # 检查是否已经在运行
        if self.is_nginx_running():
            return False, "Nginx is already running"
        
        try:
            # 使用subprocess.Popen启动Nginx（不等待）
            subprocess.Popen(
                [self._nginx_path, "-c", self._config_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
            )
            
            # 等待Nginx启动
            time.sleep(2)
            
            # 验证是否启动成功
            if self.is_nginx_running():
                logger.info("Nginx started successfully")
                return True, "Nginx started successfully"
            else:
                logger.error("Nginx failed to start")
                return False, "Nginx failed to start"
                
        except Exception as e:
            logger.error(f"Failed to start Nginx: {e}")
            return False, str(e)
    
    def stop_nginx(self) -> Tuple[bool, str]:
        """
        停止Nginx服务
        
        Returns:
            (success, message)
        """
        if not self.is_nginx_running():
            return False, "Nginx is not running"
        
        try:
            # 发送QUIT信号优雅停止（Windows需要-c参数指定配置文件）
            result = subprocess.run(
                [self._nginx_path, "-s", "quit", "-c", self._config_path],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                logger.info("Nginx stopped gracefully")
                return True, "Nginx stopped gracefully"
            else:
                error_msg = result.stderr.strip()
                logger.error(f"Failed to stop Nginx: {error_msg}")
                return False, error_msg
                
        except subprocess.TimeoutExpired:
            logger.error("Stop Nginx timeout")
            return False, "Stop timeout (10s)"
        except Exception as e:
            logger.error(f"Failed to stop Nginx: {e}")
            # 尝试强制终止
            return self._kill_nginx_processes()
    
    def reload_nginx(self) -> Tuple[bool, str]:
        """
        重载Nginx配置（不重启进程）
        
        Returns:
            (success, message)
        """
        if not self.is_nginx_running():
            return False, "Nginx is not running"
        
        try:
            # 先测试配置
            is_valid, message = self.test_config()
            if not is_valid:
                return False, f"Config test failed: {message}"
            
            # 发送reload信号（Windows需要-c参数指定配置文件）
            result = subprocess.run(
                [self._nginx_path, "-s", "reload", "-c", self._config_path],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                logger.info("Nginx configuration reloaded")
                return True, "Configuration reloaded successfully"
            else:
                error_msg = result.stderr.strip()
                logger.error(f"Failed to reload Nginx: {error_msg}")
                return False, error_msg
                
        except subprocess.TimeoutExpired:
            logger.error("Reload Nginx timeout")
            return False, "Reload timeout (10s)"
        except Exception as e:
            logger.error(f"Failed to reload Nginx: {e}")
            return False, str(e)
    
    def is_nginx_running(self) -> bool:
        """检查Nginx是否正在运行."""
        try:
            for proc in psutil.process_iter(['name', 'pid']):
                if proc.info['name'] == 'nginx.exe':
                    return True
            return False
        except Exception as e:
            logger.debug(f"Error checking Nginx process: {e}")
            return False
    
    def _kill_nginx_processes(self) -> Tuple[bool, str]:
        """强制终止所有Nginx进程."""
        try:
            killed = 0
            for proc in psutil.process_iter(['name', 'pid']):
                if proc.info['name'] == 'nginx.exe':
                    proc.kill()
                    killed += 1
            
            if killed > 0:
                logger.info(f"Force killed {killed} Nginx processes")
                return True, f"Force killed {killed} processes"
            else:
                return False, "No Nginx processes found"
                
        except Exception as e:
            logger.error(f"Failed to kill Nginx processes: {e}")
            return False, str(e)
    
    def get_nginx_processes(self) -> List[psutil.Process]:
        """获取所有Nginx进程对象."""
        processes = []
        try:
            for proc in psutil.process_iter(['name', 'pid']):
                if proc.info['name'] == 'nginx.exe':
                    processes.append(proc)
        except Exception as e:
            logger.debug(f"Error getting Nginx processes: {e}")
        
        return processes
    
    def get_process_info(self) -> Optional[NginxProcessInfo]:
        """获取Nginx进程详细信息."""
        processes = self.get_nginx_processes()
        if not processes:
            return None
        
        try:
            info = NginxProcessInfo()
            worker_pids = []
            total_cpu = 0.0
            total_memory = 0.0
            memory_info = {}
            
            for proc in processes:
                if proc.is_running():
                    # Master process (usually the first one)
                    if info.pid is None:
                        info.pid = proc.pid
                        # Try to get start time from master process
                        try:
                            info.start_time = datetime.fromtimestamp(proc.create_time())
                            info.uptime_seconds = int(time.time() - proc.create_time())
                        except Exception:
                            pass
                    else:
                        worker_pids.append(proc.pid)
                    
                    # Accumulate resource usage (non-blocking)
                    try:
                        # 使用非阻塞方式获取CPU使用率（不传入interval参数）
                        cpu_percent = proc.cpu_percent(interval=None)
                        if cpu_percent is not None:
                            total_cpu += cpu_percent
                        
                        total_memory += proc.memory_percent()
                        
                        if not memory_info:
                            mem = proc.memory_info()
                            memory_info = {
                                "rss": mem.rss,
                                "vms": mem.vms
                            }
                    except Exception:
                        pass
            
            info.worker_pids = worker_pids
            info.cpu_percent = round(total_cpu, 2)
            info.memory_percent = round(total_memory, 2)
            info.memory_info = memory_info
            
            return info
            
        except Exception as e:
            logger.error(f"Failed to get process info: {e}")
            return None
    
    def get_status(self) -> NginxStatus:
        """获取Nginx完整状态."""
        status = NginxStatus(
            nginx_path=self._nginx_path,
            config_path=self._config_path
        )
        
        # 检查配置文件状态
        if self._config_path and Path(self._config_path).exists():
            status.config_last_modified = datetime.fromtimestamp(
                Path(self._config_path).stat().st_mtime
            )
        
        # 设置进程状态
        if self.is_nginx_running():
            status.status = NginxProcessStatus.RUNNING
            status.process_info = self.get_process_info()
        else:
            status.status = NginxProcessStatus.STOPPED
        
        # 测试配置
        if self._config_path and Path(self._config_path).exists():
            is_valid, message = self.test_config()
            status.config_test_status = (
                ConfigTestStatus.SUCCESS if is_valid else ConfigTestStatus.FAILED
            )
            status.config_test_message = message
        
        return status
    
    def backup_config(self, config_path: Optional[str] = None) -> Optional[Path]:
        """
        备份Nginx配置文件
        
        Args:
            config_path: 配置文件路径，None则使用self._config_path
            
        Returns:
            备份文件路径
        """
        if config_path is None:
            config_path = self._config_path
        
        if not config_path or not Path(config_path).exists():
            logger.error(f"Config file not found: {config_path}")
            return None
        
        try:
            config_file = Path(config_path)
            
            # 创建备份目录
            backup_dir = config_file.parent / "backups"
            backup_dir.mkdir(exist_ok=True)
            
            # 生成备份文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{config_file.stem}_{timestamp}.conf.bak"
            backup_path = backup_dir / backup_name
            
            # 读取并写入备份
            content = config_file.read_text(encoding="utf-8")
            backup_path.write_text(content, encoding="utf-8")
            
            logger.info(f"Config backup created: {backup_path}")
            return backup_path
            
        except Exception as e:
            logger.error(f"Failed to backup config: {e}")
            return None
    
    def open_config_directory(self) -> bool:
        """打开配置文件所在目录."""
        if not self._config_path:
            return False
        
        try:
            config_dir = Path(self._config_path).parent
            if config_dir.exists():
                subprocess.Popen(["explorer", str(config_dir)])
                return True
        except Exception as e:
            logger.error(f"Failed to open config directory: {e}")
        
        return False
    
    def open_config_in_editor(self) -> bool:
        """在默认编辑器中打开配置文件."""
        if not self._config_path or not Path(self._config_path).exists():
            return False
        
        try:
            subprocess.Popen(["notepad", self._config_path])
            return True
        except Exception as e:
            logger.error(f"Failed to open config in editor: {e}")
            return False