# Web Audit Pro — runnable image for Windows/macOS/Linux via Docker Desktop.
# Build:  docker build -f docker/webaudit/Dockerfile -t webaudit:local .
# Run:    docker run --rm webaudit:local scan https://example.com --open none

FROM python:3.12-slim-bookworm

LABEL org.opencontainers.image.title="webaudit"
LABEL org.opencontainers.image.description="Web Audit v2 — external security hygiene scanner"
LABEL org.opencontainers.image.source="https://github.com/Vlad-1618M/web_audit"

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml README.md ./
COPY webaudit ./webaudit

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

ENV WEBAUDIT_OUTPUT_DIR=/work/audit_logs
WORKDIR /work

ENTRYPOINT ["webaudit"]
CMD ["--help"]
