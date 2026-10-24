from utils.wait_utils import WaitUtils

class BasePage:
    def __init__(self, driver):
        self.driver = driver
        self.wait = WaitUtils(driver)

    def open(self, url):
        self.driver.get(url)

    def click(self, locator):
        self.wait.click(locator)

    def type(self, locator, text):
        self.wait.type_text(locator, text)

    def get_text(self, locator):
        return self.wait.text_of(locator)