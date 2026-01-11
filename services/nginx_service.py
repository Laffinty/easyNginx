"""Nginx process management service."""

import subprocess
import psutil
import time
import threading
from pathlib import Path
from typing import Optional, Tuple, List
from datetime import datetime
from loguru import logger
from models.nginx_status import NginxStatus, NginxProcessStatus, ConfigTestStatus, NginxProcessInfo
from utils.encoding_utils import read_file_robust


# 配置常量
NGINX_START_TIMEOUT = 10  # Nginx启动超时时间（秒）
NGINX_START_CHECK_INTERVAL = 0.5  # 启动检查间隔（秒）
NGINX_STOP_TIMEOUT = 10  # Nginx停止超时时间（秒）
NGINX_RELOAD_TIMEOUT = 10  # Nginx重载超时时间（秒）
NGINX_CONFIG_TEST_TIMEOUT = 10  # 配置测试超时时间（秒）
NGINX_VERSION_CHECK_TIMEOUT = 5  # 版本检查超时时间（秒）
CPU_USAGE_INTERVAL = 0.1  # CPU使用率采样间隔（秒）


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
        
        # 新增：配置文件测试缓存，避免频繁测试
        self._last_config_mtime = None  # 记录上次配置文件修改时间
        self._last_test_result = (True, "")  # 缓存上次测试结果（is_valid, message）
        self._config_cache_lock = threading.Lock()  # 配置缓存线程锁
        
        # 新增：进程状态管理
        self._operation_lock = threading.Lock()  # 操作锁，防止并发操作
        self._last_operation_result = (True, "")  # 上次操作结果
        
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
                encoding='utf-8',
                errors='replace',
                timeout=NGINX_VERSION_CHECK_TIMEOUT
            )
            if result.returncode == 0:
                path = result.stdout.strip().split('\n')[0] if result.stdout else ""
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
        
        logger.info("Nginx executable not found")
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
        
        logger.info("Nginx config file not found")
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
                encoding='utf-8',
                errors='replace',
                timeout=5
            )
            if result.returncode == 0:
                version = result.stderr.strip() if result.stderr else "Nginx available"
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
                encoding='utf-8',  # 明确指定UTF-8编码
                errors='replace',  # 解码错误时用?替代，避免崩溃
                timeout=NGINX_CONFIG_TEST_TIMEOUT
            )
            
            if result.returncode == 0:
                # 提取成功消息中的配置文件路径
                output = result.stderr.strip() if result.stderr else "Configuration test successful"
                logger.info(f"Config test passed: {output}")
                return True, output
            else:
                # 提取错误信息
                error_output = result.stderr.strip() if result.stderr else "Unknown error"
                logger.error(f"Config test failed: {error_output}")
                return False, error_output
                
        except subprocess.TimeoutExpired:
            logger.error("Config test timeout")
            return False, f"Config test timeout ({NGINX_CONFIG_TEST_TIMEOUT}s)"
        except Exception as e:
            logger.error(f"Config test error: {e}")
            return False, str(e)
    
    def start_nginx(self) -> Tuple[bool, str]:
        """
        启动Nginx服务
        
        Returns:
            (success, message)
        """
        # 使用操作锁防止并发启动
        if not self._operation_lock.acquire(blocking=False):
            return False, "Another operation is in progress"
        
        try:
            if not self._nginx_path or not self._config_path:
                return False, "Nginx path or config path not set"
            
            # 检查是否已经在运行
            if self.is_nginx_running():
                return False, "Nginx is already running"
            
            # 检查Nginx可执行文件是否存在
            if not Path(self._nginx_path).exists():
                return False, f"Nginx executable not found: {self._nginx_path}"
            
            # 检查配置文件是否存在
            if not Path(self._config_path).exists():
                return False, f"Nginx config file not found: {self._config_path}"
            
            # 先测试配置文件
            is_valid, test_message = self.test_config()
            if not is_valid:
                return False, f"Configuration test failed: {test_message}"
            
            # 使用subprocess.Popen启动Nginx（不等待）
            process = subprocess.Popen(
                [self._nginx_path, "-c", self._config_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,  # 改为捕获stderr以获取错误信息
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
            )
            
            # 等待进程创建完成
            try:
                # 等待一小段时间让进程启动
                returncode = process.wait(timeout=3)
                if returncode != 0:
                    # 进程立即退出，读取错误信息
                    error_msg = "Unknown error"
                    if process.stderr:
                        try:
                            error_output = process.stderr.read()
                            if error_output:
                                error_msg = error_output.decode('utf-8', errors='replace')
                        except Exception as e:
                            logger.debug(f"Error reading stderr: {e}")
                    
                    logger.error(f"Nginx process exited immediately with code {returncode}: {error_msg}")
                    return False, f"Nginx failed to start: {error_msg}"
            except subprocess.TimeoutExpired:
                # 进程仍在运行，这是正常的
                pass
            finally:
                # 确保关闭管道
                if process.stderr:
                    try:
                        process.stderr.close()
                    except Exception:
                        pass
            
            # 等待Nginx完全启动
            max_wait = NGINX_START_TIMEOUT
            check_interval = NGINX_START_CHECK_INTERVAL
            for _ in range(int(max_wait / check_interval)):
                if self.is_nginx_running():
                    logger.info("Nginx started successfully")
                    return True, "Nginx started successfully"
                time.sleep(check_interval)
            
            # 超时未检测到进程
            logger.error("Nginx failed to start within timeout period")
            return False, "Nginx failed to start (timeout)"
                
        except Exception as e:
            logger.error(f"Failed to start Nginx: {e}")
            return False, str(e)
        finally:
            self._operation_lock.release()
    
    def stop_nginx(self) -> Tuple[bool, str]:
        """
        停止Nginx服务
        
        Returns:
            (success, message)
        """
        # 使用操作锁防止并发停止
        if not self._operation_lock.acquire(blocking=False):
            return False, "Another operation is in progress"
        
        try:
            if not self.is_nginx_running():
                return False, "Nginx is not running"
            
            # 发送QUIT信号优雅停止（Windows需要-c参数指定配置文件）
            result = subprocess.run(
                [self._nginx_path, "-s", "quit", "-c", self._config_path],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=NGINX_STOP_TIMEOUT
            )
            
            if result.returncode == 0:
                logger.info("Nginx stopped gracefully")
                return True, "Nginx stopped gracefully"
            else:
                error_msg = result.stderr.strip() if result.stderr else "Unknown error"
                logger.error(f"Failed to stop Nginx: {error_msg}")
                return False, error_msg
                
        except subprocess.TimeoutExpired:
            logger.error("Stop Nginx timeout")
            return False, f"Stop timeout ({NGINX_STOP_TIMEOUT}s)"
        except Exception as e:
            logger.error(f"Failed to stop Nginx: {e}")
            # 尝试强制终止
            return self._kill_nginx_processes()
        finally:
            self._operation_lock.release()
    
    def reload_nginx(self) -> Tuple[bool, str]:
        """
        重载Nginx配置（不重启进程）
        
        Returns:
            (success, message)
        """
        # 使用操作锁防止并发重载
        if not self._operation_lock.acquire(blocking=False):
            return False, "Another operation is in progress"
        
        try:
            if not self.is_nginx_running():
                return False, "Nginx is not running"
            
            # 先测试配置
            is_valid, message = self.test_config()
            if not is_valid:
                return False, f"Config test failed: {message}"
            
            # 发送reload信号（Windows需要-c参数指定配置文件）
            result = subprocess.run(
                [self._nginx_path, "-s", "reload", "-c", self._config_path],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=NGINX_RELOAD_TIMEOUT
            )
            
            if result.returncode == 0:
                logger.info("Nginx configuration reloaded")
                return True, "Configuration reloaded successfully"
            else:
                error_msg = result.stderr.strip() if result.stderr else "Unknown error"
                logger.error(f"Failed to reload Nginx: {error_msg}")
                return False, error_msg
                
        except subprocess.TimeoutExpired:
            logger.error("Reload Nginx timeout")
            return False, f"Reload timeout ({NGINX_RELOAD_TIMEOUT}s)"
        except Exception as e:
            logger.error(f"Failed to reload Nginx: {e}")
            return False, str(e)
        finally:
            self._operation_lock.release()
    
    def is_nginx_running(self) -> bool:
        """检查Nginx是否正在运行."""
        try:
            for proc in psutil.process_iter(['name', 'pid']):
                try:
                    if proc.info.get('name') == 'nginx.exe':
                        # 验证进程是否真正存在且可访问
                        if proc.is_running() and hasattr(psutil, 'STATUS_ZOMBIE') and proc.status() != psutil.STATUS_ZOMBIE:
                            return True
                except (psutil.NoSuchProcess, psutil.AccessDenied, KeyError):
                    # 进程已结束、无权限访问或信息缺失，跳过
                    continue
            return False
        except Exception as e:
            logger.debug(f"Error checking Nginx process: {e}")
            return False
    
    def _kill_nginx_processes(self) -> Tuple[bool, str]:
        """强制终止所有Nginx进程."""
        try:
            killed = 0
            failed = 0
            for proc in psutil.process_iter(['name', 'pid']):
                try:
                    if proc.info['name'] == 'nginx.exe':
                        # 检查进程是否还在运行
                        if proc.is_running():
                            proc.kill()
                            killed += 1
                except psutil.NoSuchProcess:
                    # 进程已结束，跳过
                    continue
                except psutil.AccessDenied:
                    # 无权限终止进程
                    failed += 1
                    logger.warning(f"Access denied when trying to kill process {proc.info.get('pid', 'unknown')}")
                    continue
                except Exception as e:
                    logger.debug(f"Error killing process {proc.info.get('pid', 'unknown')}: {e}")
                    continue
            
            if killed > 0:
                logger.info(f"Force killed {killed} Nginx processes")
                if failed > 0:
                    return True, f"Force killed {killed} processes, {failed} failed (access denied)"
                return True, f"Force killed {killed} processes"
            elif failed > 0:
                return False, f"Failed to kill {failed} processes (access denied)"
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
                try:
                    if proc.info['name'] == 'nginx.exe':
                        processes.append(proc)
                except (psutil.NoSuchProcess, psutil.AccessDenied, KeyError):
                    # 进程已结束或无权限访问，跳过
                    continue
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
            master_proc = None
            
            # 首先识别master进程（通常是最早创建的）
            for proc in processes:
                try:
                    if proc.is_running() and (not hasattr(psutil, 'STATUS_ZOMBIE') or proc.status() != psutil.STATUS_ZOMBIE):
                        if master_proc is None or proc.create_time() < master_proc.create_time():
                            master_proc = proc
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            if master_proc is None:
                return None  # 没有找到有效的master进程
            
            # 获取master进程信息
            try:
                info.pid = master_proc.pid
                info.start_time = datetime.fromtimestamp(master_proc.create_time())
                info.uptime_seconds = int(time.time() - master_proc.create_time())
            except Exception:
                pass
            
            # 收集所有进程的资源使用信息
            for proc in processes:
                try:
                    if proc.is_running() and (not hasattr(psutil, 'STATUS_ZOMBIE') or proc.status() != psutil.STATUS_ZOMBIE):
                        if proc.pid != master_proc.pid:
                            worker_pids.append(proc.pid)
                        
                        # Accumulate resource usage
                        try:
                            cpu_percent = proc.cpu_percent(interval=CPU_USAGE_INTERVAL)
                            if cpu_percent is not None and cpu_percent > 0:
                                total_cpu += cpu_percent
                            
                            total_memory += proc.memory_percent()
                            
                            if not memory_info:
                                mem = proc.memory_info()
                                memory_info = {
                                    "rss": mem.rss,
                                    "vms": mem.vms
                                }
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            continue
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            info.worker_pids = worker_pids
            info.cpu_percent = round(total_cpu, 2)
            info.memory_percent = round(total_memory, 2)
            info.memory_info = memory_info if memory_info else {"rss": 0, "vms": 0}
            
            return info
            
        except Exception as e:
            logger.error(f"Failed to get process info: {e}")
            return None
    
    def get_status(self) -> NginxStatus:
        """获取Nginx完整状态（优化版：减少不必要的配置测试）."""
        status = NginxStatus(
            nginx_path=self._nginx_path,
            config_path=self._config_path
        )
        
        # 检查配置文件状态
        if self._config_path and Path(self._config_path).exists():
            current_mtime = Path(self._config_path).stat().st_mtime
            status.config_last_modified = datetime.fromtimestamp(current_mtime)
            
            # 线程安全的配置缓存检查
            with self._config_cache_lock:
                # 仅当配置文件变更时才重新测试，否则使用缓存结果
                if (self._last_config_mtime is None or 
                    self._last_config_mtime != current_mtime):
                    # 配置文件有变更，执行完整测试
                    is_valid, message = self.test_config()
                    self._last_test_result = (is_valid, message)
                    self._last_config_mtime = current_mtime
                else:
                    # 配置文件未变更，使用缓存测试结果并降级日志
                    is_valid, message = self._last_test_result
                    logger.debug(f"Config unchanged, using cached test result: valid={is_valid}")
            
            status.config_test_status = (
                ConfigTestStatus.SUCCESS if is_valid else ConfigTestStatus.FAILED
            )
            status.config_test_message = message
        
        # 设置进程状态
        if self.is_nginx_running():
            status.status = NginxProcessStatus.RUNNING
            status.process_info = self.get_process_info()
        else:
            status.status = NginxProcessStatus.STOPPED
        
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
            
            # 读取并写入备份（使用健壮的编码检测）
            content = read_file_robust(config_file)
            if content is None:
                logger.error(f"无法读取配置文件进行备份: {config_file}")
                return None
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
            config_path = Path(self._config_path)
            if not config_path.exists():
                logger.warning(f"Config file does not exist: {self._config_path}")
                return False
                
            config_dir = config_path.parent
            if config_dir.exists():
                # 使用start命令替代explorer，更通用
                subprocess.Popen(["start", "", str(config_dir)], shell=True)
                return True
            else:
                logger.error(f"Config directory does not exist: {config_dir}")
                return False
        except Exception as e:
            logger.error(f"Failed to open config directory: {e}")
        
        return False
    
    def open_config_in_editor(self) -> bool:
        """在默认编辑器中打开配置文件."""
        if not self._config_path:
            return False
            
        config_path = Path(self._config_path)
        if not config_path.exists():
            logger.warning(f"Config file does not exist: {self._config_path}")
            return False
        
        try:
            # 使用start命令让系统选择默认编辑器
            subprocess.Popen(["start", "", str(config_path)], shell=True)
            return True
        except Exception as e:
            logger.error(f"Failed to open config in editor: {e}")
            return False