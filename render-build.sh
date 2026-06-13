#!/usr/bin/env bash
# exit on error
set -o errexit

echo "🚀 Iniciando construcción del Monorepo DaePoint POS..."

echo "1️⃣ Construyendo el Frontend (Angular)..."
cd frontend
npm install --legacy-peer-deps
npm run build -- --configuration=production

echo "2️⃣ Construyendo el Backend (Node.js/Express)..."
cd ../backend
npm install
# Compile TypeScript files
npx tsc

echo "✅ ¡Monorepo DaePoint POS compilado y listo para despegar!"
