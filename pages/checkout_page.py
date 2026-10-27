from pages.base_page import BasePage

class CheckoutPage(BasePage):
    INFO_CONTAINER = ("id", "checkout_info_container")        # 第一步：填写信息
    SUMMARY_CONTAINER = ("id", "checkout_summary_container")  # 第二步：Overview
    TITLE = ("css selector", ".title")
    FIRST_NAME = ("id", "first-name")
    LAST_NAME = ("id", "last-name")
    POSTAL_CODE = ("id", "postal-code")
    CONTINUE_BTN = ("id", "continue")
    SUBTOTAL = ("css selector", "[data-test='subtotal-label']")
    ITEM_NAME = ("css selector", ".cart_item .inventory_item_name")
    FINISH_BTN = ("id", "finish")
    COMPLETE_HEADER = ("css selector", ".complete-header")

    URL = "https://www.saucedemo.com/checkout-step-one.html"

    def open(self):
        super().open(self.URL)

    def fill_info(self, first, last, zip):
        """填写收货信息"""
        self.type(self.FIRST_NAME, first)
        self.type(self.LAST_NAME, last)
        self.type(self.POSTAL_CODE, zip)

    def continue_to_overview(self):
        """提交第一步信息，进入 Checkout: Overview（第二步）。

        用 `click_until` 以 URL 变化为判据重试：CI 上偶发「点了 Continue 但
        页面没跳转」（点击落空），此时如果只是死等 URL 就会白等 10 秒。
        """
        self.wait.click_until(
            self.CONTINUE_BTN,
            lambda: self.wait.until_url_contains("checkout-step-two.html", timeout=4),
        )

    def get_subtotal(self):
        """返回页面展示的 Item total"""
        return float(self.get_text(self.SUBTOTAL).split("$")[-1])

    def get_item_names(self):
        """返回 Overview 页商品列表的商品名（与购物车共用 .cart_item 结构）。"""
        items = self.wait.all_visible(self.ITEM_NAME)
        return [el.text for el in items]

    def finish(self):
        """在 Overview 页点击 Finish，跳转完成页。"""
        self.wait.click_until(
            self.FINISH_BTN,
            lambda: self.wait.until_url_contains("checkout-complete", timeout=4),
        )

    def get_complete_header(self):
        return self.get_text(self.COMPLETE_HEADER)
