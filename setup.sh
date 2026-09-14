#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${ROOT_DIR}"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker не найден. Установите Docker Engine и повторите запуск:" >&2
  echo "  curl -fsSL https://get.docker.com | sudo sh" >&2
  echo "  sudo usermod -aG docker \$USER && newgrp docker" >&2
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "Требуется Docker Compose plugin (команда: docker compose)." >&2
  exit 1
fi

mkdir -p instances workspaces
chmod 0755 bin/agent

echo
echo "Инициализация завершена. Доступные типы агентов:"
./bin/agent list
echo
echo "Примеры:"
echo "  ./bin/agent create developer dev-main -e /absolute/path/to/project"
echo "  ./bin/agent create cbt cbt-main"
