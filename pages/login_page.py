from pages.base_page import BasePage

class LoginPage(BasePage):
    USERNAME = ("id", "user-name")
    PASSWORD = ("id", "password")
    LOGIN_BTN = ("id", "login-button")
    ERROR_MSG = ("css selector", "[data-test='error']")

    def open(self):
        super().open("https://www.saucedemo.com/")

    def login(self, username, password):
        self.type(self.USERNAME, username)
        self.type(self.PASSWORD, password)
        self.click(self.LOGIN_BTN)
        self.wait.until_url_contains("inventory.html")

    def get_error_message(self):
        return self.get_text(self.ERROR_MSG)