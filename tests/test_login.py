import pytest
import yaml
import allure
from pages.login_page import LoginPage
from pages.inventory_page import InventoryPage

def load_login_data():
    with open("data/login_data.yaml") as f:
        return yaml.safe_load(f)

@allure.epic('电商API自动化测试')
@allure.feature('登录功能测试')
@allure.story('登录成功')
@allure.title('登录成功测试')
@pytest.mark.login
def test_login_success(driver):
    page = LoginPage(driver)
    page.open()
    page.login("standard_user", "secret_sauce")
    assert InventoryPage(driver).is_loaded()

@allure.epic('电商API自动化测试')
@allure.feature('登录功能测试')
@allure.story('登录失败')
@allure.title('登录失败测试')
@pytest.mark.login
@pytest.mark.parametrize("data", load_login_data(), ids=lambda d: d["case"])
def test_login_failure(driver, data):
    page = LoginPage(driver)
    page.open()
    # 预期失败：只提交、不等跳转，否则会一直等 inventory.html 直到超时
    page.submit_credentials(data["username"], data["password"])
    assert data["expected"] in page.get_error_message()
    assert "inventory.html" not in driver.current_url