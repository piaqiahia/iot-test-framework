class DeviceDetailsPage:
    def __init__(self, page, labels):
        self.page = page
        self.labels = labels
        self.device_name = page.locator(".deviceDetailHead")
        self.product_name = (
            page.locator(f"th:has-text('{labels['product_name']}')")
            .locator("xpath=./following-sibling::td[1]")
            .locator("span.j-ellipsis")
        )
        self.running_tab = page.locator(f"span:has-text('{labels['running_status']}')")
        self.running_panel = page.locator("[role='tabpanel']").filter(
            has=page.locator(f"span:has-text('{labels['temperature']}')")
        )

    def goto_running_status(self):
        self.running_tab.click()
        self.running_panel.wait_for(state="visible", timeout=3000)
        return self

    def get_temperature(self):
        temp_label = self.running_panel.locator(f"span:has-text('{self.labels['temperature']}')")
        temp_value = temp_label.locator("xpath=following-sibling::span[contains(@class, 'j-ellipsis')]")
        return temp_value.inner_text().strip()

    def get_product_name(self):
        """返回详情页中‘产品名称’对应的值（不依赖表头文本）"""
        # 直接获取 ant-descriptions 表格中第二行的 value （第一行是设备名称，第二行是产品名称）
        # 或者更简单：查找所有 span.j-ellipsis 并取第二个（通常设备名是第一个，产品名是第二个）
        items = self.page.locator(".ant-descriptions-item-content span.j-ellipsis").all_inner_texts()
        if len(items) >= 2:
            return items[1]
        return ""