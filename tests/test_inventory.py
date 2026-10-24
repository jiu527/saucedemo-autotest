import allure
import pytest

from pages.inventory_page import InventoryPage
from pages.login_page import LoginPage


@pytest.fixture
def inventory_page(driver):
    """已登录并进入库存页的页面对象，两条用例共享同一前置。"""
    page = LoginPage(driver)
    page.open()
    page.login("standard_user", "secret_sauce")
    return InventoryPage(driver)


@allure.epic('电商API自动化测试')
@allure.feature('库存页')
@allure.story('购物车')
@allure.title('购物车角标与已添加商品数一致')
@pytest.mark.inventory
def test_add_to_cart_badge(inventory_page):
    items = ["Sauce Labs Backpack", "Sauce Labs Bike Light"]
    for name in items:
        inventory_page.add_to_cart(name)
    assert inventory_page.get_cart_count() == len(items)


@allure.epic('电商API自动化测试')
@allure.feature('库存页')
@allure.story('排序')
@allure.title('按价格升序排列')
@pytest.mark.inventory
def test_sort_by_price_low_high(inventory_page):
    inventory_page.sort_by_price_low_high()
    prices = inventory_page.get_prices()
    assert prices == sorted(prices)
