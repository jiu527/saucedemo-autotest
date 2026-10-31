import allure
import pytest

from data.constants import STANDARD_PASSWORD, STANDARD_USER
from pages.inventory_page import InventoryPage
from pages.login_page import LoginPage
from utils.driver_factory import create_driver
from utils.wait_utils import WaitUtils


@pytest.fixture
def driver():
    driver = create_driver()
    yield driver
    driver.quit()


@pytest.fixture
def wait(driver):
    return WaitUtils(driver)


@pytest.fixture
def inventory_page(driver):
    """已用标准用户登录并进入库存页。

    这是跨模块共享的前置（库存/购物车/结账三个文件的起点），所以放在
    conftest；而「加哪两件商品」「走到结账第一步」这类业务前置留在各自的
    测试文件里——它们只服务单文件，混进 conftest 会让依赖关系变模糊。
    """
    page = LoginPage(driver)
    page.open()
    page.login(STANDARD_USER, STANDARD_PASSWORD)
    return InventoryPage(driver)


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    if rep.when == "call" and rep.failed:
        driver = item.funcargs.get("driver")
        if driver:
            screenshot = driver.get_screenshot_as_png()
            allure.attach(
                screenshot,
                name="失败截图",
                attachment_type=allure.attachment_type.PNG
            )
