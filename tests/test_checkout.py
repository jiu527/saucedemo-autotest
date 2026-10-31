import allure
import pytest

from data.constants import ITEM_A, ITEM_B
from pages.cart_page import CartPage
from pages.checkout_page import CheckoutPage


@pytest.fixture
def checkout_page(inventory_page):
    """两件商品已在购物车，并已走到结账第一步（填写信息页）。

    「登录进库存页」复用 conftest 的 inventory_page；本文件只保留自己的
    业务前置（加哪两件、走到哪一步）。
    """
    for name in (ITEM_A, ITEM_B):
        inventory_page.add_to_cart(name)
    cart = CartPage(inventory_page.driver)
    cart.open()
    cart.checkout()
    return CheckoutPage(inventory_page.driver)


@allure.epic('电商API自动化测试')
@allure.feature('结账')
@allure.story('Overview')
@allure.title('Overview 商品列表与实际添加的商品一致')
@pytest.mark.checkout
def test_overview_lists_added_items(checkout_page):
    checkout_page.fill_info("Test", "User", "10000")
    checkout_page.continue_to_overview()
    assert sorted(checkout_page.get_item_names()) == sorted([ITEM_A, ITEM_B])


@allure.epic('电商API自动化测试')
@allure.feature('结账')
@allure.story('完成下单')
@allure.title('Finish 后跳转订单确认页')
@pytest.mark.checkout
def test_checkout_complete_order(checkout_page, driver):
    checkout_page.fill_info("Test", "User", "10000")
    checkout_page.continue_to_overview()
    checkout_page.finish()
    assert "checkout-complete" in driver.current_url
    assert checkout_page.get_complete_header() == "Thank you for your order!"
