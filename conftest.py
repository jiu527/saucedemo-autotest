import pytest
import allure
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