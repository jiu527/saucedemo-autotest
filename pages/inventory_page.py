from selenium.common.exceptions import WebDriverException
from selenium.webdriver.support.ui import Select

from pages.base_page import BasePage
from utils.wait_utils import WaitTimeoutError

# 点击后等「效果出现」的超时（秒）；超时说明这一次点击没生效
_EFFECT_TIMEOUT = 4
_CLICK_ATTEMPTS = 3


class InventoryPage(BasePage):
    CONTAINER = ("id", "inventory_container")
    TITLE = ("css selector", ".title")
    CART_BADGE = ("css selector", ".shopping_cart_badge")
    SORT_DROPDOWN = ("css selector", "select.product_sort_container")
    ITEM_PRICE = ("css selector", ".inventory_item_price")

    def open(self):
        super().open("https://www.saucedemo.com/inventory.html")

    def is_loaded(self):
        try:
            self.wait.visible(self.CONTAINER, timeout=10)
            return True
        except Exception:
            return False

    def get_cart_count(self):
        """返回当前购物车角标数字（购物车为空时角标不存在，会等到超时）。"""
        return int(self.get_text(self.CART_BADGE))

    def add_to_cart(self, name):
        """把商品加入购物车，以「remove 按钮出现」为成功判据。

        CI 上偶发的真实故障（出现过多次）：`add-to-cart-*` 按钮明明可见可点击，
        点下去却什么也没发生，于是等 `remove-*` 一直等到 10s 超时。常见原因是
        商品图片加载导致布局漂移、原生点击落在了旧坐标上，或 React 事件监听
        尚未挂载——`element_to_be_clickable` 只看「可见+启用」，判断不出这些。

        所以这里以效果为判据，并按「滚动到可视区 → 原生点击 → JS 点击」逐次加强：
        第 1 次原生点击，第 2 次换成 JS 点击（绕过坐标计算），第 3 次再原生。
        """
        slug = name.lower().replace(" ", "-")
        add = ("css selector", f"[data-test='add-to-cart-{slug}']")
        remove = ("css selector", f"[data-test='remove-{slug}']")

        last_error = None
        for attempt in range(1, _CLICK_ATTEMPTS + 1):
            try:
                self.wait.visible(remove, timeout=1)
                return self.get_cart_count() 
            except WaitTimeoutError:
                pass

            try:
                element = self.wait.clickable(add)
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center'});", element
                )
                if attempt == 2:
                    self.driver.execute_script("arguments[0].click();", element)
                else:
                    element.click()
            except (WebDriverException, WaitTimeoutError) as exc:
                last_error = exc
                continue

            try:
                self.wait.visible(remove, timeout=_EFFECT_TIMEOUT)
                return self.get_cart_count()
            except WaitTimeoutError as exc:
                last_error = exc
                continue

        raise last_error

    def sort_by_price_low_high(self):
        """在下拉框中选中 Price (low to high)。"""
        select = Select(self.wait.clickable(self.SORT_DROPDOWN))
        select.select_by_value("lohi")

    def get_prices(self):
        """等待商品列表渲染后返回所有标价"""
        items = self.wait.all_visible(self.ITEM_PRICE)
        return [float(el.text.removeprefix("$")) for el in items]