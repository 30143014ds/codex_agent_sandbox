FROM python:3.13.7-slim-bookworm AS python_runtime

FROM node:22-bookworm-slim AS base

ARG DEBIAN_FRONTEND=noninteractive
ARG HOST_UID=1000
ARG HOST_GID=1000

COPY --from=python_runtime /usr/local /usr/local

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       bash ca-certificates curl findutils git jq procps ripgrep sudo tini \
    && rm -rf /var/lib/apt/lists/* \
    && corepack enable \
    && npm install --global @openai/codex \
    && python -m pip install --no-cache-dir pipx==1.17.1 uv==0.12.7

RUN if getent passwd "${HOST_UID}" >/dev/null 2>&1; then \
      userdel -r "$(getent passwd "${HOST_UID}" | cut -d: -f1)" 2>/dev/null || true; \
    fi \
    && if getent group "${HOST_GID}" >/dev/null 2>&1; then \
      groupdel "$(getent group "${HOST_GID}" | cut -d: -f1)" 2>/dev/null || true; \
    fi \
    && groupadd --gid "${HOST_GID}" agent \
    && useradd --create-home --shell /bin/bash \
       --uid "${HOST_UID}" --gid "${HOST_GID}" agent \
    && install -d -o agent -g agent \
       /home/agent/.agents/skills /home/agent/.cache /home/agent/.codex /workspace \
    && printf '%s\n' 'agent ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/agent \
    && chmod 0440 /etc/sudoers.d/agent

ENV CODEX_HOME=/home/agent/.codex \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER agent
WORKDIR /workspace

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["sleep", "infinity"]


FROM base AS developer

USER root

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       apache2-utils build-essential gnupg libpq-dev make openssh-client \
       openssl postgresql-client shellcheck unzip \
    && install -m 0755 -d /etc/apt/keyrings \
    && curl --fail --location --silent --show-error \
       https://download.docker.com/linux/debian/gpg \
       --output /etc/apt/keyrings/docker.asc \
    && chmod a+r /etc/apt/keyrings/docker.asc \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian $(. /etc/os-release && echo \"$VERSION_CODENAME\") stable" \
       > /etc/apt/sources.list.d/docker.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
       containerd.io docker-buildx-plugin docker-ce docker-ce-cli \
       docker-compose-plugin \
    && docker compose version \
    && rm -rf /var/lib/apt/lists/*

ENV COMPOSE_DOCKER_CLI_BUILD=1 \
    DOCKER_BUILDKIT=1 \
    DOCKER_HOST=unix:///var/run/docker.sock

USER agent

CMD ["bash", "-lc", "sudo dockerd --host=unix:///var/run/docker.sock --group=agent > /tmp/dockerd.log 2>&1 & for _ in $(seq 1 60); do if docker info >/dev/null 2>&1; then exec sleep infinity; fi; sleep 1; done; echo 'Docker daemon did not become ready within 60 seconds. Log:' >&2; tail -n 100 /tmp/dockerd.log >&2 || true; exit 1"]