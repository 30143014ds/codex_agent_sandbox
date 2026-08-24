FROM node:22-bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl ca-certificates build-essential sudo procps ripgrep \
    && rm -rf /var/lib/apt/lists/*

RUN npm install -g @openai/codex

ARG HOST_UID=1000
ARG HOST_GID=1000

RUN if getent passwd ${HOST_UID} > /dev/null 2>&1; then \
      userdel -r "$(getent passwd ${HOST_UID} | cut -d: -f1)" 2>/dev/null || true; \
    fi \
    && if getent group ${HOST_GID} > /dev/null 2>&1; then \
      groupdel "$(getent group ${HOST_GID} | cut -d: -f1)" 2>/dev/null || true; \
    fi \ 
    && groupadd -g ${HOST_GID} agent \
    && useradd -m -s /bin/bash -u ${HOST_UID} -g ${HOST_GID} agent \
    && mkdir -p /workspace \
    && chown -R agent:agent /workspace

USER agent
WORKDIR /workspace

CMD ["sleep", "infinity"]