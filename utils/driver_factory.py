import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def create_driver():
    options = Options()
    # 系统代理只在下载 chromedriver 时用得上；被测站点走代理反而慢得多
    # （saucedemo.com 实测：直连 1.1s，走代理 16.7s，最差超过 120s 直接超时）
    options.add_argument("--proxy-server=direct://")
    if os.getenv("CI"):
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
    else:
        # saucedemo.com 托管在 GitHub Pages，其 IPv4（185.199.x.x）在国内时断时续，
        # IPv6（2606:50c0::）稳定。钉死 IPv6 避免 Chrome 在坏地址间轮询——
        # 每踩中一个被丢的连接要等 ~21s TCP 超时，实测 smoke 曾因此慢到 92s。
        # 注意 IPv6 字面量必须带方括号，否则规则静默失效报 ERR_NAME_NOT_RESOLVED。
        # CI（GitHub Actions）没有 IPv6 出口，钉了会全部连不上，所以仅本地生效。
        options.add_argument(
            "--host-resolver-rules=MAP www.saucedemo.com [2606:50c0:8000::153]"
        )
    driver = webdriver.Chrome(options=options)
    if not os.getenv("CI"):
        driver.maximize_window()
    driver.implicitly_wait(0)  # 关闭隐式等待，后续只用显式等待
    return driver