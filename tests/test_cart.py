import allure
import pytest

from pages.cart_page import CartPage
from pages.checkout_page import CheckoutPage
from pages.inventory_page import InventoryPage
from pages.login_page import LoginPage

ITEM_A = "Sauce Labs Backpack"    # 29.99
ITEM_B = "Sauce Labs Bike Light"  # 9.99


@pytest.fixture
def cart_page(driver):
    page = LoginPage(driver)
    page.open()
    page.login("standard_user", "secret_sauce")
    inventory = InventoryPage(driver)
    inventory.add_to_cart(ITEM_A)
    inventory.add_to_cart(ITEM_B)
    cart = CartPage(driver)
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
