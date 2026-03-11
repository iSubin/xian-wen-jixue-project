#!/bin/bash
set -e

echo "=========================================="
echo "  ShengWen 一键部署脚本"
echo "=========================================="
echo ""

# 检查 Node.js
if ! command -v node &> /dev/null; then
    echo "❌ 错误: 未找到 Node.js，请先安装 Node.js"
    exit 1
fi

# 检查 npm
if ! command -v npm &> /dev/null; then
    echo "❌ 错误: 未找到 npm，请先安装 npm"
    exit 1
fi

# 检查 Python
if ! command -v python &> /dev/null && ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到 Python，请先安装 Python 3.8+"
    exit 1
fi

# 使用 python3 或 python
PYTHON_CMD="python3"
if ! command -v python3 &> /dev/null; then
    PYTHON_CMD="python"
fi

echo "✓ 环境检查通过"
echo ""

# 前端构建
echo "📦 步骤 1/3: 安装前端依赖..."
cd frontend
npm install

echo ""
echo "🔨 步骤 2/3: 构建前端..."
npm run build

cd ..
echo "✓ 前端构建完成"
echo ""

# 后端依赖
echo "📦 步骤 3/3: 安装后端依赖..."
$PYTHON_CMD -m pip install -r requirements.txt

echo ""
echo "=========================================="
echo "✅ 部署完成！"
echo "=========================================="
echo ""
echo "下一步操作："
echo "1. 创建配置文件: cp config/settings.example.json config/settings.json"
echo "2. 配置 LLM API 参数等（llm.base_url / llm.api_key / llm.model_id）"
echo "3. 启动服务: python ShengWen-app.py"
echo ""

