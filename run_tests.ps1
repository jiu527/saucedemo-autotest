# 运行 pytest 并生成 Allure 结果。
#
# 用法：
#   .\run_tests.ps1                  # 跑全部用例
#   .\run_tests.ps1 -k smoke         # 透传参数给 pytest
#   .\run_tests.ps1 tests/test_smoke.py::test_smoke
## 被测站点不走代理（driver_factory.py 已用 --proxy-server=direct:// 禁掉），
# 这里也不再导出 HTTPS_PROXY。
#
# SE_OFFLINE=true 让 Selenium Manager 只用本地缓存的 chromedriver、永不联网。
# 没有它时缓存条目每 1 小时过期一次，SM 会直连 googlechromelabs.github.io
# 重新核对版本，被墙后干等 ~70s 才回退缓存——表现为"每天/每小时的第一次跑莫名慢"。
$env:SE_OFFLINE = "true"
#
# 唯一需要联网下载驱动的场合：Chrome 大版本更新导致本地缓存版本对不上时，
# 临时注释掉上面的 SE_OFFLINE，并手动执行
#   $env:HTTPS_PROXY = "http://127.0.0.1:10809"
# 跑一次让它重新下载，然后把两处改回来。。

$python = Join-Path $PSScriptRoot "autotest\Scripts\python.exe"
if (-not (Test-Path $python)) {
    Write-Error "找不到虚拟环境解释器：$python"
    exit 1
}

& $python -m pytest @args
exit $LASTEXITCODE
