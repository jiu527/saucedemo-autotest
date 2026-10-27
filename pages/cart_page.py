from selenium.common.exceptions import WebDriverException
from utils.wait_utils import WaitTimeoutError
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from pages.base_page import BasePage

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
        
        self.wait.present(self.CONTAINER)          # #cart_contents_container 始终存在
        items = self.driver.find_elements(*self.ITEM_NAME)
        return [el.text for el in items]
        # """返回购物车里所有商品名；空购物车返回 []。
    
        # 空购物车没有任何 .cart_item，而 present_all 要等到至少一个元素
        # 出现才返回（空列表在 until() 里被当成"还没等到"，会一直轮询），
        # 所以用 1 秒短超时探测：等不到就按空购物车处理。
        # """
        # try:
        #     items = self.wait.present_all(self.ITEM_NAME, timeout=1)
        # except WaitTimeoutError:
        #     return []
        # return [el.text for el in items]

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
