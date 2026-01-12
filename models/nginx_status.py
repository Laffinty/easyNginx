"""Nginx status and process information models."""

from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class NginxProcessStatus(str, Enum):
    """Nginx进程状态."""
    RUNNING = "running"
    STOPPED = "stopped"
    STARTING = "starting"
    STOPPING = "stopping"
    ERROR = "error"
    UNKNOWN = "unknown"


class ConfigTestStatus(str, Enum):
    """配置测试状态."""
    SUCCESS = "success"
    FAILED = "failed"
    TESTING = "testing"
    NOT_TESTED = "not_tested"


class NginxProcessInfo(BaseModel):
    """Nginx进程详细信息."""
    pid: Optional[int] = Field(default=None, description="主进程PID")
    worker_pids: list[int] = Field(default_factory=list, description="工作进程PID列表")
    cpu_percent: float = Field(default=0.0, description="CPU使用率")
    memory_percent: float = Field(default=0.0, description="内存使用率")
    memory_info: Dict[str, float] = Field(default_factory=dict, description="内存信息")
    start_time: Optional[datetime] = Field(default=None, description="启动时间")
    uptime_seconds: int = Field(default=0, description="运行时长（秒）")


class NginxStatus(BaseModel):
    """Nginx整体状态."""
    
    # 进程状态
    status: NginxProcessStatus = Field(default=NginxProcessStatus.UNKNOWN, description="Nginx状态")
    
    # 配置信息
    nginx_path: Optional[str] = Field(default=None, description="Nginx可执行文件路径")
    config_path: Optional[str] = Field(default=None, description="Nginx配置文件路径")
    config_test_status: ConfigTestStatus = Field(
        default=ConfigTestStatus.NOT_TESTED, 
        description="配置测试结果"
    )
    config_test_message: Optional[str] = Field(default=None, description="配置测试消息")
    config_last_modified: Optional[datetime] = Field(default=None, description="配置文件最后修改时间")
    
    # 进程详细信息
    process_info: Optional[NginxProcessInfo] = Field(default=None, description="进程信息")
    
    # 站点统计
    total_sites: int = Field(default=0, description="站点总数")
    running_sites: int = Field(default=0, description="运行中的站点数")
    sites_by_type: Dict[str, int] = Field(default_factory=dict, description="按类型统计站点")
    
    # 性能指标
    last_check_time: datetime = Field(default_factory=datetime.now, description="最后检查时间")
    check_interval: int = Field(default=2, description="检查间隔（秒）")
    
    class Config:
        """Pydantic配置."""
        use_enum_values = True
    
    def is_running(self) -> bool:
        """检查Nginx是否正在运行."""
        return self.status == NginxProcessStatus.RUNNING
    
    def can_manage(self) -> bool:
        """检查是否可以管理Nginx."""
        return self.nginx_path is not None and self.config_path is not None
    
    def get_status_color(self) -> str:
        """获取状态颜色（用于UI）."""
        color_map = {
            NginxProcessStatus.RUNNING: "#28a745",  # 绿色
            NginxProcessStatus.STOPPED: "#6c757d",  # 灰色
            NginxProcessStatus.STARTING: "#ffc107",  # 黄色
            NginxProcessStatus.STOPPING: "#fd7e14",  # 橙色
            NginxProcessStatus.ERROR: "#dc3545",  # 红色
            NginxProcessStatus.UNKNOWN: "#6c757d"  # 灰色
        }
        return color_map.get(self.status, "#6c757d")
    
    def get_status_icon(self) -> str:
        """获取状态图标."""
        icon_map = {
            NginxProcessStatus.RUNNING: "●",  # 圆点
            NginxProcessStatus.STOPPED: "○",
            NginxProcessStatus.STARTING: "⟳",
            NginxProcessStatus.STOPPING: "◐",
            NginxProcessStatus.ERROR: "✕",
            NginxProcessStatus.UNKNOWN: "?"
        }
        return icon_map.get(self.status, "?")
    
    def get_memory_usage_mb(self) -> float:
        """获取内存使用（MB）."""
        if self.process_info and self.process_info.memory_info:
            return self.process_info.memory_info.get("rss", 0) / 1024 / 1024
        return 0.0
    
    def get_uptime_display(self) -> str:
        """获取运行时间显示文本."""
        if not self.process_info or self.process_info.uptime_seconds == 0:
            return "-"
        
        seconds = self.process_info.uptime_seconds
        
        if seconds < 60:
            return f"{seconds}秒"
        elif seconds < 3600:
            return f"{seconds // 60}分钟"
        elif seconds < 86400:
            return f"{seconds // 3600}小时 {(seconds % 3600) // 60}分钟"
        else:
            days = seconds // 86400
            hours = (seconds % 86400) // 3600
            return f"{days}天 {hours}小时"


class SiteListItem(BaseModel):
    """站点列表项，用于UI展示."""
    
    id: str = Field(..., description="站点唯一ID")
    site_name: str = Field(..., description="站点名称")
    site_type: str = Field(..., description="站点类型")
    listen_port: int = Field(..., description="监听端口")
    server_name: str = Field(..., description="服务器名称")
    enable_https: bool = Field(..., description="是否启用HTTPS")
    enable_http_redirect: bool = Field(default=False, description="是否启用80端口重定向")
    status: str = Field(default="configured", description="状态")
    config_file_path: Optional[str] = Field(default=None, description="配置文件路径")
    last_modified: Optional[datetime] = Field(default=None, description="最后修改时间")
    is_managed: bool = Field(default=True, description="是否由easyNginx管理")
    
    def get_display_name(self) -> str:
        """获取显示名称."""
        https_icon = "🔒" if self.enable_https else ""
        return f"{https_icon} {self.site_name} ({self.site_type})"
    
    def get_status_color(self) -> str:
        """获取状态颜色."""
        color_map = {
            "running": "#28a745",  # 绿色
            "configured": "#17a2b8",  # 青色
            "error": "#dc3545",  # 红色
            "disabled": "#6c757d"  # 灰色
        }
        return color_map.get(self.status, "#6c757d")