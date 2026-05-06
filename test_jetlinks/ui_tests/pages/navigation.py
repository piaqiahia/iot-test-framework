from .device_list_page import DeviceListPage

class Navigation:
    def __init__(self, page):
        self.page = page
        # 顶级菜单 "设备管理"，通过 data-menu-id 定位最稳定
        self.device_menu = page.locator("[data-menu-id='/iot/device']")
        # 子菜单 "设备"
        self.device_submenu = page.locator("[data-menu-id='/iot/device/Instance']")

    def goto_device_list(self):
        """点击菜单进入设备列表页"""
        self.device_menu.click()
        self.device_submenu.click()
        # 等待页面加载：出现包含“设备”的面包屑或卡片容器
        self.page.wait_for_selector(".card-content-top-line", timeout = 5000)
        return DeviceListPage(self.page)