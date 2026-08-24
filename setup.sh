#!/usr/bin/env bash
set -euo pipefail

# --- 1. Проверка Docker ---
if ! command -v docker &> /dev/null; then
  echo "Docker не найден. Установите Docker Engine и запустите скрипт снова:"
  echo "  curl -fsSL https://get.docker.com | sudo sh"
  echo "  sudo usermod -aG docker \$USER && newgrp docker"
  exit 1
fi

# --- 2. Проверка Docker Compose ---
if docker compose version &> /dev/null; then
  COMPOSE="docker compose"
elif command -v docker-compose &> /dev/null; then
  COMPOSE="docker-compose"
else
  echo "Docker Compose не найден. Установите плагин и запустите скрипт снова:"
  echo "  sudo apt install -y docker-compose-plugin"
  exit 1
fi

echo "Используется: $COMPOSE"

# --- 3. .env ---
if [ ! -f .env ]; then
  cp .env.example .env
  echo "Создан файл .env — заполните ключи Codex перед следующим запуском."
  exit 0
fi

# --- 4. Рабочие директории ---
mkdir -p workspace codex-config

export HOST_UID=$(id -u)
export HOST_GID=$(id -g)

# --- 5. Сборка и запуск ---
$COMPOSE build
$COMPOSE up -d

echo ""
echo "Готово. Контейнер codex_agent_sandbox запущен."
echo "Codex CLI:   docker exec -it codex_agent_sandbox codex"
echo "Конфиги на хосте: ./codex-config/"
