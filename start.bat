@echo off
chcp 65001 >nul
echo ============================================
echo  easyNginx - Nginx 管理工具
echo ============================================
echo.

cd /d "%~dp0"

IF EXIST venv\Scripts\activate.bat (
    echo 检测到虚拟环境，正在激活...
    call venv\Scripts\activate.bat
    echo 虚拟环境已激活 [OK]
) ELSE (
    echo 未检测到虚拟环境，使用系统 Python
)

echo.
echo 正在启动 easyNginx...
echo.

python main.py

if %errorlevel% neq 0 (
    echo.
    echo ============================================
    echo 启动失败！错误代码: %errorlevel%
    echo ============================================
    echo.
    echo 可能的原因：
    echo 1. Python 未安装或不在 PATH 中
    echo 2. 依赖库未安装 (运行: pip install -r requirements.txt)
    echo 3. Nginx 未正确安装
    echo.
    echo 请查看 logs\app.log 获取详细错误信息
    pause
) else (
    echo.
    echo ============================================
    echo 程序已正常退出
    echo ============================================
)
