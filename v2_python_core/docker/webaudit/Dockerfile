# Web Audit Pro — runnable image for Windows/macOS/Linux via Docker Desktop.
# Build:  docker build -f docker/webaudit/Dockerfile -t webaudit:local .
# Run:    docker run --rm webaudit:local scan https://example.com --open none
#
# Pull-only users: extract the host wrapper (mount + browser open on your Mac/Linux):
#   docker run --rm --entrypoint cat webaudit:local /usr/share/webaudit/webaudit-docker.sh > ~/.local/bin/webaudit-docker
#   chmod +x ~/.local/bin/webaudit-docker

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

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir . \
    && chmod 755 /usr/share/webaudit/webaudit-docker.sh

ENV WEBAUDIT_OUTPUT_DIR=/work/audit_logs
WORKDIR /work

ENTRYPOINT ["webaudit"]
CMD ["--help"]
