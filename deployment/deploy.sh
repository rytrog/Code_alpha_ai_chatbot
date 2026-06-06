#!/bin/bash
# ══════════════════════════════════════════════════
# University AI Chatbot — Deployment Script
# ══════════════════════════════════════════════════
set -e

echo "🎓 University AI Chatbot — Deployment"
echo "══════════════════════════════════════"

# Check prerequisites
for cmd in docker docker-compose; do
  if ! command -v $cmd &> /dev/null; then
    echo "❌ $cmd is not installed."
    exit 1
  fi
done

# Navigate to deployment directory
cd "$(dirname "$0")"

# Check for API key
if [ -z "$GEMINI_API_KEY" ]; then
  echo "⚠️  GEMINI_API_KEY not set. AI features will be disabled."
  echo "   Set it with: export GEMINI_API_KEY=your_key_here"
fi

# Build and start
echo ""
echo "📦 Building Docker images..."
docker-compose build

echo ""
echo "🚀 Starting containers..."
docker-compose up -d

echo ""
echo "⏳ Waiting for services..."
sleep 8

# Health check
if curl -sf http://localhost:8000/api/health | grep -q "healthy"; then
  echo "✅ Backend is healthy"
else
  echo "⚠️  Backend health check pending (may still be starting)"
fi

echo ""
echo "══════════════════════════════════════"
echo "✅ Deployment complete!"
echo ""
echo "  📡 API:         http://localhost:8000"
echo "  📡 API Docs:    http://localhost:8000/docs"
echo "  💬 Widget:      http://localhost/widget/chatbot.html"
echo "  🔧 Admin:       http://localhost/admin/dashboard.html"
echo "  ❤️  Health:      http://localhost:8000/api/health"
echo ""
echo "  📋 Logs:   docker-compose logs -f"
echo "  🛑 Stop:   docker-compose down"
echo "══════════════════════════════════════"
