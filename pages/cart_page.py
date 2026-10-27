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
        # 要等的那一行（用于判断「点了之后真的消失了」）
        row = ("xpath",
            f"//div[contains(@class,'cart_item')]"
            f"[.//div[contains(@class,'inventory_item_name') "
            f"and normalize-space()='{name}']]")
        # 以「这一行真的消失」为判据重试点击（CI 上偶发点击落空）
        self.wait.click_until(
            ("css selector", f"[data-test='remove-{slug}']"),
            lambda: self.wait.invisible(row, timeout=4),
        )

    def checkout(self):
        """点击 Checkout，跳转到 checkout-step-one 页。

        以 URL 变化为判据重试（CI 上偶发点击落空，详见 WaitUtils.click_until）。
        """
        self.wait.click_until(
            self.CHECKOUT_BTN,
            lambda: self.wait.until_url_contains("checkout-step-one.html", timeout=4),
        )

