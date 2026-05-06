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