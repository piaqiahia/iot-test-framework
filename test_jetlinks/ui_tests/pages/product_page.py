class ProductPage:
    def __init__(self, page):
        self.page = page
        # 左侧菜单
        self.device_menu = page.locator("[data-menu-id='/iot/device']")
        self.product_submenu = page.locator("[data-menu-id='/iot/device/Product']")

        # 产品新增按钮
        self.add_btn = page.locator("button:has(svg[data-icon='plus'])")

        # 新增产品弹窗
        self.product_id_input = page.locator("#form_item_id")
        self.product_name_input = page.locator("#form_item_name")

        # 设备类型选择（单选）
        self.device_type_direct = page.locator(".j-card-select-item:has(img[src='/assets/device-type-1.png'])")

        # 确定按钮
        self.confirm_btn = page.locator("button.ant-btn-primary").last

        # 创建成功后的“关闭”按钮：.ant-modal-footer 里的 ant-btn-default 按钮
        self.close_success_btn = page.locator(".ant-modal-footer button.ant-btn-default")

        # 确认启用按钮
        self.confirm_enable_btn = page.locator(".ant-modal-confirm button.ant-btn-primary").last

    def goto_product_list(self):
        """导航到产品列表页"""
        self.device_menu.click()
        self.product_submenu.click()
        # 等待新增按钮出现（用 plus 图标判断，中英文通用）
        self.page.wait_for_selector("button:has(svg[data-icon='plus'])", timeout = 5000)

    def create_product(self, product_id, product_name):
        """创建产品（完全不依赖文本）"""
        # 点击新增
        self.add_btn.click()
        # 等待弹窗渲染
        self.page.wait_for_selector("#form_item_id", timeout=5000)
        # 填写表单
        self.product_id_input.fill(product_id)
        self.product_name_input.fill(product_name)
        # 选择设备类型
        self.device_type_direct.click()
        # 提交
        self.confirm_btn.click()
        # 等待窗口关闭，列表刷新
        self.page.wait_for_timeout(2000)

    def close_success_dialog(self):
        """关闭创建/操作成功后的提示框"""
        self.close_success_btn.wait_for(state = "visible", timeout = 5000)
        self.close_success_btn.click()
        self.page.wait_for_timeout(1000)

    def enable_product(self, product_id):
        """
        启用指定产品
        :param product_id: 产品 ID，用于定位该产品的卡片容器
        """
        # 定位该产品所在的行/卡片容器（id 为产品 ID）
        product_container = self.page.locator(f"#{product_id}")
        product_container.wait_for(state="visible", timeout=5000)

        # 在该容器内找启用按钮
        enable_btn = product_container.locator("button.ant-btn-default:has(svg[data-icon='check-circle'])")
        enable_btn.wait_for(state="visible", timeout=5000)
        enable_btn.click()

        # 处理确认弹窗
        self.confirm_enable_btn.wait_for(state="visible", timeout=5000)
        self.confirm_enable_btn.click()

        self.page.wait_for_timeout(2000)
        self.close_success_dialog()