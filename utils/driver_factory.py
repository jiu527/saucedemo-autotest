import atexit
import os
import shutil
import subprocess
import uuid

from selenium import webdriver
from selenium.common.exceptions import SessionNotCreatedException
from selenium.webdriver.chrome.options import Options

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 启动失败时重建目录再试的次数（chromedriver 建临时目录偶发失败）
_LAUNCH_ATTEMPTS = 3


def _grant_full_control(path):
    """尽力给目录补一条当前用户的 FullControl ACE（仅 Windows）。

    chromedriver 建临时目录 / Chrome 写 profile 都需要较宽的权限；某些环境下
    目录的继承 ACL 不够，补一条最省事。失败就静默跳过，不影响主流程。
    """
    if os.name != "nt":
        return
    user = os.environ.get("USERNAME")
    if not user:
        return
    try:
        subprocess.run(
            ["icacls", path, "/grant", f"{user}:(OI)(CI)F", "/Q"],
            capture_output=True, timeout=15, check=False,
        )
    except Exception:
        pass


def _user_data_dir():
    """自己建好 Chrome 的 user-data 目录，再显式传给 Chrome。

    默认由 chromedriver 在 %TEMP% 下创建并给它设自定义 DACL；权限受限时失败，
    报 ``cannot create temp dir for user data dir``。改由我们用普通权限建目录，
    再用 --user-data-dir 指过去，绕开 chromedriver 的创建步骤。

    目录放在项目内 .tmp/ 下（已 gitignore），退出时尽力清理；
    设 KEEP_CHROME_PROFILE=1 可保留现场用于排查。
    """
    base = os.path.join(_PROJECT_ROOT, ".tmp")
    os.makedirs(base, exist_ok=True)
    # 不用 tempfile.mkdtemp：它会给目录加受限 ACL，后续删除会 Access denied。
    path = os.path.join(base, "chrome-profile-" + uuid.uuid4().hex[:8])
    os.makedirs(path, exist_ok=True)
    _grant_full_control(path)
    if os.getenv("KEEP_CHROME_PROFILE") != "1":
        atexit.register(shutil.rmtree, path, True)
    return path


def _prepare_temp_dir():
    """把 TEMP/TMP 指到项目内可写目录，供 chromedriver 使用。

    chromedriver 除 user-data 目录外，还会在 TEMP 下创建「unpacking
    extensions」用的临时目录，同样会设自定义 DACL。权限受限时报：

        cannot create temp dir for user data dir
        cannot create temp dir for unpacking extensions

    这里把 TEMP/TMP 指向项目内 .tmp/tmp（并补 FullControl），写回 os.environ
    让 Selenium 派生的 chromedriver 继承。设 CHROME_TEMP_DIR=system 可沿用系统 TEMP。

    仅 Windows 需要（macOS/Linux 的临时目录没有这个权限问题）。
    """
    if os.name != "nt":
        return None
    if os.getenv("CHROME_TEMP_DIR", "").lower() == "system":
        return None
    path = os.path.join(_PROJECT_ROOT, ".tmp", "tmp")
    os.makedirs(path, exist_ok=True)
    _grant_full_control(path)
    os.environ["TEMP"] = path
    os.environ["TMP"] = path
    return path


def _build_options(profile_dir):
    options = Options()
    # 显式指定 user-data 目录，绕开 chromedriver 建临时目录失败的问题（见上方注释）
    options.add_argument(f"--user-data-dir={profile_dir}")
    # 不加载任何扩展：chromedriver 为「解包扩展」还要在 TEMP 下建目录，
    # 关掉扩展可以少走一条容易失败的路径。
    options.add_argument("--disable-extensions")
    # 被测站点必须直连：走系统代理实测慢 15 倍
    # （saucedemo.com 直连 1.1s，走代理 16.7s，最差超过 120s 直接超时），
    # 而且走代理时 DNS 由代理端解析，下面的 --host-resolver-rules 会静默失效。
    # 仅当所在网络只能经代理出网时，临时设 USE_SYSTEM_PROXY=1 放行。
    if os.getenv("USE_SYSTEM_PROXY") != "1":
        options.add_argument("--no-proxy-server")
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
    return options


def create_driver():
    # Selenium Manager 默认每次构造 driver 前都会联网校验 chromedriver 版本。
    # 该域名（googlechromelabs.github.io）在受限网络下不可达，于是每个用例都要
    # 先等 1~3 分钟的 TCP 超时、才回退本地缓存——表现为「跑一个用例卡三分钟」。
    #
    # 判断条件用 GITHUB_ACTIONS 而不是 CI：本地常为了无头而设 CI=true，那时
    # 仍然需要离线（否则每个用例又开始等网络超时）；而 CI 跑在全新 runner 上、
    # 没有本地驱动缓存、要靠 Selenium Manager 现下驱动，必须允许联网。
    # 需要手动覆盖时设 SE_OFFLINE=false（或 true）即可。
    if not os.getenv("GITHUB_ACTIONS"):
        os.environ.setdefault("SE_OFFLINE", "true")

    # 给 chromedriver 一个能建临时目录的 TEMP（见上方注释）
    _prepare_temp_dir()

    # chromedriver 建临时目录是偶发失败（同一环境时好时坏），失败后换个新
    # profile 目录重试通常就能起来；重试耗尽才把原始异常抛出去。
    last_error = None
    for attempt in range(1, _LAUNCH_ATTEMPTS + 1):
        profile_dir = _user_data_dir()
        try:
            driver = webdriver.Chrome(options=_build_options(profile_dir))
        except SessionNotCreatedException as exc:
            last_error = exc
            shutil.rmtree(profile_dir, ignore_errors=True)
            if attempt < _LAUNCH_ATTEMPTS:
                continue
            raise
        if not os.getenv("CI"):
            driver.maximize_window()
        driver.implicitly_wait(0)  # 关闭隐式等待，后续只用显式等待
        return driver

    raise last_error  # 理论上不可达
