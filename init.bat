@echo off
chcp 65001 >nul
echo ========================================
echo easyNginx 注册表清理工具
echo ========================================
echo.
echo 本工具将清除 easyNginx 在注册表中存储的所有配置信息
echo 包括：
echo   - Nginx 路径配置
echo   - 接管状态
echo   - 备份目录设置
echo.
echo 警告：此操作将重置所有配置，下次启动时需要重新设置 Nginx 路径
echo.
echo 按任意键继续，或关闭窗口取消...
pause >nul
echo.
echo 正在清理注册表...
echo.

:: 设置注册表路径
set "REG_PATH=HKEY_CURRENT_USER\SOFTWARE\easyNginx"

echo 1. 检查注册表项是否存在...
reg query "%REG_PATH%" >nul 2>&1
if %errorlevel% neq 0 (
    echo    注册表项不存在或已被删除
echo    路径：%REG_PATH%
goto :completed
)

echo 2. 删除 easyNginx 注册表项...
reg delete "%REG_PATH%" /f

if %errorlevel% neq 0 (
    echo.
    echo 错误：无法删除注册表项
echo 请以管理员身份运行此脚本
echo.
    pause
    exit /b 1
)

:completed
echo.
echo ========================================
echo 清理完成！
echo ========================================
echo.
echo 已清除 easyNginx 的所有注册表配置
echo 下次启动 easyNginx 时将需要重新配置 Nginx 路径
echo.
echo 按任意键退出...
pause >nul
exit /b 0
