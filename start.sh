#!/bin/bash
# Quick start script for Xray VPN with 3x-ui

set -e

echo "🚀 Starting Xray VPN service..."

# 1. Check environment
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    echo "📋 Creating .env from .env.example..."
    cp .env.example .env
    echo "⚠️  Please edit .env with your settings"
    exit 1
fi

# 2. Load environment
source .env

# 3. Validate required variables
required_vars=(
    "TELEGRAM_BOT_TOKEN"
    "XRAY_ADMIN_SECRET"
    "VPN_ENDPOINT_HOST"
    "POSTGRES_PASSWORD"
)

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ Missing required variable: $var"
        exit 1
    fi
done

# 4. Create directories
mkdir -p xray ssl frontend/dist

# 5. Build and start
echo "📦 Building Docker images..."
docker-compose build

echo "🐳 Starting Docker containers..."
docker-compose up -d

echo "⏳ Waiting for services to be ready..."
sleep 5

# 6. Check health
echo "🏥 Checking service health..."

for i in {1..30}; do
    if curl -s http://localhost:8080/api/health > /dev/null; then
        echo "✅ API is healthy"
        break
    fi
    echo "⏳ Waiting... ($i/30)"
    sleep 1
done

# 7. Show info
echo ""
echo "✅ Xray VPN Service Started!"
echo ""
echo "📍 Access points:"
echo "  • FastAPI: http://localhost:8080/api/health"
echo "  • 3x-ui Admin: http://localhost:8080/admin/"
echo "  • Telegram Bot: @$(echo $TELEGRAM_BOT_TOKEN | cut -d: -f1)"
echo ""
echo "🔑 Default credentials:"
echo "  • 3x-ui: $THREE_X_UI_USERNAME / $THREE_X_UI_PASSWORD"
echo "  • Admin API: $ADMIN_USER / $ADMIN_PASSWORD"
echo ""
echo "📚 Documentation: README_XRAY_3XUI.md"
echo ""
echo "🛑 To stop: docker-compose down"
echo "📊 To see logs: docker-compose logs -f"
