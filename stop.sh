#!/bin/bash

echo "🛑 Stopping Ferbit services..."
docker-compose down

echo "🧹 Cleaning up (optional - removes images)..."
read -p "Remove built images? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker-compose down --rmi local
    echo "✅ Images removed."
else
    echo "✅ Services stopped (images kept for faster restart)."
fi