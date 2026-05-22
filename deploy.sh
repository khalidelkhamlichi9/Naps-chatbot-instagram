#!/bin/bash

# Chatbot NAPS - Quick Deploy Script
# Usage: ./deploy.sh

echo "🚀 Starting Deployment for Chatbot NAPS..."

# 1. Check if .env exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found!"
    echo "Please copy .env.example to .env and fill in your credentials."
    exit 1
fi

# 2. Create data directory for SQLite if it doesn't exist
mkdir -p data

# 3. Pull/Build and Start containers
echo "📦 Building and starting containers..."
docker compose up -d --build

# 4. Clean up dangling images
echo "🧹 Cleaning up..."
docker image prune -f

echo "✅ Deployment complete!"
echo "App is running at http://localhost:8000"
echo "Check logs with: docker compose logs -f"
