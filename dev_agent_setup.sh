#!/usr/bin/env bash
set -e

mkdir -p codex-config/agents

[ -f ./codex_dev_md/scout.toml ]     && cp ./codex_dev_md/scout.toml ./codex-config/agents/scout.toml
[ -f ./codex_dev_md/worker.toml ]    && cp ./codex_dev_md/worker.toml ./codex-config/agents/worker.toml
[ -f ./codex_dev_md/architect.toml ] && cp ./codex_dev_md/architect.toml ./codex-config/agents/architect.toml

if [ -f ./codex-config/config.toml ]; then
  echo "config.toml уже существует — модифицируйте текущий конфиг вручную"
elif [ -f ./codex_dev_md/config.toml ]; then
  cp ./codex_dev_md/config.toml ./codex-config/config.toml
fi

if [ -f ./workspace/AGENTS.md ]; then
  echo "AGENTS.md уже существует — модифицируйте вручную"
elif [ -f ./codex_dev_md/AGENTS.md ]; then
  cp ./codex_dev_md/AGENTS.md ./workspace/AGENTS.md
fi