from utils.wait_utils import WaitTimeoutError

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
        """返回购物车里所有商品名；空购物车返回 []。

        空购物车没有任何 .cart_item，而 present_all 要等到至少一个元素
        出现才返回（空列表在 until() 里被当成"还没等到"，会一直轮询），
        所以用 1 秒短超时探测：等不到就按空购物车处理。
        """
        try:
            items = self.wait.present_all(self.ITEM_NAME, timeout=1)
        except WaitTimeoutError:
            return []
        return [el.text for el in items]

    def get_prices(self):
        """返回购物车里所有商品标价（float，不含 $）。"""
        items = self.wait.all_visible(self.ITEM_PRICE)
        return [float(el.text.removeprefix("$")) for el in items]

    def remove_item(self, name):
        """按商品名移除，slug 转换规则与 InventoryPage.add_to_cart 一致。"""
        slug = name.lower().replace(" ", "-")
        self.click(("css selector", f"[data-test='remove-{slug}']"))

    def checkout(self):
        """点击 Checkout，跳转到 checkout-step-one 页。"""
        self.click(self.CHECKOUT_BTN)
