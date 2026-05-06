from .device_details_page import DeviceDetailsPage

class DeviceListPage:
    def __init__(self, page):
        self.page = page
        self.device_cards = page.locator(".card-content-top-line")

    def get_device_card_by_name(self, device_name):
        name_span = self.page.locator("span[style*='font-weight: 600']", has_text=device_name)
        name_span.wait_for(state="visible", timeout=10000)
        card = self.page.locator(".card-content-top-line").filter(has=name_span)
        return card

    def get_device_status(self, device_name):
        """
        获取设备状态文本。
        状态在卡片内的 .card-state .ant-badge-status-text
        """
        card = self.get_device_card_by_name(device_name)
        status_elem = card.locator(".card-state .ant-badge-status-text")
        status_elem.wait_for(state="visible", timeout=5000)
        return status_elem.inner_text()

    def click_device(self, device_name, labels):
        name_span = self.page.locator("span[style*='font-weight: 600']", has_text=device_name)
        name_span.click()
        self.page.wait_for_selector(".deviceDetailHead", timeout=10000)
        return DeviceDetailsPage(self.page, labels)