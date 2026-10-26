from pages.base_page import BasePage

class LoginPage(BasePage):
    USERNAME = ("id", "user-name")
    PASSWORD = ("id", "password")
    LOGIN_BTN = ("id", "login-button")
    ERROR_MSG = ("css selector", "[data-test='error']")

    def open(self):
        super().open("https://www.saucedemo.com/")

    def submit_credentials(self, username, password):
        """只填充并提交登录表单，不判断是否跳转。

        成功和失败两种结果都从这一步出发，所以这里不能等 inventory.html：
        失败场景的 URL 永远停留在登录页，等下去只会白等到超时。
        """
        self.type(self.USERNAME, username)
        self.type(self.PASSWORD, password)
        self.click(self.LOGIN_BTN)

    def login(self, username, password):
        """登录并等待进入库存页——仅适用于预期成功的场景。

        预期失败的场景请改用 submit_credentials()，再断言错误提示。
        """
        self.submit_credentials(username, password)
        self.wait.until_url_contains("inventory.html")

    def get_error_message(self):
        """等待登录错误提示可见并返回文本（仅适用于预期失败的场景）。"""
        return self.get_text(self.ERROR_MSG)