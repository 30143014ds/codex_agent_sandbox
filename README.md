# codex_agent_sandbox

Портативная среда для запуска независимых Codex CLI агентов в Docker.
Можно работать локально или на VDS через SSH. Каждый экземпляр получает свой
home: роль, настройки, skills, SSH, авторизацию и историю Codex.
Проект подключается отдельно как workspace.

## Структура

```text
.
├── Dockerfile                      # Node.js 22 + Python 3.13 + Codex CLI; targets base и developer
├── compose.yaml                    # общее окружение: home и workspace экземпляра
├── setup.sh                        # проверка Docker/Compose и подготовка каталогов
├── bin/agent                       # создание, запуск и управление экземплярами
├── completion/agent.bash            # Bash completion для launcher
├── runtime/
│   ├── codex                       # запуск пользовательской копии Codex
│   └── npm                         # обновление Codex без sudo
├── agents/                         # стартовые шаблоны типов агентов
│   ├── generic/                    # универсальный агент без заданной роли
│   ├── developer/                  # разработчик с внутренним Docker Engine
│   └── cbt/                        # агент для рефлексии и ведения заметок
├── instances/                      # экземпляры; не попадают в Git
│   └── dev-main/
│       ├── instance.env            # пути, UID/GID и порты
│       ├── compose.override.yaml   # копия окружения типа, если оно задано
│       ├── home/                   # подключается как /home/agent
│       │   ├── .codex/             # роль, config, subagents, авторизация и сессии
│       │   ├── .agents/skills/      # skills этого экземпляра
│       │   ├── .ssh/               # SSH-ключи, config и known_hosts
│       │   └── .local/share/codex/  # установка Codex после первого запуска
│       └── workspace/              # проект, если создан без -e
└── workspaces/                     # рабочие папки для -e без пути; не попадают в Git
```

Тип агента используется как шаблон при `create`. Его home и Compose override
копируются в экземпляр. Дальше можно редактировать эти копии: изменения шаблона
не перезаписывают настройки уже созданных экземпляров.

## Запуск локально или на VDS через SSH

На хосте нужны Docker Engine и Docker Compose plugin. Для удалённого сервера
сначала подключитесь по SSH:

```bash
ssh user@server
```

Скачайте репозиторий и подготовьте окружение:

```bash
git clone git@github.com:30143014ds/codex_agent_sandbox.git
cd codex_agent_sandbox
chmod +x setup.sh
./setup.sh
```

`setup.sh` подготавливает каталоги и launcher. Создание и запуск агента выполняются
отдельными командами:

```bash
./bin/agent create developer dev-main -e /srv/projects/my-app
./bin/agent start dev-main
```

При первом запуске войдите в Codex внутри контейнера:

```bash
./bin/agent shell dev-main
codex login --device-auth
exit
```

Затем на хосте откройте агент:

```bash
./bin/agent attach dev-main
```

`start` собирает образ и ждёт готовности контейнера. Для developer готовность
означает, что внутренний Docker Engine запущен и отвечает на `docker info`.

## Выбор workspace и типа агента

Без `-e` проект создаётся внутри экземпляра:

```bash
./bin/agent create generic task-001
# workspace: instances/task-001/workspace
```

С `-e` без пути создаётся отдельная рабочая папка:

```bash
./bin/agent create developer dev-scratch -e
# workspace: workspaces/dev-scratch
```

С `-e /absolute/path` подключается указанный проект. Если папки нет, launcher
создаст её. Несколько экземпляров могут использовать один workspace со своими
ролями и skills; файлы проекта при этом общие.

Для CBT можно создать отдельный экземпляр с папками для заметок:

```bash
./bin/agent create cbt cbt-main
./bin/agent start cbt-main
./bin/agent attach cbt-main
```

## Работа с агентами

```bash
./bin/agent list                    # доступные типы и созданные экземпляры
./bin/agent status                  # состояние всех экземпляров
./bin/agent status dev-main         # состояние одного экземпляра
./bin/agent attach dev-main         # открыть Codex CLI
./bin/agent shell dev-main          # shell внутри контейнера
./bin/agent logs dev-main           # смотреть логи
./bin/agent stop dev-main           # остановить контейнер
./bin/agent start dev-main          # запустить снова
./bin/agent down dev-main           # удалить контейнер и сеть экземпляра
```

`stop` и `down` сохраняют home, workspace и именованный volume внутреннего
Docker. Launcher не удаляет пользовательские данные.

Для подсказок по Tab подключите Bash completion:

```bash
source /absolute/path/to/codex_agent_sandbox/completion/agent.bash
```

Чтобы подключать его автоматически, добавьте эту строку с реальным путём
в `~/.bashrc`.

