#!/bin/sh

set -e

echo "🌵 Aguardando banco de dados subir..."

while ! nc -z db 3306; do
  sleep 1
done

echo "✅ Banco de dados disponível!"

echo "📦 Rodando Migrações..."
python manage.py migrate

echo "🚀 Iniciando Servidor..."
python manage.py runserver 0.0.0.0:8000