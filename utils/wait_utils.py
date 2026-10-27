"""统一的显式等待封装。

约定：所有元素获取都必须经过本模块。测试与 Page Object 里不用
driver.find_element / find_elements，也不直接构造 WebDriverWait，
更不用 time.sleep。

locator 统一为 (By.X, "value") 元组，例如 (By.ID, "user-name")。

超时、轮询间隔与 stale 重试次数在导入时从环境变量 WAIT_TIMEOUT /
WAIT_POLL / WAIT_STALE_RETRIES 读取，或者在构造 Wait 时显式传入覆盖。
"""

import os

from selenium.common.exceptions import (
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

DEFAULT_TIMEOUT = float(os.getenv("WAIT_TIMEOUT", "10"))
DEFAULT_POLL = float(os.getenv("WAIT_POLL", "0.5"))
DEFAULT_STALE_RETRIES = int(os.getenv("WAIT_STALE_RETRIES", "2"))

# Selenium 自带的默认忽略项只有 NoSuchElementException，
# 传入的值是"追加"而不是覆盖。页面重渲染时元素会在轮询期间失效，
# 不追加 StaleElementReferenceException 的话等待会被提前打断而不是继续重试。
IGNORED_EXCEPTIONS = (StaleElementReferenceException,)


class WaitTimeoutError(TimeoutException):
    """显式等待超时，附带定位失败所需的上下文。"""

    def __init__(self, locator, timeout, expectation, url, title):
        self.locator = locator
        self.timeout = timeout
        self.expectation = expectation
        self.url = url
        self.title = title
        super().__init__(
            f"等待超时（{timeout}s）：期望「{expectation}」\n"
            f"  locator: {locator[0]} = {locator[1]!r}\n"
            f"  页面标题: {title}\n"
            f"  当前 URL: {url}"
        )


class WaitUtils:
    """围绕一个 driver 的显式等待，所有等待失败都抛 WaitTimeoutError。"""

    def __init__(
        self,
        driver,
        timeout=DEFAULT_TIMEOUT,
        poll_frequency=DEFAULT_POLL,
        stale_retries=DEFAULT_STALE_RETRIES,
    ):
        self.driver = driver
        self.timeout = timeout
        self.poll_frequency = poll_frequency
        # 至少尝试一次，否则重试次数为 0 时无处抛出异常
        self.stale_retries = max(1, stale_retries)

    def _page_info(self):
        # 会话可能已经失效，取页面信息失败时不能掩盖原始的等待超时
        try:
            return self.driver.current_url, self.driver.title
        except WebDriverException:
            return "<会话已失效>", "<会话已失效>"

    def _until(self, locator, condition, expectation, timeout):
        timeout = self.timeout if timeout is None else timeout
        try:
            return WebDriverWait(
                self.driver,
                timeout,
                poll_frequency=self.poll_frequency,
                ignored_exceptions=IGNORED_EXCEPTIONS,
            ).until(condition)
        except TimeoutException as exc:
            url, title = self._page_info()
            raise WaitTimeoutError(locator, timeout, expectation, url, title) from exc

    def _act(self, locator, waiter, action, timeout=None):
        """等待元素后执行动作；元素失效时重新定位重试。

        每次重试都重新调用 waiter（第 1 层的等待方法），拿到的必定是新元素。
        所以最坏耗时是 stale_retries * timeout。
        """
        last_error = None
        for _ in range(self.stale_retries):
            element = waiter(locator, timeout)
            try:
                return action(element)
            except StaleElementReferenceException as exc:
                last_error = exc
        raise last_error

    def until_url_contains(self, fragment, timeout=None):
        return self._until(
            ("url", fragment),
            EC.url_contains(fragment),
            f"URL 包含 {fragment!r}",
            timeout,
        )

    # --- 第 1 层：基础等待 ---

    def visible(self, locator, timeout=None):
        """等待元素可见，返回该元素。"""
        return self._until(
            locator, EC.visibility_of_element_located(locator), "元素可见", timeout
        )

    def present(self, locator, timeout=None):
        """等待元素出现在 DOM 中，返回该元素（不要求可见）。"""
        return self._until(
            locator, EC.presence_of_element_located(locator), "元素存在于 DOM", timeout
        )

    def clickable(self, locator, timeout=None):
        """等待元素可见且可点击，返回该元素。

        只判断可见与启用，不判断是否被别的元素遮挡，
        被遮挡时会一直等到超时。
        """
        return self._until(
            locator, EC.element_to_be_clickable(locator), "元素可见且可点击", timeout
        )

    def invisible(self, locator, timeout=None):
        """等待元素不可见或从 DOM 移除，成功返回 True（此时没有元素可返回）。"""
        return self._until(
            locator,
            EC.invisibility_of_element_located(locator),
            "元素不可见",
            timeout,
        )

    def all_visible(self, locator, timeout=None):
        """等待所有匹配元素都可见，返回元素列表（至少一个）。"""
        return self._until(
            locator,
            EC.visibility_of_all_elements_located(locator),
            "所有匹配元素可见",
            timeout,
        )

    def present_all(self, locator, timeout=None):
        """等待至少一个匹配元素出现在 DOM 中，返回元素列表。"""
        return self._until(
            locator,
            EC.presence_of_all_elements_located(locator),
            "匹配元素存在于 DOM",
            timeout,
        )

    def elements_now(self, locator):
        """立即返回当前匹配的所有元素，**允许空列表、不等待**。

        用于「元素数量本身就是断言目标」的场景，典型例子是购物车为空时的
        `get_item_names()` 必须返回 `[]`：`present_all` 的语义是「等到至少
        一个出现」，空列表会被当作条件不满足而一直轮询到超时，无法表达
        「一个都没有」。所以这种场景要先等某个稳定容器出现（`present`），
        再用本方法直接取当前列表。

        注意：本方法不做任何等待，调用者要自己保证页面已渲染到位。
        """
        return self.driver.find_elements(*locator)

    # --- 第 2 层：交互 ---

    def click(self, locator, timeout=None):
        """等待元素可点击后点击它，返回 None。

        最坏耗时 stale_retries * timeout（默认 2 * 10s）。
        元素被弹层遮挡时 clickable 判断不出来，会在点击时抛
        ElementClickInterceptedException，这里不做自动重试。
        """
        return self._act(
            locator, self.clickable, lambda element: element.click(), timeout
        )

    def click_until(self, locator, waiter, timeout=None, attempts=3):
        """点击 locator，直到 `waiter()` 返回真值；未生效则重新点击。

        CI 上多次出现过「点击落空」：按钮可见可点击，点下去却什么也没发生
        （布局在图片加载时漂移、或 React 事件监听尚未挂载）。`clickable`
        只看可见+启用，判断不出这类情况，所以这里以调用方给的 `waiter`
        作为「生效」判据——通常是把本类另一个等待方法包一层 lambda：

            wait.click_until(BTN, lambda: wait.until_url_contains("step-two.html"))
            wait.click_until(BTN, lambda: wait.invisible(row))

        `waiter` 抛 `WaitTimeoutError` 视为本次未生效并重试；重试耗尽后
        抛出最后一次的异常（点击异常或等待超时）。
        """
        last_error = None
        for _ in range(max(1, attempts)):
            try:
                self.click(locator, timeout)
            except (TimeoutException, WebDriverException) as exc:
                last_error = exc
                continue
            try:
                if waiter():
                    return
            except (TimeoutException, WebDriverException) as exc:
                last_error = exc
        if last_error is not None:
            raise last_error
        url, title = self._page_info()
        raise WaitTimeoutError(
            locator, self.timeout if timeout is None else timeout, "点击生效", url, title
        )

    def type_text(self, locator, text, clear=True, timeout=None):
        """等待元素可点击后输入文本，返回 None。

        clear=True 先清空再输入。对 React/Vue 受控组件 clear() 可能不触发
        组件状态更新，若出现清不掉的情况改用全选删除后输入。
        最坏耗时 stale_retries * timeout。
        """

        def action(element):
            if clear:
                element.clear()
            element.send_keys(text)

        return self._act(locator, self.clickable, action, timeout)

    def text_of(self, locator, timeout=None):
        """等待元素可见后返回它的 .text。

        注意 .text 只返回可见文本，元素隐藏时返回空串。需要隐藏元素的
        文本时改用 present() 拿到元素，或用 attr_of(locator, "textContent")。
        """
        return self._act(locator, self.visible, lambda element: element.text, timeout)

    def attr_of(self, locator, name, timeout=None):
        """等待元素存在于 DOM 后返回指定属性值，属性不存在时返回 None。"""
        return self._act(
            locator,
            self.present,
            lambda element: element.get_attribute(name),
            timeout,
        )
