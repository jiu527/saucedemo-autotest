from selenium.common.exceptions import WebDriverException

from pages.base_page import BasePage
from utils.wait_utils import WaitTimeoutError


class CartPage(BasePage):
    CONTAINER = ("id", "cart_contents_container")
    CART_ITEM = ("css selector", ".cart_item")
    ITEM_NAME = ("css selector", ".cart_item .inventory_item_name")
    ITEM_PRICE = ("css selector", ".cart_item .inventory_item_price")
    CHECKOUT_BTN = ("id", "checkout")

    URL = "https://www.saucedemo.com/cart.html"

    def open(self):
        super().open(self.URL)

    def get_item_names(self):
        """返回购物车里所有商品名；空购物车返回 []。

        空购物车没有任何 `.cart_item`，而 `present_all` 的语义是「等到至少
        一个出现」——空列表会被当成条件不满足而一直轮询到超时。所以这里先
        等始终存在的容器出现，再用 `elements_now` 取当前列表（允许为空）。
        """
        self.wait.present(self.CONTAINER)
        return [element.text for element in self.wait.elements_now(self.ITEM_NAME)]

    def get_prices(self):
        """返回购物车里所有商品标价（float，不含 $）。"""
        items = self.wait.all_visible(self.ITEM_PRICE)
        return [float(el.text.removeprefix("$")) for el in items]

    def remove_item(self, name):
        slug = name.lower().replace(" ", "-")
        self.wait.click(("css selector", f"[data-test='remove-{slug}']"))
        # 等这一行真正消失
        row = ("xpath",
            f"//div[contains(@class,'cart_item')]"
            f"[.//div[contains(@class,'inventory_item_name') "
            f"and normalize-space()='{name}']]")
        self.wait.invisible(row)

    def checkout(self):
        """点击 Checkout，跳转到 checkout-step-one 页。

        与 InventoryPage.add_to_cart 同理：以 URL 变化为成功判据，
        点一次没跳转就再点（CI 上偶发，事件监听未就绪或布局漂移时点击无效）。
        """
        last_error = None
        for attempt in range(1, 4):
            try:
                element = self.wait.clickable(self.CHECKOUT_BTN)
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center'});", element
                )
                if attempt == 2:
                    self.driver.execute_script("arguments[0].click();", element)
                else:
                    element.click()
            except WebDriverException as exc:
                last_error = exc
                continue

            try:
                self.wait.until_url_contains("checkout-step-one.html", timeout=4)
                return
            except WaitTimeoutError as exc:
                last_error = exc
                continue

        raise last_error
