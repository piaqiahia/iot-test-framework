class LoginPage:
    def __init__(self, page):
        self.page = page
        self.username_input = page.locator("#form_item_username") # 登录框id 优先使用id
        self.password_input = page.locator("#form_item_password")
        self.submit_btn = page.locator("button:has-text('登 录')") # has-text 模糊匹配 避免空格带来的匹配失败

    def goto(self, base_url = "http://localhost:8848"):
        self.page.goto(f"{base_url}/#/login")
        return self # 方便链式调用

    def login(self, username = "admin", password = "123456Qwe"):
        """执行登录操作"""
        self.username_input.fill(username)
        self.password_input.fill(password)
        self.submit_btn.click()
        self.page.wait_for_url(f"http://localhost:8848/#/iot/home", timeout = 5000)
        return self