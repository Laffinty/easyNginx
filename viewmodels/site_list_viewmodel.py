"""Site list ViewModel - Manages site list and selection."""

from typing import List, Optional, Dict
from PySide6.QtCore import QObject, Signal, Property
from loguru import logger
from models.site_config import SiteConfigBase
from models.nginx_status import SiteListItem


class SiteListViewModel(QObject):
    """
    站点列表ViewModel
    
    职责：
    1. 管理站点列表数据
    2. 处理站点选择
    3. 提供站点过滤和搜索
    """
    
    # 信号定义
    site_selected = Signal(str)  # 站点被选中
    site_double_clicked = Signal(str)  # 站点双击
    
    def __init__(self):
        """初始化站点列表ViewModel."""
        super().__init__()
        self._sites: List[SiteConfigBase] = []
        self._site_items: List[SiteListItem] = []
        self._selected_site: Optional[SiteListItem] = None
        self._filter_text: str = ""
        
        logger.info("SiteListViewModel initialized")
    
    def update_sites(self, sites: List[SiteConfigBase]):
        """更新站点列表."""
        self._sites = sites
        self._update_display_items()
    
    def update_site_items(self, items: List[SiteListItem]):
        """更新站点列表项."""
        self._site_items = items
        self._update_display_items()
    
    def _update_display_items(self):
        """更新显示项（应用过滤）."""
        # 如果有过滤文本，应用过滤
        if self._filter_text:
            filtered = [
                item for item in self._site_items
                if self._filter_text.lower() in item.site_name.lower() or
                   self._filter_text.lower() in item.server_name.lower() or
                   self._filter_text.lower() in item.site_type.lower()
            ]
            self.items_changed.emit()
        else:
            self.items_changed.emit()
    
    # Property定义
    items_changed = Signal()
    
    @Property(list, notify=items_changed)
    def items(self) -> List[SiteListItem]:
        """获取列表项."""
        if self._filter_text:
            return [
                item for item in self._site_items
                if self._filter_text.lower() in item.site_name.lower() or
                   self._filter_text.lower() in item.server_name.lower() or
                   self._filter_text.lower() in item.site_type.lower()
            ]
        return self._site_items
    
    @Property(int, notify=items_changed)
    def count(self) -> int:
        """获取站点数量."""
        return len(self._site_items)
    
    selected_site_changed = Signal()
    
    @Property(str, notify=selected_site_changed)
    def selected_site_name(self) -> str:
        """获取选中站点名称."""
        return self._selected_site.site_name if self._selected_site else ""
    
    # 方法
    def select_site(self, site_name: str):
        """选择站点."""
        try:
            site_item = next((item for item in self._site_items if item.site_name == site_name), None)
            if site_item:
                self._selected_site = site_item
                self.selected_site_changed.emit()
                self.site_selected.emit(site_name)
                logger.info(f"Site selected: {site_name}")
        except Exception as e:
            logger.error(f"Failed to select site: {e}")
    
    def get_selected_site(self) -> Optional[SiteListItem]:
        """获取选中的站点."""
        return self._selected_site
    
    def set_filter(self, filter_text: str):
        """设置过滤文本."""
        self._filter_text = filter_text
        self.items_changed.emit()
    
    def clear_filter(self):
        """清除过滤."""
        self._filter_text = ""
        self.items_changed.emit()
    
    def get_site_by_name(self, site_name: str) -> Optional[SiteListItem]:
        """根据名称获取站点项."""
        try:
            return next((item for item in self._site_items if item.site_name == site_name), None)
        except Exception:
            return None
    
    def get_site_types_count(self) -> Dict[str, int]:
        """获取各类型站点数量."""
        counts = {"static": 0, "php": 0, "proxy": 0}
        for item in self._site_items:
            if item.site_type in counts:
                counts[item.site_type] += 1
        return counts