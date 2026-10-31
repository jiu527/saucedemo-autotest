"""跨测试文件共享的测试数据（常量）。

只放「被多个测试文件引用」的稳定值：凭据、商品名。
登录失败场景的用例数据在 data/login_data.yaml（参数化用，需要多组）。
"""

# saucedemo 内置的标准账号（只读演示站，非真实凭据）
STANDARD_USER = "standard_user"
STANDARD_PASSWORD = "secret_sauce"

# 购物车/结账用例用的两件商品（价格 29.99 / 9.99，用于总价断言）
ITEM_A = "Sauce Labs Backpack"
ITEM_B = "Sauce Labs Bike Light"
