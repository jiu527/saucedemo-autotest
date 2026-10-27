from selenium.webdriver.support.ui import Select

from pages.base_page import BasePage
from utils.wait_utils import WaitTimeoutError


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
        """把商品加入购物车，返回当前购物车角标数字。

        以「remove 按钮出现」为判据重试点击（CI 上偶发点击落空，详见
        WaitUtils.click_until）。先查一次 remove 按钮，已加购就直接返回，
        避免重复点击把同一商品加两次。
        """
        slug = name.lower().replace(" ", "-")
        add = ("css selector", f"[data-test='add-to-cart-{slug}']")
        remove = ("css selector", f"[data-test='remove-{slug}']")

        try:
            self.wait.visible(remove, timeout=1)
        except WaitTimeoutError:
            self.wait.click_until(add, lambda: self.wait.visible(remove, timeout=4))
        return self.get_cart_count()

    def sort_by_price_low_high(self):
        """在下拉框中选中 Price (low to high)。"""
        select = Select(self.wait.clickable(self.SORT_DROPDOWN))
        select.select_by_value("lohi")

    def get_prices(self):
        """等待商品列表渲染后返回所有标价"""
        items = self.wait.all_visible(self.ITEM_PRICE)
        return [float(el.text.removeprefix("$")) for el in items]