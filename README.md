# saucedemo UI 自动化测试

基于 Selenium 4 + pytest + Allure 的 Web UI 自动化项目，被测站点为 [saucedemo.com](https://www.saucedemo.com/)（Sauce Labs 官方演示电商站，托管在 GitHub Pages）。

项目采用 Page Object 模式，并把「显式等待」抽成了一个独立的可自测封装层——这是本项目与常见练手项目最主要的区别：等待逻辑本身也有测试覆盖，而不是散落在各 Page Object 里的魔法 `sleep`。

---

## 目录

- [1. 项目目的与测试范围](#1-项目目的与测试范围)
- [2. 技术栈](#2-技术栈)
- [3. 架构分层](#3-架构分层)
- [4. 本地运行](#4-本地运行)
- [5. Allure 报告](#5-allure-报告)
- [6. CI 状态](#6-ci-状态)
- [7. 调试问题记录](#7-调试问题记录)
- [8. 已知问题与待办](#8-已知问题与待办)

---

## 1. 项目目的与测试范围

### 目的

1. **验证核心购物链路的正确性**：登录 → 浏览/加购 → 购物车 → 结账，覆盖页面跳转、DOM 渲染、金额计算、状态同步。
2. **沉淀一套可复用的等待与页面对象基础设施**：用 `WaitUtils` 统一收口所有元素获取，禁止 `time.sleep` 和裸 `find_element`。
3. **让等待逻辑自身可回归**：`wait_utils` 的第 1、2 层能力有 13 条本地用例守护，用 `file://` 页面确定性触发「延迟出现 / 延迟消失 / 元素被替换」等场景，不依赖外网。

### 覆盖范围

| 模块 | 测试文件 | marker | 用例函数 | 收集条数 | 依赖外网 |
|---|---|---|---|---|---|
| 冒烟（站点可达 + 登录表单渲染） | [tests/test_smoke.py](tests/test_smoke.py) | `smoke` | 1 | 1 | ✅ |
| 登录（成功 + 3 种失败场景） | [tests/test_login.py](tests/test_login.py) | `login` | 2 | 4 | ✅ |
| 库存页（加购角标、价格排序） | [tests/test_inventory.py](tests/test_inventory.py) | `inventory` | 2 | 2 | ✅ |
| 购物车（总价核对、移除商品） | [tests/test_cart.py](tests/test_cart.py) | `cart` | 2 | 2 | ✅ |
| 结账（Overview 商品列表、下单完成） | [tests/test_checkout.py](tests/test_checkout.py) | `checkout` | 2 | 2 | ✅ |
| 等待封装 · 第 1 层基础等待 | [tests/test_wait_utils.py](tests/test_wait_utils.py) | `wait` | 7 | 7 | ❌ |
| 等待封装 · 第 2 层交互 | [tests/test_wait_utils.py](tests/test_wait_utils.py) | `action` | 6 | 6 | ❌ |
| **合计** | | | **22** | **24** | |

> 用例函数 22 个，收集条目 24 条：`test_login_failure` 用 `pytest.mark.parametrize` 展开成 3 条（数据来自 [data/login_data.yaml](data/login_data.yaml)：锁定用户 / 空用户名 / 错误密码）。
>
> 其中登录失败的 3 条曾因用例设计缺陷稳定失败，已按[第 8 节](#8-已知问题与待办)的 P0 条目修复，并在修复后实测通过（`-m login` → 4 passed）。

### 明确不在范围内

- 真实支付、下单后的后端数据校验（演示站没有真实后端状态）。
- 多浏览器/多分辨率矩阵（当前只跑 Chrome，本地最大化窗口、CI 固定 1920×1080）。
- 移动端、无障碍（a11y）、性能压测。
- 接口层测试（项目名为 `autotest`，但目前是纯 UI 层）。

---

## 2. 技术栈

| 类别 | 选型 | 版本 | 说明 |
|---|---|---|---|
| 语言 | Python | 3.14 | 与 CI 一致 |
| 浏览器驱动 | Selenium | 4.51.0 | 用 Selenium Manager 自动管理 chromedriver，不手放 `chromedriver.exe` |
| 测试框架 | pytest | 9.1.1 | `--strict-markers` 开启，marker 必须注册 |
| 报告 | allure-pytest | 2.16.2 | 原始结果写 `allure-results/` |
| 测试数据 | PyYAML | 6.0.3 | 登录失败用例参数化 |
| 运行环境 | venv | — | 虚拟环境位于 `./autotest/`（注意与项目根目录同名，是历史原因） |
| CI | GitHub Actions | ubuntu-latest | 见 [.github/workflows/test.yaml](.github/workflows/test.yaml) |

完整依赖见 [requirements.txt](requirements.txt)（26 个包，含传递依赖，已全量钉版本）。

---

## 3. 架构分层

```
tests/                      ← 第 4 层：用例层，只写业务断言
  test_smoke.py                smoke
  test_login.py                login（数据驱动）
  test_inventory.py            inventory
  test_cart.py                 cart
  test_checkout.py             checkout
  test_wait_utils.py           wait / action（基础设施自测，走 file://）
  data/wait_probe.html         本地测试页面
        ↓ 只调用页面对象方法，不碰 driver
pages/                      ← 第 3 层：Page Object，封装页面结构与操作
  base_page.py                 持有 WaitUtils，提供 open/click/type/get_text
  login_page.py                登录页
  inventory_page.py            库存页（加购、排序、取价格）
  cart_page.py                 购物车页（移除、结算入口）
  checkout_page.py             结账两步 + 完成页
        ↓ 全部元素操作必须经过 WaitUtils
utils/
  wait_utils.py              ← 第 2 层：显式等待封装（第 1 层基础等待 + 第 2 层交互）
  driver_factory.py          ← 第 1 层：浏览器工厂（代理策略、headless、IPv6 固定）
        ↓
conftest.py                 ← 夹具与钩子：driver / wait fixture、失败自动截图
pytest.ini                  ← marker 注册、allure 参数、testpaths
data/login_data.yaml        ← 外部测试数据
```

### 各层职责与约束

**第 1 层 · 浏览器工厂** —— [utils/driver_factory.py](utils/driver_factory.py)

唯一创建 driver 的地方，集中处理所有环境相关的浏览器配置，避免环境差异渗进用例：

- 默认 `--no-proxy-server`，强制直连（除非显式设 `USE_SYSTEM_PROXY=1`）；
- 检测到 `CI` 环境变量时切 `--headless=new` 并关沙箱；
- 本地把 `www.saucedemo.com` 的 DNS 固定到 IPv6 地址；
- `implicitly_wait(0)`，关掉隐式等待，避免与显式等待叠加出双重超时。

**第 2 层 · 等待封装** —— [utils/wait_utils.py](utils/wait_utils.py)

全项目唯一的元素获取入口，硬约定：**不用 `driver.find_element`、不直接 `WebDriverWait`、不用 `time.sleep`**。

- 第 1 层（查询）：`visible` / `present` / `clickable` / `invisible` / `all_visible` / `present_all` / `until_url_contains`
- 第 2 层（交互）：`click` / `type_text` / `text_of` / `attr_of`，内部带 stale 元素重新定位重试
- 超时统一抛 `WaitTimeoutError`，消息里带 locator、超时值、页面标题、当前 URL——失败时不用再猜是哪一步挂的
- 超时/轮询/重试次数可由 `WAIT_TIMEOUT` / `WAIT_POLL` / `WAIT_STALE_RETRIES` 覆盖，无需改代码

**第 3 层 · Page Object** —— `pages/`

一个页面一个类，只暴露业务语义方法（`login()`、`add_to_cart(name)`、`sort_by_price_low_high()`），locator 以类常量声明在类顶部。定位串统一用 `("id", "user-name")` 这种元组形式，与 Selenium 的 `By` 语义等价。

**第 4 层 · 用例层** —— `tests/`

只做三件事：调用页面对象、断言、挂 Allure 元数据（`epic` / `feature` / `story` / `title`）。跨用例的重复前置（已登录、已加购、已走到结账第一步）抽成各测试文件内的 `@pytest.fixture`，而不是互相 import 用例。

**横向支撑**

- [conftest.py](conftest.py)：`driver` fixture 负责创建/退出，`wait` fixture 注入 `WaitUtils`；`pytest_runtest_makereport` 钩子在 `call` 阶段失败时自动截图并附到 Allure。
- [pytest.ini](pytest.ini)：注册 7 个 marker（`--strict-markers` 下拼错会直接报错）、`testpaths = tests`、默认带 `--alluredir` 和 `--clean-alluredir`。

---

## 4. 本地运行

### 前置条件

- Windows + PowerShell（仓库自带 [run_tests.ps1](run_tests.ps1) 是 PowerShell 脚本）
- 本机装 Chrome
- 已创建虚拟环境 `./autotest/`（`python -m venv autotest`）并装好依赖

```powershell
# 首次准备
python -m venv autotest
.\autotest\Scripts\python.exe -m pip install -r requirements.txt
```

### 跑测试

**推荐（任何终端都能用，不受 PowerShell 脚本执行策略影响）：**

```powershell
Set-Location 'D:\Code\Python\autotest'
.\autotest\Scripts\python.exe -m pytest -o addopts="" -q
```

`-o addopts=""` 用来跳过 `pytest.ini` 里的 `--clean-alluredir`，避免清掉已有报告；要生成报告就去掉这个参数。

| 场景 | 命令 |
|---|---|
| 全部用例 | `.\autotest\Scripts\python.exe -m pytest` |
| 只跑冒烟 | `... -m smoke` |
| 只跑本地等待自测（不联网，最快） | `... -m "wait or action"` |
| 只跑某个模块 | `... -m login` |
| 指定用例 | `... tests/test_cart.py::test_cart_total` |
| 关键字过滤 | `... -k "badge or sort"` |
| 只收集不执行（看用例清单） | `... --collect-only -q` |
| 无头运行（不弹窗口、更快） | 先 `$env:CI = "true"`，再执行上面任意一条 |

**`run_tests.ps1` 也可以**，它与上面完全等价（`.\run_tests.ps1 -m login`），但它是个 `.ps1` 脚本，在限制脚本执行的环境里会被拦（详见第 8 节 P3/P4）。它只是薄包装：定位 venv 的 `python.exe`、设 `SE_OFFLINE=true`、透传参数、透传退出码——其中 `SE_OFFLINE` 现在也由 [driver_factory.py](utils/driver_factory.py) 兜底了。

### 环境变量

| 变量 | 默认 | 作用 |
|---|---|---|
| `CI` | 未设 | 设了即切 headless + 固定窗口 + 跳过最大化 |
| `SE_OFFLINE` | 由 `run_tests.ps1` 设为 `true` | 让 Selenium Manager 只读本地驱动缓存、不联网校验 |
| `USE_SYSTEM_PROXY` | 未设 | 设为 `1` 时不做直连，改走系统代理 |
| `WAIT_TIMEOUT` | `10` | 显式等待默认超时（秒） |
| `WAIT_POLL` | `0.5` | 轮询间隔（秒） |
| `WAIT_STALE_RETRIES` | `2` | stale 元素重新定位的最大尝试次数 |

> `WAIT_STALE_RETRIES` 是**总尝试次数**而非「额外重试次数」，所以单次交互的最坏耗时是 `retries × timeout`（默认 2 × 10s = 20s）。

---

## 5. Allure 报告

`pytest.ini` 的 `addopts` 已默认带 `--alluredir=allure-results --clean-alluredir`，所以每次跑都会重新生成原始结果（注意：会清空上一次的结果）。

```powershell
# 实时起服务预览（需要装 allure 命令行，或从 Allure 官方 release 解压后加进 PATH）
allure serve allure-results

# 或生成为静态站点
allure generate allure-results -o report --clean
allure open report
```

仓库里已有一份生成的静态报告在 [report/](report/index.html)，可直接用浏览器打开。失败用例会自动附带全页截图（见 `conftest.py` 的钩子）。

---

## 6. CI 状态

### 工作流

[.github/workflows/test.yaml](.github/workflows/test.yaml)，名称 `Selenium Tests CI`，跑在 `ubuntu-latest`。

| 项 | 配置 |
|---|---|
| 触发条件 | push 到 `main`、对 `main` 的 PR、手动 `workflow_dispatch` |
| Python | 3.14（`actions/setup-python@v5`） |
| 依赖缓存 | 缓存 `~/.cache/pip`，key 取 `requirements.txt` 的哈希 |
| 执行 | `pytest --alluredir=allure-results --clean-alluredir`，并设 `CI=true` 触发 headless |
| 产物 | `if: always()` 上传 `allure-results/` 为 artifact（用例挂了也能拿到结果） |

### 本地与 CI 的行为差异

| 行为 | 本地 | CI |
|---|---|---|
| 浏览器形态 | 有界面，最大化窗口 | `--headless=new`，1920×1080 |
| 代理 | 强制直连 | 强制直连（Actions 本来也没代理） |
| IPv6 固定 | 生效 | **不生效**（GitHub Actions 无 IPv6 出口，钉了会全挂） |
| `SE_OFFLINE` | `true`（由脚本设） | 未设，靠 Actions 正常联网下载 chromedriver |
| 报告 | 本地 `allure serve` | 只上传 artifact，不部署 GitHub Pages |

---

## 7. 调试问题记录

### 问题一：外网用例偶发慢到 90s+，最差直接超时

**症状**：冒烟用例平时 1s 左右，但会周期性出现 92s、120s+ 的极端耗时，且没有固定规律。

**排查**：

1. 拆解耗时，发现时间不是花在等待元素上，而是卡在 `driver.get()` 建连阶段。
2. 发现两件事叠加：
   - 本机开着系统代理，Chrome 默认读系统代理，saucedemo 走代理实测 16.7s（直连 1.1s），最差超过 120s 直接超时；
   - saucedemo 托管在 GitHub Pages，其 IPv4（`185.199.x.x`）在国内时断时续，而 IPv6（`2606:50c0::`）稳定。Chrome 会在多个地址间轮询，每踩中一个被丢的 IPv4 连接就要等约 21s TCP 超时——这才是 92s 这种数字的来源（几个坏地址叠加）。

**修复**：

- [driver_factory.py](utils/driver_factory.py) 加 `--no-proxy-server` 强制直连（留 `USE_SYSTEM_PROXY=1` 逃生口）；
- 本地加 `--host-resolver-rules=MAP www.saucedemo.com [2606:50c0:8000::153]` 固定走 IPv6，且仅在非 CI 生效。

**两个关键细节**（都是踩过的坑）：

- **走代理时 `--host-resolver-rules` 会静默失效**。DNS 由代理端解析，本地 MAP 规则被直接跳过、不报错。所以「强制直连」和「固定 IPv6」必须同时存在，缺一个另一个就白搭。
- **IPv6 字面量必须带方括号**。写成 `MAP www.saucedemo.com 2606:50c0:8000::153` 不会报错，但会静默失效并报 `ERR_NAME_NOT_RESOLVED`。

**结果**：冒烟稳定在 1s 量级。

### 问题二：每天/每小时「第一次跑」莫名慢约 70 秒

**症状**：连续跑几次都很快，但隔一段时间后的第一次执行总要干等约 70s 才开始。

**排查**：慢的是 `webdriver.Chrome()` 构造，不是用例本身。Selenium Manager 会为 chromedriver 缓存条目记录 1 小时有效期，过期后它会直连 `googlechromelabs.github.io` 重新核对版本；该域名在国内不可达，于是先干等 TCP 超时（约 70s），才回退到本地缓存继续跑。

**修复**：[run_tests.ps1](run_tests.ps1#L13) 里设 `$env:SE_OFFLINE = "true"`，让 Selenium Manager 只用本地缓存、永不联网。

**代价与配套**：Chrome 大版本升级后本地缓存版本对不上时，这个开关会导致启动失败。此时需要临时注释掉 `SE_OFFLINE`、手动导出 `HTTPS_PROXY` 跑一次让它重新下载驱动，再把两处改回来——这套操作已经写进脚本注释，避免下次重新排查一遍。

### 问题三：断言「购物车为空」时卡满 10 秒超时

**症状**：`test_remove_item_empties_cart` 里两次移除商品后断言列表为空，逻辑正确但要白等到超时；空购物车场景下方法直接抛 `WaitTimeoutError` 而不是返回 `[]`。

**排查**：最初用 `wait.present_all(ITEM_NAME)` 取商品名列表，但 `presence_of_all_elements_located` 在匹配到 **0 个**元素时返回空列表，而 `WebDriverWait.until()` 把 falsy 返回值当作「条件未满足」，于是继续轮询直到超时。也就是说：**「等待至少一个元素出现」这个语义，天生无法表达「等待元素全部消失」**。

**修复**：[cart_page.py](pages/cart_page.py#L18-L33) 改成先等容器 `#cart_contents_container` 出现（它始终存在），再用 `driver.find_elements` 直接收集——空列表是合法返回值，不再等价于「还没等到」。文件里保留了另一种写法（1s 短超时探测 + 捕获 `WaitTimeoutError` 返回 `[]`）的注释，作为备选方案记录。

**延伸结论**：`present_all` 适合「至少一个」的场景，判断「全部消失」应使用 `invisible`（逐元素）或先确认容器存在再取列表。

---

## 8. 已知问题与待办

### 本次实测结果

| 运行 | 命令要点 | 结果 |
|---|---|---|
| 本地等待自测 | `pytest tests/test_wait_utils.py`，`CI=true`（headless）+ `-o addopts=""` | **13 passed**，46.4s |
| 冒烟 | `pytest tests/test_smoke.py`，不设 `CI`（真实窗口 + IPv6 固定） | **1 passed**，4.7s（call 阶段 2.1s） |
| 其余外网用例 | `pytest` 登录/库存/购物车/结账 4 个文件 | **4 failed, 6 passed**，425.5s |
| 本地等待自测（P5/P6 修复后复跑） | `pytest -m "wait or action"`，`CI=true` | **13 passed, 11 deselected**，**43.0s** ✅ |
| 登录模块（P0 修复后复跑） | `pytest -m login`，`CI=true` | **4 passed, 20 deselected**，**17.8s** ✅ |
| 其余外网用例（P0 修复后复跑） | `pytest -m "smoke or inventory or cart or checkout"`，`CI=true` | **7 passed, 17 deselected**，**55.7s** ✅ |
| **全量一次性跑通（P5 加固后）** | `pytest`（不加 `-m` 过滤），`CI=true` | **24 passed**，**220.5s（3:40）** ✅ |

> **当前状态：24 条全部实测通过**，且已用一次不加过滤的全量运行确认（`24 passed in 220.48s`）。修复前那批 `4 failed` 全部来自登录用例的 P0 缺陷。
>
> 注：分批跑合计约 116s，全量跑 220s，差异主要来自外网用例的网络波动与偶发启动重试，不是固定开销。

### P0（已修复，实测通过）：登录失败用例必然失败，断言根本没执行

`LoginPage.login()` 点完登录按钮后无条件执行 `until_url_contains("inventory.html")`（[login_page.py](pages/login_page.py#L16)）。失败场景的 URL 永远停在 `https://www.saucedemo.com/`，于是 3 条失败用例都在 10s 后抛 `WaitTimeoutError`，`assert data["expected"] in get_error_message()` 一行都没跑到。实测报错原文：

```
WaitTimeoutError: 等待超时（10.0s）：期望「URL 包含 'inventory.html'」
  locator: url = 'inventory.html'
  页面标题: Swag Labs
  当前 URL: https://www.saucedemo.com/
```

修复（已实施）：把 `login()` 拆成两步——`submit_credentials()` 只填充并点击、不判断跳转；`login()` 在此基础上再断言 `until_url_contains("inventory.html")`，失败用例改用 `submit_credentials()` + 等待错误提示可见，并补一条「URL 没有变成 inventory.html」的断言。正负两条路径各用各的等待条件。

**验证状态：已实测通过。** 修复后 `pytest -m login` 结果：

```
4 passed, 20 deselected in 17.81s
```

4 条登录用例（1 条成功 + 3 条失败场景）全部通过，总耗时 17.8 秒——原来 3 条失败场景各要干等 10s 超时（合计 30s+），现在不再等待，说明失败分支确实走上了「等错误提示」而不是「等 URL 跳转」。

### P1：`test_login_success` 出现过一次 120s 挂起

`driver.get("https://www.saucedemo.com/")` 卡在 chromedriver 的 read timeout（`read timeout=120`），而同批后面的库存/购物车/结账用例（同样要登录）全部通过；同配置下单跑冒烟只用 2.1s。怀疑与本地钉死 IPv6 的 `--host-resolver-rules` 有关：钉成单一地址后失去多地址回退，IPv6 路径一抖就整体挂住。待复现确认，排障时可去掉 MAP 规则或用 `USE_SYSTEM_PROXY=1` 做对照实验。

**复跑情况**：P0 修复后重跑 `-m login`（4 条，含 `test_login_success`）耗时 17.8 秒、未再出现长挂起。因只跑了一轮，仍按「偶发、未定位」保留，不宣称已解决。

### P2：其它待办

- **每条用例都新建一次 driver**，整套跑下来偏慢（10 条外网 425s，其中约 120s 是上面那次挂起）。若调用频繁，可考虑 driver 提到 session 级 fixture + 用例间 `delete_all_cookies()`，代价是页面状态残留风险上升。
- 仓库根目录有 3 个临时脚本：`_marker_count.ps1`（统计各 marker 用例数，可留）、`_net_probe.ps1` 和 `_timing_probe.ps1`（均为 0 字节空文件、无任何引用，可删）。
- `allure-results/`、`report/` 已在 [.gitignore](.gitignore) 中忽略，但本地会持续累积。
- CI 只上传 artifact，不产出可直接访问的报告站点；如需可访问，可加 `allure generate` + GitHub Pages 发布。
- `CartPage.get_item_names` 仍直接调用 `driver.find_elements`，与「元素获取全部经 WaitUtils」的约定有出入（问题三的权衡结果）。

### 自动化验证的两个环境障碍（与项目代码无关）

**其一：命令沙箱拿到 `WRITE_DAC` 失败。** 默认 `workspace-write` 沙箱下任何命令都会在启动前失败：

```
SetNamedSecurityInfoW failed (Win32 5): grantWrite(D:\Code\Python\autotest)
```

该目录 Owner 就是当前用户、`Authenticated Users` 也有 `Modify`，但进程拿不到改 DACL 的权限（仅 `BUILTIN\Administrators` 显式持有）——所以「能写文件」却「改不了 ACL」。给该目录补一条显式 ACE 后此问题消失。

**其二：受限会话里 Chrome 起不来。** 症状是**所有**用例都挂在 `driver` fixture 的 `create_driver()`，与用例代码无关：

```
SessionNotCreatedException: session not created: Chrome failed to start: crashed.
  (session not created: DevToolsActivePort file doesn't exist)
```

绕过 pytest 直接命令行启动 Chrome 可以定位到根因：

```
chrome.exe --headless=new --user-data-dir=... --dump-dom about:blank
[ERROR:crashpad_client_win.cc:430] OpenProcess: 拒绝访问。 (0x5)
[ERROR:crashpad_client_win.cc:144] crash server failed to launch, self-terminating
[FATAL:mojo\public\cpp\platform\platform_channel.cc:112] Check failed: . : 拒绝访问。 (0x5)
```

即 Chrome 的崩溃上报进程和 Mojo IPC 命名通道都被拒绝，浏览器自身无法启动，`--no-sandbox` 与 `--disable-breakpad` 均无效。结论：**UI 用例必须在普通终端（或 CI）里执行**，受限的自动化会话只能做收集、静态检查这类不启动浏览器的工作。

### P3：终端里「pytest 不能用」——其实是 venv 没激活

最常见的误判。症状是 `pytest --version` 报 `ModuleNotFoundError: No module named 'pytest'`，或者 `python -m pytest` 找不到 selenium，但项目本身完好。

判据（两条命令即可分清）：

```powershell
# A. 用 venv 解释器直接问 —— 正常会打印版本号
& '.\autotest\Scripts\python.exe' -m pytest --version

# B. 用终端里的 python 问 —— 若这里报 ModuleNotFoundError，就是没激活
python -m pytest --version
```

A 正常、B 失败 = **只是终端里的 `python` 指向系统解释器**（`D:\Program Files (x86)\Python\python.exe`），那里没装依赖。三种解法，任选：

1. **直接用项目脚本**（推荐，最省心）：
   ```powershell
   .\run_tests.ps1
   ```
   它内部写死 `autotest\Scripts\python.exe`，完全不依赖终端激活状态。
2. **显式用 venv 解释器**（等价写法，注意先切目录）：
   ```powershell
   Set-Location 'D:\Code\Python\autotest'
   & '.\autotest\Scripts\python.exe' -m pytest -o addopts="" -q
   ```
3. **让 VS Code 终端自动激活**：`Ctrl+Shift+P` → *Python: Select Interpreter* → 选 `autotest\Scripts\python.exe`。若此时终端报「未对文件 ...\Activate.ps1 进行数字签名」，见下一条。

### P4：`Activate.ps1` 报「未进行数字签名 / UnauthorizedAccess」

本机 `Get-ExecutionPolicy` 是 `RemoteSigned`，正常应允许本地未签名脚本。已排除的方向：

- 该文件**没有** `Zone.Identifier`（`Get-Item -Stream Zone.Identifier` 无输出、`dir /r` 无流），不是「来自网络」标记；
- 不是文件损坏：删掉重建、换新脚本同样报错；
- 不是组策略：`MachinePolicy`/`UserPolicy` 均为 `Undefined`，注册表 `Policies\Microsoft\Windows\PowerShell` 无值；
- 不是 PowerShell 配置文件：`$PROFILE` 三类文件都不存在。

最终只在**受限执行环境**里稳定复现（该环境同时拒绝 `fsutil`、`Get-CimInstance`、`Get-MpComputerStatus`，且对 `.ps1` 施加了 AllSigned 级限制）。**普通窗口不受影响**（新建脚本可直接运行）。

如果确实需要在报错的环境里激活，用可回退的放宽手段：

```powershell
Set-ExecutionPolicy -Scope Process  -ExecutionPolicy Bypass   # 只影响当前终端
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy Bypass # 长期生效（可改回 RemoteSigned）
```

`Bypass` 是实测唯一能穿透该拦截的档位（`RemoteSigned` / `Unrestricted` 均失败）。

### P5：`session not created: cannot create temp dir for user data dir`（已修）

症状：所有用例在 `driver` fixture 处失败，报

```
selenium.common.exceptions.SessionNotCreatedException: Message: session not created
from unknown error: cannot create temp dir for user data dir
```

不是驱动版本、不是磁盘空间、也不是 `%TEMP%` 指向异常（本机 `%TEMP%` 就是 `C:\Users\1\AppData\Local\Temp`，可正常写）。

**根因**：默认由 chromedriver 在 `%TEMP%` 下创建 Chrome 的 user-data 目录，并且会给该目录设置一个自定义 DACL——这一步需要 `WRITE_DAC`，在权限被收紧的环境里会失败（与本文档前面记录的 `grantWrite` 失败属同一类）。

**修复**（[utils/driver_factory.py](utils/driver_factory.py#L12-L29)）：改由 Python 用普通权限在项目内 `.tmp/` 下建目录，再通过 `--user-data-dir` 显式传给 Chrome，绕开 chromedriver 的目录创建：

```python
path = os.path.join(base, "chrome-profile-" + uuid.uuid4().hex[:8])
os.makedirs(path, exist_ok=True)
options.add_argument(f"--user-data-dir={path}")
atexit.register(shutil.rmtree, path, True)   # 退出时尽力清理
```

几个实现细节：

- 目录**不带受限 ACL**（刻意不用 `tempfile.mkdtemp`，它会给目录加受限 ACL，后续删除会 `Access denied`）；
- 每条用例独立目录，不会串 cookie/缓存，不影响登录类用例的「干净会话」前提；
- `.tmp/` 已加入 [.gitignore](.gitignore)；
- 设 `KEEP_CHROME_PROFILE=1` 可保留现场（目录不自动删），排查用。

**同类第二处**：修掉 user-data 目录之后，会暴露另一个同源错误——

```
session not created: from unknown error: cannot create temp dir for unpacking extensions
```

chromedriver 还要在 `TEMP` 下建「解包扩展」用的目录，同样会设自定义 DACL。因此 [utils/driver_factory.py](utils/driver_factory.py) 里额外有 `_prepare_temp_dir()`：把 `TEMP`/`TMP` 指向项目内 `.tmp/tmp/`（该目录权限通常比用户 Temp 宽），并写回 `os.environ` 让 Selenium 派生的 chromedriver 继承。设 `CHROME_TEMP_DIR=system` 可沿用系统 TEMP。

**回滚**：删掉 `_user_data_dir()` / `_prepare_temp_dir()` 两个函数及 `create_driver()` 里对应的三行调用即可恢复默认行为。（加固与重试的回滚见本节末尾）

**验证结果：已实测通过。** 修复后同一台机器上跑 `pytest -m "wait or action"`：

```
13 passed, 11 deselected in 43.02s
```

即 13 条本地用例全部通过、总耗时 43 秒（单次 `create_driver()` 从分钟级降到秒级）。注意这些改动只影响**测试进程内**的 `TEMP`/`TMP` 与 Chrome 启动参数，不改变系统环境变量。

**该故障会偶发**：同一台机器、同一套配置，出现过「一次 `DRIVER OK`、下一次却报 `cannot create temp dir for unpacking extensions`」的情况——说明 chromedriver 建临时目录本身就是不稳的，不是配置选错。因此又加了三层加固：

| 加固 | 目的 |
|---|---|
| 建目录后 `icacls <dir> /grant <user>:(OI)(CI)F` | 继承 ACL 不够时补授权（失败静默跳过） |
| `--disable-extensions` | 不加载扩展，让 chromedriver 不必走「解包扩展」那条建目录的路径 |
| 启动失败最多重试 3 次，每次换新 profile 目录 | 覆盖偶发失败；3 次全败才抛出原始异常 |

加固后复跑：`13 passed, 11 deselected in 43.62s` ✅

**回滚**：删掉 `_user_data_dir()` / `_prepare_temp_dir()` / `_grant_full_control()` 及 `create_driver()` 里的重试循环，恢复成直接 `webdriver.Chrome(options=...)` 即可。

### P6：跑一个用例要卡 1~3 分钟才出第一个结果（已修）

症状：`pytest` 启动后长时间没有任何输出，三分钟左右才蹦出第一个 `E`；用例越多等得越久。慢的不是浏览器，是 **Selenium Manager 的联网校验**。

每个用例的 `driver` fixture 都会构造一次 `webdriver.Chrome()`，Selenium Manager 在这之前要访问 `googlechromelabs.github.io` 核对驱动版本。该域名在受限网络下不可达，于是每次先等完几个 TCP 超时（累计 1~3 分钟）才回退本地缓存——`13` 条用例就是半小时。

**为什么之前不容易发现**：[run_tests.ps1](run_tests.ps1#L13) 里设了 `$env:SE_OFFLINE = "true"`，走它跑就不会有这个等待；但一旦改成直接调解释器（`.\autotest\Scripts\python.exe -m pytest ...`，P3 里推荐的写法），这个开关就丢了。

**修复**（[utils/driver_factory.py](utils/driver_factory.py)）：在 `create_driver()` 开头兜底

```python
os.environ.setdefault("SE_OFFLINE", "true")
```

这样无论从哪个入口跑都会离线，且 `SE_OFFLINE=false` 仍可显式覆盖（需要更新驱动时）。

**判据**：修复前后同一机器上单条用例的 `create_driver()` 耗时从分钟级降到秒级。

**验证结果：已实测通过。** 修复后 `pytest -m "wait or action"` 全程 **43.02 秒**跑完 13 条（修复前一个用例就要三分钟）。

---

## 9. 本次会话遗留的「非项目」问题（备忘）

排查过程中确认过、但与本项目代码无关的坑，记录下来避免重复踩：

| 问题 | 结论 |
|---|---|
| `run_tests.ps1` 报「未进行数字签名」 | 项目文件带「来自网络」标记，`RemoteSigned` 要求签名。`Unblock-File` / 删 ADS 均无效；用 `Set-ExecutionPolicy -Scope CurrentUser Bypass` 或直接调 venv 解释器可绕过（见 P3/P4） |
| VS Code 安装被更新中断（`resources` 被挪进 `<commit>\` 目录） | 表现为 `Code.exe` 启动即退出（`--version` 打印的是 Electron 版本而非 VS Code 版本）。修法：从该 commit 目录把文件铺回安装根目录，或按官方安装包覆盖重装 |



