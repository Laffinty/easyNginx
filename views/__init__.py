"""UI components."""

from .main_window import MainWindow
from .site_list_widget import SiteListWidget
from .config_pages import StaticSitePage, PHPSitePage, ProxySitePage
from .status_bar import StatusBar

__all__ = [
    "MainWindow",
    "SiteListWidget",
    "StaticSitePage",
    "PHPSitePage", 
    "ProxySitePage",
    "StatusBar"
]