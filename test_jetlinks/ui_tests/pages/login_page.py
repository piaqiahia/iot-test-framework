class LoginPage:
    def __init__(self, page):
        self.page = page
        self.username_input = page.locator("#form_item_username") # 登录框id 优先使用id
        self.password_input = page.locator("#form_item_password")
        self.submit_btn = page.locator("form button[type='submit']") # 直接找 login-form 里的提交按钮

    def goto(self, base_url = "http://localhost:8848"):
        self.page.goto(f"{base_url}/#/login")
        return self # 方便链式调用

    def login(self, username = "admin", password = "123456Qwe"):
        """执行登录操作"""
        # 等待账号输入框可见
        self.username_input.wait_for(state="visible", timeout=10000)
        self.username_input.fill(username)
        self.password_input.fill(password)
        # 等待登录按钮可见并可点击
        self.submit_btn.wait_for(state="visible", timeout=10000)
        self.submit_btn.click()
        # 不等待特定 URL，等待页面网络空闲或特定元素出现 防初始化
        self.page.wait_for_load_state("networkidle")
        return self