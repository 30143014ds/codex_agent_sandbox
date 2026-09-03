# codex_agent_sandbox

Портативная изолированная среда для запуска Claude Code и Codex CLI в одном Docker-контейнере.
Один и тот же `docker-compose.yml` работает и headless на VDS через SSH,
и как dev-контейнер в VS Code Remote — конфигурация не дублируется.

## Структура

```
.
├── Dockerfile              # образ: Node.js 22 + Claude Code + Codex CLI + непривилегированный пользователь
├── docker-compose.yml      # сервис claude_dev_agent: тома проекта, конфигов агентов, лимиты ресурсов
├── .devcontainer/
│   └── devcontainer.json   # ссылается на тот же docker-compose.yml для VS Code Remote
├── codex_dev_md/
│   └── AGENT.md        #инструкции агенту
│   └── config.toml     #конфиг агента
│   └── scout.toml        #инструкции субагенту скауту
│   └── worker.toml        #инструкции субагенту воркеру
│   └── architect.toml       #инструкции субагенту архитектору
├── env.example         # шаблон переменных окружения (переименовать в .env.example)
├── setup.sh                # проверка Docker/Compose + сборка + запуск headless
├── dev_agent_setup.sh      # скрипт по настройке субагентов для агента-разработчика
├── gitignore           # переименовать в .gitignore
├── workspace/               # код проекта — единственное, что видят агенты
└── codex-config/            # конфиг и сессия Codex CLI (bind mount, не в git)
```


## Вариант 1: headless на VDS через SSH

```bash
git clone git@github.com:30143014ds/codex_agent_sandbox.git codex_agent_sandbox
cd codex_agent_sandbox
cp .env.example .env      # впишите нужные ключи/токены
chmod +x setup.sh
chmod +x dev_agent_setup.sh
./setup.sh
```

Работа с агентами:
```bash
docker exec -it claude_dev_agent codex       # запустить Codex CLI
docker exec -it claude_dev_agent bash        # шелл внутри контейнера
docker compose logs -f
docker compose stop                          # остановить, не удаляя контейнер
docker compose down                          # остановить и удалить контейнер (конфиги останутся на хосте)
```

## Вариант 2: открыть в VS Code (локально или Remote-SSH)

1. Установите расширение **Dev Containers** в VS Code.
2. Если сервер удалённый — подключитесь через **Remote-SSH** к VDS.
3. Откройте папку репозитория → палитра команд → **"Dev Containers: Reopen in Container"**.
4. VS Code соберёт образ по `docker-compose.yml` и `.devcontainer/devcontainer.json`,
   подключит терминал под пользователем `agent`.
5. Полезно при первом логине через браузер: VS Code автоматически пробрасывает
   локальные порты с VDS на ваш компьютер, поэтому `codex login` можно запускать прямо в терминале VS Code, а не только на
   локальной машине.

Контейнер после закрытия VS Code **не останавливается** (`shutdownAction: none`).
Остановить вручную: `docker compose down`.

## Изоляция

- Контейнер работает под пользователем `agent` (не root), с тем же UID/GID, что и пользователь на хосте (см. `ARG HOST_UID/HOST_GID` в `Dockerfile`) — это устраняет проблемы прав на bind mount.
- Примонтированы только `workspace/`, `codex-config/` — остальная файловая система хоста и SSH-ключи недоступны.
- Ресурсы ограничены в `docker-compose.yml` (`deploy.resources.limits`).
- Для сетевой изоляции добавьте allowlist-прокси отдельным сервисом.

## Аутентификация

### Codex CLI
Один из вариантов:
- `OPENAI_API_KEY` в `.env` — ключ с [platform.openai.com/api-keys](https://platform.openai.com/api-keys).
- `codex login --device-auth` прямо внутри контейнера (через VS Code терминал) — headless-режим с одноразовым кодом, без проброса портов.
- Перенос готового `~/.codex/auth.json` с локальной машины в `codex-config/auth.json` на сервере.

