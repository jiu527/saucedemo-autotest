"""wait_utils 的自测（第 1 层基础等待 + 第 2 层交互）。

用本地 HTML 制造"元素延迟出现 / 延迟消失 / 元素被替换"，不依赖外网，
也不受代理影响。其中两条是关键：

- test_visible_actually_waits 断言等待确实在轮询，实现退化成"查一次就返回"会失败
- test_click_retries_after_stale 确定性地触发 stale，重试逻辑失效会失败

标记：wait = 第 1 层基础等待；action = 第 2 层交互。选择方式见 pytest.ini。
"""

import time
from pathlib import Path

import pytest
from selenium.webdriver.common.by import By

from utils.wait_utils import WaitTimeoutError

PAGE = (Path(__file__).parent / "data" / "wait_probe.html").as_uri()


# --- 第 1 层：基础等待 ---


@pytest.mark.wait
def test_present(driver, wait):
    driver.get(PAGE)
    assert wait.present((By.ID, "always")).text == "always here"


@pytest.mark.wait
def test_visible_actually_waits(driver, wait):
    driver.get(PAGE)
    start = time.time()
    element = wait.visible((By.ID, "late"))
    elapsed = time.time() - start
    assert element.text == "late arrival"
    assert elapsed >= 0.8, f"元素 900ms 后才出现，但只等了 {elapsed:.2f}s，说明没有真正轮询"


@pytest.mark.wait
def test_clickable(driver, wait):
    driver.get(PAGE)
    assert wait.clickable((By.ID, "always")).tag_name == "div"


@pytest.mark.wait
def test_invisible(driver, wait):
    driver.get(PAGE)
    assert wait.invisible((By.ID, "gone")) is True


@pytest.mark.wait
def test_all_visible(driver, wait):
    driver.get(PAGE)
    assert len(wait.all_visible((By.CSS_SELECTOR, ".item"))) == 3


@pytest.mark.wait
def test_present_all(driver, wait):
    driver.get(PAGE)
    assert len(wait.present_all((By.CSS_SELECTOR, ".item"))) == 3


@pytest.mark.wait
def test_timeout_raises_with_context(driver, wait):
    driver.get(PAGE)
    with pytest.raises(WaitTimeoutError) as excinfo:
        wait.visible((By.ID, "never-exists"), timeout=1)
    message = str(excinfo.value)
    assert "1s" in message, message
    assert "never-exists" in message, message
    assert "wait_probe.html" in message, message
    assert "wait probe" in message, message


# --- 第 2 层：交互 ---


@pytest.mark.action
def test_click(driver, wait):
    driver.get(PAGE)
    assert wait.click((By.ID, "btn")) is None
    assert wait.text_of((By.ID, "click-result")) == "clicked"


@pytest.mark.action
def test_type_text_clears_by_default(driver, wait):
    driver.get(PAGE)
    wait.type_text((By.ID, "name-input"), "new value")
    assert wait.attr_of((By.ID, "name-input"), "value") == "new value"


@pytest.mark.action
def test_type_text_without_clear_keeps_existing(driver, wait):
    driver.get(PAGE)
    wait.type_text((By.ID, "name-input"), "!", clear=False)
    value = wait.attr_of((By.ID, "name-input"), "value")
    assert "prefilled" in value and value != "prefilled"


@pytest.mark.action
def test_text_of_visible_and_hidden(driver, wait):
    driver.get(PAGE)
    assert wait.text_of((By.ID, "always")) == "always here"
    # .text 只返回可见文本：present 能拿到隐藏元素，但它的 .text 是空串
    assert wait.present((By.ID, "hidden")).text == ""
    assert wait.attr_of((By.ID, "hidden"), "textContent") == "hidden text"


@pytest.mark.action
def test_attr_of_returns_value_or_none(driver, wait):
    driver.get(PAGE)
    assert wait.attr_of((By.ID, "with-attr"), "data-state") == "idle"
    assert wait.attr_of((By.ID, "with-attr"), "data-missing") is None


@pytest.mark.action
def test_click_retries_after_stale(driver, wait, monkeypatch):
    driver.get(PAGE)

    # 先拿到元素，再把它从 DOM 里换掉，让这个引用失效
    stale = wait.clickable((By.ID, "btn"))
    driver.execute_script(
        "var b = document.getElementById('btn');"
        "b.parentNode.replaceChild(b.cloneNode(true), b);"
    )

    # 只让第一次等待返回那个已失效的元素，验证 _act 会重新定位
    calls = {"n": 0}
    real_clickable = wait.clickable

    def first_call_returns_stale(locator, timeout=None):
        calls["n"] += 1
        return stale if calls["n"] == 1 else real_clickable(locator, timeout)

    monkeypatch.setattr(wait, "clickable", first_call_returns_stale)

    wait.click((By.ID, "btn"))

    assert calls["n"] == 2, f"stale 后没有重试，clickable 只被调用 {calls['n']} 次"
    assert wait.text_of((By.ID, "click-result")) == "clicked"
