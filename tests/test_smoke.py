import pytest
import allure

from pages.login_page import LoginPage


@allure.epic('电商API自动化测试')
@allure.feature('冒烟测试')
@allure.story('冒烟测试')
@allure.title('站点冒烟测试')
@pytest.mark.smoke
def test_smoke(driver, wait):
    driver.get("https://www.saucedemo.com/")
    assert "Swag Labs" in driver.title
    wait.visible(LoginPage.USERNAME)
