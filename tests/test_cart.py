import allure
import pytest

from data.constants import ITEM_A, ITEM_B
from pages.cart_page import CartPage
from pages.checkout_page import CheckoutPage


@pytest.fixture
def cart_page(inventory_page):
    """两件商品已在购物车里。

    fixture 只保留本文件自己的业务前置（加哪两件、进购物车）；
    「登录并进入库存页」来自 conftest 的 inventory_page。
    """
    inventory_page.add_to_cart(ITEM_A)
    inventory_page.add_to_cart(ITEM_B)
    cart = CartPage(inventory_page.driver)
    cart.open()
    return cart


@allure.epic('电商API自动化测试')
@allure.feature('购物车')
@allure.story('总价')
@allure.title('多商品总价与页面展示的 Item total 一致')
@pytest.mark.cart
def test_cart_total(cart_page, driver):
    prices = cart_page.get_prices()
    cart_page.checkout()
    checkout = CheckoutPage(driver)
    checkout.fill_info("Test", "User", "10000")
    checkout.continue_to_overview()
    assert sum(prices) == pytest.approx(checkout.get_subtotal())


@allure.epic('电商API自动化测试')
@allure.feature('购物车')
@allure.story('移除商品')
@allure.title('移除商品后列表为空')
@pytest.mark.cart
def test_remove_item_empties_cart(cart_page):
    cart_page.remove_item(ITEM_A)
    assert cart_page.get_item_names() == [ITEM_B]
    cart_page.remove_item(ITEM_B)
    assert cart_page.get_item_names() == []
