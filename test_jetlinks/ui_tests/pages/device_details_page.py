class DeviceDetailsPage:
    def __init__(self, page):
        self.page = page
        # 顶部设备名
        self.device_name = page.locator(".deviceDetailHead")
        # 产品名：在描述列表里，找到包含"产品名称"标签的行，再取后面内容单元格里的 span
        self.product_name = (
            page.locator("th:has-text('产品名称')")
            .locator("xpath=./following-sibling::td[1]")
            .locator("span.j-ellipsis")
        )
        # 运行状态 tab 和面板
        self.running_tab = page.locator("span:has-text('运行状态')")
        self.running_panel = page.locator("[role='tabpanel']").filter(has=page.locator("span:has-text('温度')"))

    def goto_running_status(self):
        """切换到运行状态页签，等待面板可见"""
        self.running_tab.click()
        self.running_panel.wait_for(state = "visible", timeout = 3000)
        return self

    def get_temperature(self):
        """
        获取运行状态里的温度数值。
        结构示例：
        <span>温度</span>
        <span class="j-ellipsis j-ellipsis-line-clamp ...">36.80</span>
        """
        # 先定位到“温度”标签所在的父级容器（比如一个 div 行）
        temp_label = self.running_panel.locator("span:has-text('温度')")
        # 获取父容器，再在父容器内定位紧跟着的数值 span
        # 通常这两个 span 是兄弟节点，可以通过 CSS 相邻选择器或 XPath 获取
        temp_value = temp_label.locator("xpath=following-sibling::span[contains(@class, 'j-ellipsis')]")
        return temp_value.inner_text().strip()