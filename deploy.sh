#!/bin/bash

echo "🚀 Deploying Time Capsule Bot..."

# 加载环境变量
if [ -f .env ]; then
    echo "📋 Loading environment variables from .env..."
    source .env
else
    echo "⚠️  .env file not found"
fi

# 检查环境变量
if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo "❌ Error: TELEGRAM_BOT_TOKEN not set"
    echo "Please set it in .env file or export it"
    exit 1
fi

echo "✅ TELEGRAM_BOT_TOKEN loaded successfully"

# 创建数据目录
mkdir -p ./data

# 停止现有容器
echo "🛑 Stopping existing containers..."
docker-compose down

# 构建并启动
echo "🔨 Building and starting containers..."
docker-compose up -d --build

# 查看日志
echo "📋 Container logs:"
docker-compose logs -f