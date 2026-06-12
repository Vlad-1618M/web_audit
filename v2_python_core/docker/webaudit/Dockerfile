# Web Audit Pro — runnable image for Windows/macOS/Linux via Docker Desktop.
# Build:  docker build -f docker/webaudit/Dockerfile -t webaudit:local .
# Run:    docker run --rm webaudit:local scan https://example.com --js --open none
#
# Pull-only users: install host wrapper (pull + PATH + ~/.local/bin/webaudit-docker):
#   curl -fsSL https://raw.githubusercontent.com/Vlad-1618M/web_audit/v.tools_main/v2_python_core/scripts/install-webaudit-docker.sh | bash

FROM python:3.12-slim-bookworm

LABEL org.opencontainers.image.title="webaudit"
LABEL org.opencontainers.image.description="Web Audit v2 — external security hygiene scanner"
LABEL org.opencontainers.image.source="https://github.com/Vlad-1618M/web_audit"
LABEL io.webaudit.host-wrapper="/usr/share/webaudit/webaudit-docker.sh"

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml README.md ./
COPY webaudit ./webaudit
COPY scripts/webaudit-docker.sh /usr/share/webaudit/webaudit-docker.sh
COPY scripts/install-webaudit-docker.sh /usr/share/webaudit/install-webaudit-docker.sh

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir ".[js]" \
    && python -m playwright install --with-deps chromium chromium-headless-shell \
    && chmod 755 /usr/share/webaudit/webaudit-docker.sh \
    && chmod 755 /usr/share/webaudit/install-webaudit-docker.sh

ENV WEBAUDIT_OUTPUT_DIR=/work/audit_logs
WORKDIR /work

ENTRYPOINT ["webaudit"]
CMD ["--help"]
