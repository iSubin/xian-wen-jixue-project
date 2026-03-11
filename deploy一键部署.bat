@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ==========================================
echo   ShengWen 一键部署脚本
echo ==========================================
echo.

REM 检查 Node.js
where node >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ 错误: 未找到 Node.js，请先安装 Node.js
    pause
    exit /b 1
)

REM 检查 npm
where npm >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ 错误: 未找到 npm，请先安装 npm
    pause
    exit /b 1
)

REM 检查 Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ 错误: 未找到 Python，请先安装 Python 3.8+
    pause
    exit /b 1
)

echo ✓ 环境检查通过
echo.

REM 前端构建
echo 📦 步骤 1/3: 安装前端依赖...
cd frontend
call npm install
if %errorlevel% neq 0 (
    echo ❌ 前端依赖安装失败
    cd ..
    pause
    exit /b 1
)

echo.
echo 🔨 步骤 2/3: 构建前端...
call npm run build
if %errorlevel% neq 0 (
    echo ❌ 前端构建失败
    cd ..
    pause
    exit /b 1
)

cd ..
echo ✓ 前端构建完成
echo.

REM 后端依赖
echo 📦 步骤 3/3: 安装后端依赖...
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ❌ 后端依赖安装失败
    pause
    exit /b 1
)

echo.
echo ==========================================
echo ✅ 部署完成！
echo ==========================================
echo.
echo 下一步操作：
echo 1. 创建配置文件: copy config\settings.example.json config\settings.json
echo 2. 配置 LLM API 参数等（llm.base_url / llm.api_key / llm.model_id）
echo 3. 启动服务: python ShengWen-app.py
echo.
pause