## Инструкции, настройки и skills

- `workspace/AGENTS.md` описывает проект и общие правила работы с ним.
- `home/.codex/AGENTS.md` задаёт роль конкретного экземпляра.
- `home/.codex/config.toml` содержит настройки Codex этого экземпляра.
- `home/.codex/agents/` содержит определения его субагентов.
- `home/.agents/skills/` содержит его skills.

Внутри контейнера эти файлы доступны в `/workspace` и `/home/agent`.
Codex читает инструкции экземпляра, затем инструкции проекта. Проектный
`.codex/config.toml`, если он есть, может переопределять настройки экземпляра.
Проектные skills из `.agents/skills` также доступны работающим с ним агентам.

Пути `INSTANCE_HOME_PATH`, `WORKSPACE_PATH` и порты можно изменить в
`instances/<name>/instance.env`. Окружение экземпляра настраивается в его
`compose.override.yaml`, если этот файл присутствует.

## Docker и доступ к сервисам developer

Developer запускается с `privileged: true` и собственным Docker Engine внутри
контейнера. Образы, контейнеры и volumes этого Docker сохраняются в отдельном
именованном volume экземпляра. Dockerd работает в foreground и штатно
завершается при `stop`; временные PID-файлы и сокеты в `/run` очищаются.

Порты сервисов внутреннего Docker проброшены на loopback хоста:

- `127.0.0.1:18080` → порт `80` контейнера агента;
- `127.0.0.1:18443` → порт `443`;
- `127.0.0.1:18081` → порт `8080`.

Чтобы получить доступ с локального компьютера к сервисам на VDS, откройте
SSH-туннель:

```bash
ssh \
  -L 18080:127.0.0.1:18080 \
  -L 18443:127.0.0.1:18443 \
  -L 18081:127.0.0.1:18081 \
  user@server
```

Порты хоста задаются в `instance.env` переменными `DEV_HTTP_PORT`,
`DEV_HTTPS_PORT` и `DEV_ADMINER_PORT`. Для второго developer выберите другие
порты перед запуском.

## Изоляция и сохранение данных

- Codex и shell работают под пользователем `agent` с UID/GID пользователя хоста.
- В базовом окружении подключены только home экземпляра и выбранный workspace.
  SSH доступен из `home/.ssh`, если вы положили туда ключи и настройки.
- Каждый экземпляр имеет свою авторизацию, сессии и пользовательские skills.
- Compose использует имя проекта `codex-<instance>` для отдельных контейнеров,
  сетей и именованных volumes.
- CBT работает без внутреннего Docker и опубликованных портов, с отключённым
  повышением привилегий.
- Данные экземпляров, рабочие папки и `.env` исключены из контекста сборки Docker.

## Аутентификация и SSH

Вход через `codex login --device-auth` использует одноразовый код и не требует
проброса порта для входа. Авторизация хранится в
`instances/<name>/home/.codex/auth.json`.

Можно перенести готовый `auth.json` в этот каталог перед запуском нового
экземпляра. Для SSH скопируйте нужные ключи, `config` и `known_hosts` в
`instances/<name>/home/.ssh/`, сохранив права доступа и владельца файлов.
Launcher создаёт каталоги по шаблону и не переносит данные старых экземпляров.

## Обновление Codex

При первом запуске Codex копируется из образа в `~/.local/share/codex` внутри
home экземпляра. Обновить эту копию можно через предложение CLI или командой
в shell контейнера:

```bash
npm install -g @openai/codex@latest
```

Обёртка npm направляет только команду установки или обновления Codex в этот
пользовательский каталог. Поддерживаются `-g` и `--global`, пакет
`@openai/codex` и вариант `@openai/codex@latest`. Остальные npm-команды работают
обычно; глобальные установки в системный каталог требуют sudo.
Обновлённый Codex сохраняется в home экземпляра и переживает пересоздание
контейнера. Другие экземпляры используют свои копии.

## Добавление типа агента

Создайте каталог `agents/<type>/`. Все файлы в нём необязательны:

```text
agents/my-agent/
├── compose.override.yaml           # дополнительное окружение
├── home-template/                  # копируется в home нового экземпляра
│   ├── .codex/
│   │   ├── AGENTS.md               # роль
│   │   ├── config.toml
│   │   └── agents/
│   └── .agents/skills/
└── workspace-template/             # дополняет проект без перезаписи файлов
```

Пустой каталог означает базовое окружение и стандартные настройки Codex.
`.gitkeep` нужен только для сохранения пустого каталога в Git. Новый тип
появляется в `list` и completion автоматически:

```bash
./bin/agent create my-agent my-task
./bin/agent start my-task
./bin/agent attach my-task
```
