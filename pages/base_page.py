from selenium.common.exceptions import WebDriverException

from utils.wait_utils import WaitUtils

# Chrome 网络层的瞬时错误：链路上偶发 RST/超时，重试一次通常就好。
# saucedemo 托管在 GitHub Pages，国内链路实测会偶发 ERR_CONNECTION_RESET。
_NETWORK_ERROR_MARKERS = (
    "net::ERR_CONNECTION",
    "net::ERR_NAME_NOT_RESOLVED",
    "net::ERR_TIMED_OUT",
    "net::ERR_NETWORK",
    "net::ERR_EMPTY_RESPONSE",
    "net::ERR_INTERNET_DISCONNECTED",
)


def _is_network_error(error) -> bool:
    text = str(error)
    return any(marker in text for marker in _NETWORK_ERROR_MARKERS)


class BasePage:
    def __init__(self, driver):
        self.driver = driver
        self.wait = WaitUtils(driver)

    def open(self, url, attempts=3):
        """打开页面；遇到 Chrome 网络层瞬时错误自动重试。

        这类错误（ERR_CONNECTION_RESET / ERR_TIMED_OUT 等）不是页面或定位问题，
        重试即可；其它 WebDriverException 仍按原样抛出，避免掩盖真实故障。
        """
        last_error = None
        for _ in range(max(1, attempts)):
            try:
                self.driver.get(url)
                return
            except WebDriverException as exc:
                last_error = exc
                if not _is_network_error(exc):
                    raise
        raise last_error

    def click(self, locator):
        self.wait.click(locator)

    def type(self, locator, text):
        self.wait.type_text(locator, text)

    def get_text(self, locator):
        return self.wait.text_of(locator)
